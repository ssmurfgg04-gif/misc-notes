#!/usr/bin/env python3
"""train_v2.py — R4 two-head training + site-ID features + structural-lock fusion.

Protocols (E2/E5): clip-held-out, site-held-out, both-held-out. AUC reported for
the presence head; NO probability calibration (E2).
Baselines: zero-const (= benchmark predictor, A15), mean-const (train-optimal).

E4 ablation: model / model+siteID / lock-only / fused(w=0.5) x with/without
total-energy features (A17 says total energy alone cannot identify f).

Hedge comparison (A16 restated): train on HEDGE synth, validate on the FIXED
primary-scenario holdout — does a different training marginal help?

Rules (A22): site centroids and lock medians are fit on TRAIN data only
(synthetic train + SA package backgrounds). Test inputs are inference-only.
"""
import argparse, json, os, sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tournament import featurize  # R2 battle-tested features (window-internal only)


def site_features(X, train_sites_bg, train_site_keys):
    """E3: fit nearest-centroid on TRAIN background windows; return per-window
    distance features (10 sites -> 10 distances, unseen sites get +inf->large).
    X: (N,15,25); train_sites_bg: (M,15,25) background windows from train split."""
    import site_id as S
    d_tr = S.window_descriptor(train_sites_bg)
    model = S.SiteID(tau=1.0).fit(d_tr, train_site_keys)
    d_all = S.window_descriptor(X)
    # assign() gives (site, confident, margin, dist matrix) in fitted-site order
    site, conf, margin, dist = model.assign(d_all)
    cols = np.column_stack([dist[:, k] for k in range(dist.shape[1])] +
                           [margin, conf.astype(float)])
    names = [f"site_dist_{s}" for s in model.sites] + ["site_margin", "site_conf"]
    return cols, names, model


