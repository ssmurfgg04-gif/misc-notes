#!/usr/bin/env python3
"""Features (window-internal only, observed-cells-only) + tournament v1.

Models: constant, band-background excess heuristic, LightGBM direct,
LightGBM two-head (presence x conditional fraction). Grouped validation:
hold out reference clips AND background sites. Reports RMSE per scenario.
"""
import numpy as np
import pandas as pd
import argparse, json, os

BANDS = 25


def featurize(X):
    """X: (N,15,25) linear power with NaN -> feature matrix."""
    N = X.shape[0]
    Xf = np.where(np.isfinite(X), X, np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        logX = np.log10(np.maximum(Xf, 1e-30))
    feats = {}
    band_mean = np.nanmean(Xf, axis=1)               # (N,25)
    feats["log_band_mean"] = 10 * np.log10(np.maximum(band_mean, 1e-30))
    tot = np.nansum(Xf, axis=(1, 2))                 # (N,)
    feats["log_total"] = 10 * np.log10(np.maximum(tot, 1e-30))[:, None]
    # spectral shape
    bm = band_mean / np.maximum(np.nansum(band_mean, axis=1, keepdims=True), 1e-30)
    feats["band_share"] = bm
    gm = np.exp(np.nanmean(np.log(np.maximum(band_mean, 1e-30)), axis=1))
    am = np.nanmean(band_mean, axis=1)
    feats["flatness"] = (gm / np.maximum(am, 1e-30))[:, None]
    tilt = np.nanmean(np.log10(np.maximum(band_mean, 1e-30))[:, :8], axis=1) - \
        np.nanmean(np.log10(np.maximum(band_mean, 1e-30))[:, 17:], axis=1)
    feats["tilt"] = tilt[:, None]
    # temporal structure
    per_min = np.nansum(Xf, axis=2)                  # (N,15)
    pm_med = np.nanmedian(per_min, axis=1)
    feats["min_profile"] = (per_min / np.maximum(pm_med[:, None], 1e-30))
    feats["min_cv"] = (np.nanstd(per_min, axis=1) / np.maximum(np.nanmean(per_min, axis=1), 1e-30))[:, None]
    feats["min_max_ratio"] = (np.nanmax(per_min, axis=1) / np.maximum(np.nanmedian(per_min, axis=1), 1e-30))[:, None]
    # band outliers vs window band-median (per-minute excess)
    ratio = Xf / np.maximum(band_mean[:, None, :], 1e-30)
    feats["band_excess_p95"] = np.nanquantile(ratio, .95, axis=(1, 2))[:, None]
    feats["band_excess_max"] = np.nanmax(ratio, axis=(1, 2))[:, None]
    # missingness
    feats["missing_frac"] = 1 - np.isfinite(X).reshape(N, -1).mean(1)[:, None]
    m01 = np.isfinite(X[:, 0, :]).mean(1)
    feats["m01_obs"] = m01[:, None]
    names, cols = [], []
    for k, v in feats.items():
        if v.ndim == 1:
            v = v[:, None]
        for j in range(v.shape[1]):
            names.append(f"{k}_{j}" if v.shape[1] > 1 else k)
            cols.append(v[:, j])
    Fm = np.column_stack(cols)
    return np.nan_to_num(Fm, nan=0.0, posinf=0.0, neginf=0.0), names


def heuristic(X, bg_band_median):
    """Excess-over-background fraction proxy (linear domain)."""
    Xf = np.where(np.isfinite(X), X, np.nan)
    exc = np.nansum(np.clip(Xf - bg_band_median[None, :, :], 0, None), axis=(1, 2))
    tot = np.nansum(Xf, axis=(1, 2))
    return np.clip(exc / np.maximum(tot, 1e-30), 0, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synth_dir", default="/home/z/my-project/data/synth_v1")
    ap.add_argument("--test_csv", default="/home/z/my-project/data/Test.csv")
    ap.add_argument("--out", default="/home/z/my-project/data/tournament_v1")
    ap.add_argument("--round1", action="store_true", help="single 80/20 split (fast path)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    import lightgbm as lgb

    X = np.load(f"{a.synth_dir}/X.npy")
    f = np.load(f"{a.synth_dir}/f.npy")
    aux = pd.read_csv(f"{a.synth_dir}/aux.csv")
    Fm, names = featurize(X)
    print("features:", Fm.shape)

    # grouped split: hold out clips AND sites
    clips = sorted(aux["clip_uid"].unique())
    sites = sorted(aux["site"].unique())
    rng = np.random.default_rng(1)
    test_clips = set(rng.choice(clips, size=max(1, len(clips) // 5), replace=False).tolist())
    test_sites = set(rng.choice(sites, size=max(1, len(sites) // 5), replace=False).tolist())
    is_val = aux["clip_uid"].isin(test_clips) | aux["site"].isin(test_sites)
    tr, va = ~is_val.to_numpy(), is_val.to_numpy()
    print(f"train {tr.sum()}  val {va.sum()}  (held-out clips {len(test_clips)}, sites {test_sites})")

    scen = aux["scenario"].to_numpy()
    results = {}
    preds_val = np.zeros(len(f))
    # 1) constant (optimum on train)
    from scipy.optimize import minimize_scalar
    c = minimize_scalar(lambda v: np.mean((f[tr] - v) ** 2), bounds=(0, 1), method="bounded").x
    results["constant"] = {"val_rmse": float(np.sqrt(np.mean((f[va] - c) ** 2))), "const": float(c)}
    preds_val += c * 0  # placeholder
    # 2) heuristic
    bg_med = np.nanmedian(X[tr], axis=0)
    h = heuristic(X, bg_med)
    results["heuristic"] = {"val_rmse": float(np.sqrt(np.mean((f[va] - h[va]) ** 2)))}
    # 3) LightGBM direct
    m1 = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=0, verbose=-1)
    m1.fit(Fm[tr], f[tr], eval_set=[(Fm[va], f[va])], callbacks=[lgb.early_stopping(50, verbose=False)])
    p1 = np.clip(m1.predict(Fm[va]), 0, 1)
    results["lgbm_direct"] = {"val_rmse": float(np.sqrt(np.mean((f[va] - p1) ** 2))),
                              "best_iter": int(m1.best_iteration_ or 600)}
    # 4) two-head
    y_bin = (f > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=0, verbose=-1)
    mc.fit(Fm[tr], y_bin[tr])
    pc = np.clip(mc.predict_proba(Fm[va])[:, 1], 0, 1)
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, random_state=0, verbose=-1)
    mr.fit(Fm[tr & (f > 1e-9)], f[tr & (f > 1e-9)])
    pr = np.clip(mr.predict(Fm[va]), 0, 1)
    p2 = pc * pr
    results["lgbm_twohead"] = {"val_rmse": float(np.sqrt(np.mean((f[va] - p2) ** 2)))}
    # per-scenario
    for model, pv in [("constant", None), ("heuristic", h), ("lgbm_direct", None), ("lgbm_twohead", p2)]:
        per = {}
        for s in np.unique(scen[va]):
            msk = scen[va] == s
            if model == "constant":
                val = np.sqrt(np.mean((f[va][msk] - c) ** 2))
            elif model == "heuristic":
                val = np.sqrt(np.mean((f[va][msk] - h[va][msk]) ** 2))
            elif model == "lgbm_direct":
                val = np.sqrt(np.mean((f[va][msk] - p1[msk]) ** 2))
            else:
                val = np.sqrt(np.mean((f[va][msk] - p2[msk]) ** 2))
            per[s] = round(float(val), 4)
        results[model]["per_scenario"] = per

    # feature importance (direct model)
    imp = sorted(zip(names, m1.feature_importances_), key=lambda t: -t[1])[:15]
    results["top_features"] = [[n, int(v)] for n, v in imp]

    # ---- inference on real test with two-head (and direct) ----
    test = pd.read_csv(a.test_csv)
    cols = [c2 for c2 in test.columns if c2 != "ID"]
    At = test[cols].to_numpy(dtype=np.float64).reshape(-1, 15, BANDS)
    Ft, _ = featurize(At)
    sub = pd.DataFrame({"ID": test["ID"]})
    sub["share_direct"] = np.clip(m1.predict(Ft), 0, 1)
    sub["share_twohead"] = np.clip(mc.predict_proba(Ft)[:, 1] * mr.predict(Ft), 0, 1)
    sub["score_twohead"] = np.clip(mc.predict_proba(Ft)[:, 1], 0, 1)
    sub["share_heuristic"] = heuristic(At, bg_med)
    sub.to_csv(f"{a.out}/test_predictions_v1.csv", index=False)

    with open(f"{a.out}/results.json", "w") as fh:
        json.dump(results, fh, indent=1)
    print(json.dumps({k: v for k, v in results.items() if k != "top_features"}, indent=1))
    print("top features:", results["top_features"][:8])
    print("saved ->", a.out)


if __name__ == "__main__":
    main()
