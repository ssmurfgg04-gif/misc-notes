#!/usr/bin/env python3
"""R8b — post-intel build (R10-B C5/C3/C4 + R10-C floor fix).

Adds to the validated R8 T1+T2 stack:
  W1  Knudsen wind-index features (C5): quiet-minute robust dB~log10(f) fit
      over wind-regime bands k12..24 (0.5-8 kHz): level, slope, fit MAD.
  W2  Full-axis median LogTBN channel (M8 correction): per-band median over
      all 15 minutes = baseline; continuous positive-excess share f_pcfull.
  W3  Soft floor for no-bump windows (R10-C item 2): CAL-calibrated isotonic
      f_true | f_pc on no-bump windows replaces the hard 0 (kills the
      33.8%-at-floor point mass honestly).
  W4  Rank-REST domain probe (C3/C4 tabular analogue): quantile-map train
      features into each target-group distribution, retrain, eval on
      class-matched pools vs unmapped baseline (AdaBN analogue; CORAL for
      trees is not axis-aligned, rank-REST is monotone per feature = safe).

Gates (D29 family): VALclassB_G1 < 0.0507 adopt wind; softfloor must not
worsen any pool; rank-REST must beat unmapped on its own class pool.

Outputs: data/train_v3/r8b_report.json, r8b_test_diag.npz
Run AFTER r8_t1t2_build.py (needs r8_pool/*.npy).
"""
import json, sys, os
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.isotonic import IsotonicRegression
from sklearn.preprocessing import QuantileTransformer

BASE = "/home/z/my-project"
sys.path.insert(0, f"{BASE}/src")
from tournament import featurize

WIN, NB = 15, 25
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
LOGC = np.log10(CENTRES)
LF, WND_B, WREG = slice(0, 7), slice(15, 20), slice(12, 25)
OUT = f"{BASE}/data/train_v3"
POOL = f"{OUT}/r8_pool"
R = {"protocol": "R8 pools + W1 wind-index + W2 full-axis LogTBN + W3 softfloor + W4 rank-REST probe"}

CLASS_SITES = {
    "A_west_moored_G0": ["13_Saldhana_Bay", "09_Fish_Hoek"],
    "B_southcoast_exposed_G1": ["07_St_Francis", "03_Cape_Recife"],
    "C_harbour_industrial_G2": ["01_Richards_Bay", "02_Durban", "05_St_Croix_Island"],
    "D_residual": ["04_Bird_Island", "06_Riy_Banks", "10_Sea_Point"],
}
GATE_B_G1 = 0.0507

def load(name):
    X = np.load(f"{POOL}/X_{name}.npy")
    f = np.load(f"{POOL}/f_{name}.npy")
    return X, f

def bed_profile(w):
    W = np.where(np.isfinite(w) & (w > 0), w, np.nan)
    return 10 * np.log10(np.nanpercentile(W, 10, axis=0) + 1e-30)