def train_twohead(Ftr, ftr, Fva, fva):
    ytr = (ftr > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=0, verbose=-1, n_jobs=2)
    mc.fit(Ftr, ytr)
    pc = np.clip(mc.predict_proba(Fva)[:, 1], 0, 1)
    auc = float(roc_auc_score((fva > 1e-9).astype(int), pc))
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=0, verbose=-1, n_jobs=2)
    mr.fit(Ftr[ytr == 1], ftr[ytr == 1])
    pr = np.clip(mr.predict(Fva), 0, 1)
    p2 = np.clip(pc * pr, 0, 1)
    m1 = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=0, verbose=-1, n_jobs=2)
    m1.fit(Ftr, ftr)
    p1 = np.clip(m1.predict(Fva), 0, 1)
    return {"p_direct": p1, "p_two": p2, "auc": auc, "mc": mc, "mr": mr, "m1": m1}


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y) - np.asarray(p)) ** 2)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth", default="/home/z/my-project/data/synth_v2")
    ap.add_argument("--test_csv", default="/home/z/my-project/data/Test.csv")
    ap.add_argument("--out", default="/home/z/my-project/data/train_v2")
    ap.add_argument("--hedges", default="G_weighted_low,G_nonuniform")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    R = {}

    # ---------- primary ----------
    d = os.path.join(a.synth, "G_unif_04")
    X = np.load(f"{d}/X.npy"); f = np.load(f"{d}/f.npy")
    aux = pd.read_csv(f"{d}/aux.csv")
    print("primary", X.shape, flush=True)
    Fm, names = featurize(X)

    rng = np.random.default_rng(1)
    clips = aux["clip_uid"].astype(str).to_numpy()
    sites = aux["site"].astype(str).to_numpy()
    uc, us = np.unique(clips), np.unique(sites)
    hold_c = set(rng.choice(uc, size=max(1, len(uc) // 5), replace=False).tolist())
    hold_s = set(rng.choice(us, size=max(1, len(us) // 5), replace=False).tolist())
    va_c = np.isin(clips, list(hold_c))
    va_s = np.isin(sites, list(hold_s))

    # background windows per site from TRAIN slice (for site-ID fitting, A22)
    bg_mask = (f == 0.0) & (~va_c) & (~va_s)
    bgX = X[bg_mask]; bg_sites = sites[bg_mask]

    F_site, site_names, site_model = site_features(X, bgX, bg_sites)
    F_full = np.hstack([Fm, F_site])

    # A17 ablation: drop total-energy features (log_total, min_profile scale, min_cv...)
    drop_idx = [i for i, n in enumerate(names) if n.startswith("log_total")]
    F_noshape_total = np.delete(Fm, drop_idx, axis=1)
    F_noshape_total_full = np.delete(F_full, drop_idx, axis=1)

    protocols = {"clip_held_out": va_c, "site_held_out": va_s, "both_held_out": va_c | va_s}
    results = {"feature_sets": {}}
    fsum = np.nansum(X.astype(np.float64), axis=(1, 2))     # ΣM per window

    for pname, va in protocols.items():
        tr = ~va
        # lock model: site-conditional median ΣB on train background windows only
        import structural_lock as SL
        bg_tr = (f == 0.0) & tr
        sumB_bg = np.nansum(X[bg_tr].astype(np.float64), axis=(1, 2))
        lm = SL.LockModel().fit(sumB_bg, sites[bg_tr])
        f_lock = np.clip(1.0 - lm.predict_sumB(sites) / np.maximum(fsum, 1e-30), 0, 1)

        pr = {}
        # (a) base features
        m = train_twohead(F_full[tr], f[tr], F_full[va], f[va])
        pr["model_twohead"] = {"rmse": rmse(f[va], m["p_two"]), "auc": m["auc"]}
        pr["model_direct"] = {"rmse": rmse(f[va], m["p_direct"])}
        # (b) without total-energy features (A17 ablation)
        m2 = train_twohead(F_noshape_total_full[tr], f[tr], F_noshape_total_full[va], f[va])
        pr["model_no_total_feat"] = {"rmse": rmse(f[va], m2["p_two"]), "auc": m2["auc"]}
        # (c) lock only / (d) fused
        pr["lock_only"] = {"rmse": rmse(f[va], f_lock[va])}
        p_fused = 0.5 * m["p_two"] + 0.5 * f_lock[va]
        pr["fused_w0.5"] = {"rmse": rmse(f[va], p_fused)}
        # baselines
        pr["zero_const"] = {"rmse": rmse(f[va], np.zeros(len(f[va])))}
        pr["mean_const"] = {"rmse": rmse(f[va], np.full(len(f[va]), f[tr].mean()))}
        results["feature_sets"][pname] = pr
        print(pname, json.dumps(pr), flush=True)
        if pname == "both_held_out":
            best_model = m

    # ---------- hedge comparison on FIXED primary holdout ----------
    va_fixed = va_c | va_s
    tr_fixed = ~va_fixed
    for hname in a.hedges.split(","):
        hd = os.path.join(a.synth, hname)
        if not os.path.isdir(hd):
            continue
        Xh = np.load(f"{hd}/X.npy"); fh = np.load(f"{hd}/f.npy")
        auxh = pd.read_csv(f"{hd}/aux.csv")
        Fh, _ = featurize(Xh)
        Fh_site, _, _ = site_features(Xh, X[bg_mask], sites[bg_mask])
        Fh_full = np.hstack([Fh, Fh_site])
        mh = train_twohead(Fh_full[tr_fixed], fh[tr_fixed], F_full[va_fixed], f[va_fixed])
        results[f"hedge_{hname}"] = {
            "val_on_primary_holdout_rmse": rmse(f[va_fixed], mh["p_two"]),
            "primary_model_same_val_rmse": rmse(f[va_fixed], best_model["p_two"]),
            "auc": mh["auc"]}
        print(f"hedge {hname}:", json.dumps(results[f"hedge_{hname}"]), flush=True)

    # ---------- test inference (primary two-head, both-held-out trained on ~80%) ----------
    # For submission: refit on ALL primary windows (train+val) — labels are synthetic.
    m_all = train_twohead(F_full, f, F_full[:100], f[:100])  # refit on full
    test = pd.read_csv(a.test_csv)
    cols = [c for c in test.columns if c != "ID"]
    At = test[cols].to_numpy(dtype=np.float64).reshape(-1, 15, 25)
    Ft, _ = featurize(At)
    Ft_site, _, _ = site_features(At, bgX, sites[bg_mask])
    Ft_full = np.hstack([Ft, Ft_site])
    share = np.clip(m_all["mr"].predict(Ft_full) * m_all["mc"].predict_proba(Ft_full)[:, 1], 0, 1)
    score = np.clip(m_all["mc"].predict_proba(Ft_full)[:, 1], 0, 1)
    sub = pd.DataFrame({"ID": test["ID"], "share_added_vessel": share,
                        "score_added_vessel": score})
    sub.to_csv(f"{a.out}/submission_r4_v1.csv", index=False)
    results["submission"] = {"file": "submission_r4_v1.csv", "n": int(len(sub)),
                             "mean_share": float(share.mean()),
                             "mean_score": float(score.mean()),
                             "share_quantiles": {str(q): float(np.quantile(share, q))
                                                 for q in [0, .1, .25, .5, .75, .9, 1]}}
    with open(f"{a.out}/train_report_v2.json", "w") as fh:
        json.dump(results, fh, indent=1, default=str)
    print(json.dumps(results["submission"], indent=1))


if __name__ == "__main__":
    main()