# ---------------- W2/W1 machinery ----------------
def window_stats(X):
    """vectorised-ish per-window: tot, bump mask, E5, f_pc, f_pcfull, wind fit."""
    N = X.shape[0]
    f5 = np.zeros(N); f_pc = np.zeros(N); f_pcfull = np.zeros(N)
    w_int = np.full(N, np.nan); w_sl = np.full(N, np.nan); w_mad = np.full(N, np.nan)
    nobump = np.ones(N, bool)
    k = 5
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot = np.nansum(np.where(obs, W, 0.0), axis=1)
        pos = tot > 0
        if not pos.any():
            continue
        med = np.median(tot[pos])
        bump = tot > 1.35 * med
        # E5 (verbatim)
        if bump.sum() >= 2:
            quiet = ~bump & pos
            if quiet.sum() >= 2:
                Bq = np.nanmedian(np.where(quiet[:, None], W, np.nan), axis=0)
                exc = np.where(obs & bump[:, None], np.maximum(W - Bq[None, :], 0.0), 0.0)
                totsum = np.nansum(np.where(obs, W, 0.0))
                f5[i] = float(np.clip(exc.sum() / totsum, 0, 1))
                nobump[i] = False
        # trailing runmed PCEN-ish (verbatim)
        runmed = np.array([np.median(tot[max(0, j-k+1):j+1]) for j in range(WIN)])
        f_pc[i] = np.clip(np.maximum(tot - 1.15*runmed, 0).sum() / max(tot.sum(), 1e-30), 0, 1)
        # W2 full-axis per-band median baseline
        Bmed = np.nanmedian(np.where(obs & pos[:, None], W, np.nan), axis=0)
        excf = np.where(obs, np.maximum(W - Bmed[None, :], 0.0), 0.0)
        f_pcfull[i] = float(np.clip(excf.sum() / max(np.nansum(np.where(obs, W, 0.0)), 1e-30), 0, 1))
        # W1 wind fit on quiet minutes, wind-regime bands, dB vs log10(f)
        qm = pos & ~bump
        if qm.sum() >= 3:
            Wq = W[qm][:, WREG]
            ok = np.isfinite(Wq) & (Wq > 0)
            if ok.sum() >= 20:
                xs, ys = LOGC[WREG], 10*np.log10(Wq)
                xs = np.broadcast_to(xs, Wq.shape)
                x, y = xs[ok], ys[ok]
                # Theil-Sen via subsample (sklearn robust not needed): median of pair slopes
                n = len(x)
                if n > 60:
                    r = np.random.default_rng(11+i)
                    sel = r.choice(n, 60, replace=False)
                    x2, y2 = x[sel], y[sel]
                else:
                    x2, y2 = x, y
                sl = []
                for a_i in range(len(x2)):
                    for b_i in range(a_i+1, len(x2)):
                        if abs(x2[a_i]-x2[b_i]) > 1e-9:
                            sl.append((y2[a_i]-y2[b_i])/(x2[a_i]-x2[b_i]))
                if sl:
                    s = np.median(sl)
                    b = np.median(y - s*x)
                    w_sl[i] = s; w_int[i] = b
                    w_mad[i] = np.median(np.abs(y - (s*x + b)))
    return dict(f5=f5, f_pc=f_pc, f_pcfull=f_pcfull, nobump=nobump,
                w_int=w_int, w_sl=w_sl, w_mad=w_mad)

def t1t2_features(X):
    """same T1/T2 blocks as r8_followup (A70 centered shapes)."""
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])
    beds_c = beds - np.nanmean(beds, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10*np.log10(np.maximum(bmean, 1e-30))
    return {"bed": beds, "snr": bmean_dB - beds,
            "bed_low": beds[:, LF].mean(1)[:, None],
            "bed_hf": beds[:, 20:].mean(1)[:, None]}

# class fingerprints from train pool sites (as r8_followup)
X_tr0, f_tr0 = load("train")
sites = pd.read_csv(f"{POOL}/aux_train.csv")["site"].to_numpy()
site_fp = {}
for s in sorted(set(sites)):
    idx = np.where(sites == s)[0][:400]
    site_fp[s] = np.nanmedian(np.stack([bed_profile(X_tr0[i]) for i in idx]), axis=0)
class_fp = {c: np.nanmean(np.stack([site_fp[s] for s in sl]), axis=0) for c, sl in CLASS_SITES.items()}
class_fp_c = {c: fp - np.nanmean(fp) for c, fp in class_fp.items()}

def t1_features(X):
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])
    beds_c = beds - np.nanmean(beds, axis=1, keepdims=True)
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10*np.log10(np.maximum(bmean, 1e-30))
    feats = {"bed": beds, "snr": bmean_dB - beds,
             "bed_low": beds[:, LF].mean(1)[:, None], "bed_hf": beds[:, 20:].mean(1)[:, None]}
    for c, fp in class_fp.items():
        d_level = np.sqrt(np.nanmean((beds - fp[None, :])**2, axis=1))
        d_shape = np.sqrt(np.nanmean((beds_c - class_fp_c[c][None, :])**2, axis=1))
        feats[f"dist_{c.split('_G')[0]}"] = d_level[:, None]
        feats[f"shp_{c.split('_G')[0]}"] = d_shape[:, None]
    return feats

def t2_wind(stats):
    return {"wind_int": stats["w_int"][:, None], "wind_sl": stats["w_sl"][:, None],
            "wind_mad": stats["w_mad"][:, None],
            "f_pcfull": stats["f_pcfull"][:, None]}

def assemble(X, stats):
    Fb, nb = featurize(X)
    parts, names = [Fb], list(nb)
    for tag, d in (("t1", t1_features(X)), ("t2w", t2_wind(stats))):
        for k, v in d.items():
            parts.append(np.nan_to_num(np.asarray(v, float), nan=0.0, posinf=0.0, neginf=0.0))
            names += [f"{tag}_{k}_{j}" for j in range(np.asarray(v).shape[1])]
    return np.hstack(parts), names

def twohead(Ftr, ftr, seed=0):
    y = (ftr > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=seed, verbose=-1, n_jobs=2)
    mc.fit(Ftr, y)
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=seed, verbose=-1, n_jobs=2)
    mr.fit(Ftr[y == 1], ftr[y == 1])
    return mc, mr

def rmse(a, b): return float(np.sqrt(np.mean((np.asarray(a, float)-np.asarray(b, float))**2)))

# ---------------- pools ----------------
print("loading pools...", flush=True)
P = {}
for nm in ["train", "cal", "val_main", "val_calm", "val_A_west_moored",
           "val_B_southcoast_exposed", "val_C_harbour_industrial", "val_D_residual"]:
    P[nm] = load(nm)
    print(" ", nm, P[nm][0].shape, flush=True)

print("window stats per pool (E5/E5pcen/fullaxis/wind)...", flush=True)
S = {nm: window_stats(X) for nm, (X, f) in P.items()}

print("features train/cal...", flush=True)
F_tr, names_tr = assemble(P["train"][0], S["train"])
F_cal, _ = assemble(P["cal"][0], S["cal"])
mc, mr = twohead(F_tr, P["train"][1])

# ---------------- W3 softfloor: CAL isotonic on no-bump windows ----------------
cal = S["cal"]
nbm = cal["nobump"]
iso = IsotonicRegression(out_of_bounds="clip")
iso.fit(cal["f_pc"][nbm], P["cal"][1][nbm])
R["softfloor_cal"] = {
    "n_nobump": int(nbm.sum()), "mean_f_nobump": float(P["cal"][1][nbm].mean()),
    "spearman_fp_f_nobump": float(pd.Series(cal["f_pc"][nbm]).corr(pd.Series(P["cal"][1][nbm]), method="spearman")),
    "mean_f_bumpwin": float(P["cal"][1][~nbm].mean()),
    "fn_rate_nobump": float((P["cal"][1][nbm] > 1e-9).mean()),
}
print("softfloor CAL:", json.dumps(R["softfloor_cal"]), flush=True)

def predict_set(X, f, st, F=None):
    if F is None:
        F, _ = assemble(X, st)
    lgb_p = np.clip(mc.predict_proba(F)[:, 1] * mr.predict(F), 0, 1)
    soft = np.where(st["nobump"], iso.predict(st["f_pc"]), lgb_p)
    return {"lgb": lgb_p, "lgb_softfloor": np.clip(soft, 0, 1)}, F

def evalrow(tag, f, preds):
    row = {"n": len(f)}
    for k, p in preds.items():
        row[f"{k}_rmse"] = rmse(f, p)
        row[f"{k}_rho"] = float(np.corrcoef(p, f)[0, 1])
    R[tag] = row
    print(f"{tag:28} " + " ".join(f"{k}:{row[f'{k}_rmse']:.4f}" for k in preds), flush=True)
    return row

print("\neval (with wind features)...", flush=True)
GATE_OK = {"wind": None, "softfloor": True}
for nm, tag in [("val_main", "VAL_main"), ("val_calm", "VAL_calm"),
                ("val_A_west_moored", "VALclassA_G0"),
                ("val_B_southcoast_exposed", "VALclassB_G1"),
                ("val_C_harbour_industrial", "VALclassC_G2"),
                ("val_D_residual", "VALclassD")]:
    X, f = P[nm]
    preds, _ = predict_set(X, f, S[nm])
    evalrow(tag, f, preds)
    if tag == "VALclassB_G1":
        GATE_OK["wind"] = preds["lgb_rmse"] < GATE_B_G1
    # softfloor must not worsen
    if preds["lgb_softfloor_rmse"] > preds["lgb_rmse"] + 1e-4:
        GATE_OK["softfloor"] = False

R["gates"] = {"wind_adopted": bool(GATE_OK["wind"]), "softfloor_ok": bool(GATE_OK["softfloor"]),
              "gate_ref": GATE_B_G1}

# ---------------- W4 rank-REST probe (A/B/C class pools) ----------------
print("\nrank-REST probe...", flush=True)
probe = {}
for cls_nm, cls_tag in [("val_A_west_moored", "A_G0"), ("val_B_southcoast_exposed", "B_G1"),
                        ("val_C_harbour_industrial", "C_G2")]:
    Xv, fv = P[cls_nm]
    Sv = S[cls_nm]
    Fv, _ = assemble(Xv, Sv)
    qt = QuantileTransformer(n_quantiles=min(600, len(Fv)), output_distribution="uniform",
                             subsample=int(1e9), random_state=0)
    qt.fit(Fv)                       # target = class-matched pool distribution
    Ftr_m = qt.transform(F_tr)       # map train into target space
    mc_m, mr_m = twohead(Ftr_m, P["train"][1])
    pm = np.clip(mc_m.predict_proba(Fv)[:, 1] * mr_m.predict(Fv), 0, 1)
    base_rmse = rmse(fv, np.clip(mc.predict_proba(Fv)[:, 1]*mr.predict(Fv), 0, 1))
    probe[cls_tag] = {"unmapped_rmse": base_rmse, "rankrest_rmse": rmse(fv, pm)}
    print(cls_tag, probe[cls_tag], flush=True)
R["rankrest_probe"] = probe

# ---------------- test side ----------------
print("\ntest side...", flush=True)
test = pd.read_csv(f"{BASE}/data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)
TX_lin = 10.0 ** (TX / 10.0)
m01m = np.isnan(TX[:, 0, :]).all(1); m15m = np.isnan(TX[:, 14, :]).all(1)
grp = np.where(m01m, "G1", np.where(m15m, "G2", "G0")).astype("<U2")
St = window_stats(TX_lin)
Ft, _ = assemble(TX_lin, St)
lgb_t = np.clip(mc.predict_proba(Ft)[:, 1] * mr.predict(Ft), 0, 1)
soft_t = np.clip(np.where(St["nobump"], iso.predict(St["f_pc"]), lgb_t), 0, 1)
R["test_census"] = {"nobump_frac": float(St["nobump"].mean()),
                    "lgb_mean": float(lgb_t.mean()), "soft_mean": float(soft_t.mean()),
                    "soft_point_mass": float(pd.Series(np.round(soft_t, 9)).value_counts().iloc[0]/1500)}
print("test census:", json.dumps(R["test_census"]), flush=True)
R["test_moments"] = {"E_f2_lgb": float(np.mean(lgb_t**2)), "E_f2_soft": float(np.mean(soft_t**2)),
                     "pinned": 0.06058}

np.savez(f"{OUT}/r8b_test_diag.npz", lgb=lgb_t, softfloor=soft_t,
         nobump_mask=St["nobump"], f_pc=St["f_pc"], f5=St["f5"], grp=grp,
         wind_int=St["w_int"], wind_sl=St["w_sl"])
json.dump(R, open(f"{OUT}/r8b_report.json", "w"), indent=1, default=float)
print("\nsaved -> r8b_report.json / r8b_test_diag.npz")
print("GATES:", json.dumps(R["gates"]), flush=True)
