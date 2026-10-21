#!/usr/bin/env python3
"""R8 follow-up: (1) INVERTED wind gate (CAL shows FA bumps are LF-RICH,
planted vessel passages wind-band-rich: stat p50 FA 3.17 vs vessel 0.77,
AUC(FA)=0.921); (2) feature importances of the T1T2 head; (3) centered-shape
class distances (level vs shape separated); (4) E5+LGBM blend sweep.

Reloads r8_pool artifacts -> identical data; retrains with the same seeds.
"""
import json, sys
import numpy as np
import pandas as pd
import lightgbm as lgb

BASE = "/home/z/my-project"
sys.path.insert(0, f"{BASE}/src")
from tournament import featurize

WIN, NB = 15, 25
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
LOGC = np.log10(CENTRES)
LF, WND = slice(0, 7), slice(15, 20)
OUT = f"{BASE}/data/train_v3"
POOL = f"{OUT}/r8_pool"
R = {}

CLASS_SITES = {
    "A_west_moored_G0": ["13_Saldhana_Bay", "09_Fish_Hoek"],
    "B_southcoast_exposed_G1": ["07_St_Francis", "03_Cape_Recife"],
    "C_harbour_industrial_G2": ["01_Richards_Bay", "02_Durban", "05_St_Croix_Island"],
    "D_residual": ["04_Bird_Island", "06_Riy_Banks", "10_Sea_Point"],
}

def load(name):
    X = np.load(f"{POOL}/X_{name}.npy")
    f = np.load(f"{POOL}/f_{name}.npy")
    a = pd.read_csv(f"{POOL}/aux_{name}.csv")
    return X, f, a

def bed_profile(w):
    W = np.where(np.isfinite(w) & (w > 0), w, np.nan)
    return 10 * np.log10(np.nanpercentile(W, 10, axis=0) + 1e-30)

BGmeta = None
X_tr, f_tr, aux_tr = load("train")
sites = aux_tr["site"].to_numpy()
site_fp = {}
for s in sorted(set(sites)):
    idx = np.where(sites == s)[0][:400]
    site_fp[s] = np.nanmedian(np.stack([bed_profile(X_tr[i]) for i in idx]), axis=0)
class_fp = {c: np.nanmean(np.stack([site_fp[s] for s in sl]), axis=0)
            for c, sl in CLASS_SITES.items()}
class_fp_c = {c: fp - np.nanmean(fp) for c, fp in class_fp.items()}  # centered shape

def excess_stats(X):
    N = X.shape[0]
    f5 = np.zeros(N); f_pc = np.zeros(N)
    lf_frac = np.full(N, np.nan); wnd_frac = np.full(N, np.nan)
    exc_tilt = np.full(N, np.nan); smooth = np.full(N, np.nan)
    onset = np.full(N, np.nan); r_lf_wnd = np.full(N, np.nan)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot = np.nansum(np.where(obs, W, 0.0), axis=1)
        med = np.median(tot[tot > 0]) if (tot > 0).any() else 0.0
        bump = tot > 1.35 * med
        if bump.sum() >= 2:
            quiet = ~bump & (tot > 0)
            if quiet.sum() >= 2:
                Bq = np.nanmedian(np.where(quiet[:, None], W, np.nan), axis=0)
                exc = np.where(obs & bump[:, None], np.maximum(W - Bq[None, :], 0.0), 0.0)
                totsum = np.nansum(np.where(obs, W, 0.0))
                f5[i] = np.clip(exc.sum() / totsum if totsum > 0 else 0.0, 0, 1)
                E = exc.sum(0); Es = E.sum()
                if Es > 0:
                    lf_frac[i] = E[LF].sum() / Es
                    wnd_frac[i] = E[WND].sum() / Es
                    okb = E > 0
                    if okb.sum() >= 5:
                        exc_tilt[i] = np.polyfit(LOGC[okb], np.log10(E[okb]), 1)[0]
                    r_lf_wnd[i] = E[LF].sum() / max(E[WND].sum(), Es * 1e-6)
                    seg = tot[bump & (tot > 0)]
                    if len(seg) >= 3:
                        smooth[i] = np.std(np.diff(seg)) / max(np.std(seg), 1e-30)
                    onset[i] = (seg[0] - med) / max(med, 1e-30)
        if (tot > 0).any():
            k = 5
            runmed = np.array([np.median(tot[max(0, j - k + 1):j + 1]) for j in range(WIN)])
            excm = np.maximum(tot - 1.15 * runmed, 0.0)
            f_pc[i] = np.clip(excm.sum() / max(tot.sum(), 1e-30), 0, 1)
    return f5, f_pc, {"lf_frac": lf_frac, "wnd_frac": wnd_frac, "exc_tilt": exc_tilt,
                      "smooth": smooth, "onset": onset, "r_lf_wnd": r_lf_wnd}

def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a, float) - np.asarray(b, float)) ** 2)))

def t1_features(X):
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])
    beds_c = beds - np.nanmean(beds, axis=1, keepdims=True)      # centered shape
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10 * np.log10(np.maximum(bmean, 1e-30))
    feats = {"bed": beds, "snr": bmean_dB - beds,
             "bed_low": beds[:, LF].mean(1)[:, None],
             "bed_hf": beds[:, 20:].mean(1)[:, None]}
    for c, fp in class_fp.items():
        d_level = np.sqrt(np.nanmean((beds - fp[None, :]) ** 2, axis=1))
        d_shape = np.sqrt(np.nanmean((beds_c - class_fp_c[c][None, :]) ** 2, axis=1))
        feats[f"dist_{c.split('_G')[0]}"] = d_level[:, None]
        feats[f"shp_{c.split('_G')[0]}"] = d_shape[:, None]
    return feats

def t2_features(X, stats):
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10 * np.log10(np.maximum(bmean, 1e-30))
    return {"wind_bed": beds[:, WND].mean(1)[:, None],
            "wind_mean": bmean_dB[:, WND].mean(1)[:, None],
            "lf_wind_bed": beds[:, LF].mean(1)[:, None] - beds[:, WND].mean(1)[:, None],
            "lf_wind_mean": bmean_dB[:, LF].mean(1)[:, None] - bmean_dB[:, WND].mean(1)[:, None],
            "lf_frac": stats["lf_frac"][:, None], "wnd_frac": stats["wnd_frac"][:, None],
            "exc_tilt": stats["exc_tilt"][:, None], "smooth": stats["smooth"][:, None],
            "onset": stats["onset"][:, None],
            "log_r_lf_wnd": np.log10(np.maximum(stats["r_lf_wnd"], 1e-6))[:, None]}

def assemble(X, stats):
    Fb, nb = featurize(X)
    parts, names = [Fb], list(nb)
    for k, v in t1_features(X).items():
        parts.append(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0))
        names += [f"t1_{k}_{j}" for j in range(v.shape[1])]
    for k, v in t2_features(X, stats).items():
        parts.append(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0))
        names += [f"t2_{k}_{j}" for j in range(v.shape[1])]
    return np.hstack(parts), names

def twohead(Ftr, ftr, seed=0):
    y = (ftr > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=seed, verbose=-1, n_jobs=4)
    mc.fit(Ftr, y)
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=seed, verbose=-1, n_jobs=4)
    mr.fit(Ftr[y == 1], ftr[y == 1])
    return mc, mr

# ---------------- CAL: inverted gate threshold ----------------
print("CAL...", flush=True)
X_cal, f_cal, aux_cal = load("cal")
f5_cal, fpc_cal, st_cal = excess_stats(X_cal)
stat = np.log10(np.maximum(st_cal["r_lf_wnd"], 1e-6))
pos = f_cal > 1e-9; neg = ~pos
# FA windows that produced a bump (the ones we want to zero)
fa_bump = neg & np.isfinite(stat)
vessel_bump = pos & np.isfinite(stat)
thr_hi = float(np.nanpercentile(stat[fa_bump], 80)) if fa_bump.sum() > 30 else None
y = np.concatenate([np.zeros(fa_bump.sum()), np.ones(vessel_bump.sum())])
s = np.concatenate([stat[fa_bump], stat[vessel_bump]])
from sklearn.metrics import roc_auc_score
auc_fa = roc_auc_score(y, s)  # HIGH stat = FA (inverted vs v1 run)
R["gate_inverted"] = {"auc_FA_vs_vessel": float(auc_fa), "thr_hi_p80_FA": thr_hi,
                      "n_FA": int(fa_bump.sum()), "n_vessel": int(vessel_bump.sum()),
                      "vessel_recall_at_thr": float(np.mean(stat[vessel_bump] < thr_hi))}
print(json.dumps(R["gate_inverted"]), flush=True)

def e5_gate_inv(f5, stats, thr):
    out = f5.copy()
    s = np.log10(np.maximum(stats["r_lf_wnd"], 1e-6))
    out[np.isfinite(s) & (s > thr)] = 0.0   # FA = LF-rich excess -> HIGH stat
    return out

# ---------------- train heads (same seeds as main run) ----------------
print("features + train...", flush=True)
st_tr = excess_stats(X_tr)[2]
Ft_tr, names_t = assemble(X_tr, st_tr)
Fb_tr, nb = featurize(X_tr)
n_base = Fb_tr.shape[1]
mc_b, mr_b = twohead(Fb_tr, f_tr)
mc_t, mr_t = twohead(Ft_tr, f_tr)
R["n_features"] = {"base": int(n_base), "t1t2": int(Ft_tr.shape[1])}

imp = pd.DataFrame({"feat": names_t,
                    "gain": mc_t.feature_importances_ + mr_t.feature_importances_})
imp["block"] = np.where(imp["feat"].str.startswith("t1_"), "T1",
                        np.where(imp["feat"].str.startswith("t2_"), "T2", "base"))
R["importance_by_block"] = imp.groupby("block")["gain"].sum().div(imp["gain"].sum()).round(4).to_dict()
R["top15_features"] = imp.nlargest(15, "gain")[["feat", "gain"]].to_dict("records")
print(json.dumps(R["importance_by_block"]), flush=True)
print(imp.nlargest(12, "gain").to_string(index=False), flush=True)

# ---------------- evaluate everywhere ----------------
def run(tag, X, f):
    f5, fpc, st = excess_stats(X)
    preds = {"e5": f5, "e5pcen": fpc}
    if thr_hi is not None:
        preds["e5gateInv"] = np.clip(e5_gate_inv(f5, st, thr_hi), 0, 1)
    Ft, _ = assemble(X, st)
    preds["lgb_t1t2"] = np.clip(mc_t.predict_proba(Ft)[:, 1] * mr_t.predict(Ft), 0, 1)
    # blend e5gateInv + lgb
    if thr_hi is not None:
        for w in (0.3, 0.5, 0.7):
            preds[f"blend_w{w}"] = np.clip(w * preds["lgb_t1t2"] + (1 - w) * preds["e5gateInv"], 0, 1)
    row = {"n": len(f), "f_mean": float(f.mean())}
    for k, p in preds.items():
        row[f"{k}_rmse"] = rmse(f, p)
        row[f"{k}_rho"] = float(np.corrcoef(p, f)[0, 1])
    R[tag] = row
    print(f"{tag:30} " + " ".join(f"{k}:{row[f'{k}_rmse']:.4f}" for k in preds), flush=True)

for name, tag in [("val_main", "VAL_main_allpool"), ("val_calm", "VAL_calm"),
                  ("val_A_west_moored", "VALclassA_G0"), ("val_B_southcoast_exposed", "VALclassB_G1"),
                  ("val_C_harbour_industrial", "VALclassC_G2"), ("val_D_residual", "VALclassD")]:
    X, f, _ = load(name)
    run(tag, X, f)

# ---------------- TEST diag with inverted gate ----------------
print("TEST...", flush=True)
test = pd.read_csv(f"{BASE}/data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)
TX_lin = 10.0 ** (TX / 10.0)
m01m = np.isnan(TX[:, 0, :]).all(1); m15m = np.isnan(TX[:, 14, :]).all(1)
grp = np.where(m01m, "G1", np.where(m15m, "G2", "G0")).astype("<U2")
f5t, fpct, stt = excess_stats(TX_lin)
Ft_t, _ = assemble(TX_lin, stt)
p_lgb_t = np.clip(mc_t.predict_proba(Ft_t)[:, 1] * mr_t.predict(Ft_t), 0, 1)
p_gate_t = e5_gate_inv(f5t, stt, thr_hi) if thr_hi is not None else f5t
diag = {}
for g in ["G0", "G1", "G2"]:
    m = grp == g
    diag[g] = {"e5": [float(np.nanmean(f5t[m])), float(np.nanpercentile(f5t[m], 50))],
               "gateInv": [float(np.nanmean(p_gate_t[m])), float(np.nanpercentile(p_gate_t[m], 50))],
               "lgb": [float(np.nanmean(p_lgb_t[m])), float(np.nanpercentile(p_lgb_t[m], 50))],
               "fa_killed": float(np.mean((f5t[m] > 0) & (p_gate_t[m] == 0)))}
R["test_diag"] = diag
print(json.dumps(diag, indent=1), flush=True)
R["test_moments"] = {"e5_mean": float(np.nanmean(f5t)), "gateInv_mean": float(np.nanmean(p_gate_t)),
                     "lgb_mean": float(np.nanmean(p_lgb_t)),
                     "E_f2_e5": float(np.nanmean(f5t ** 2)), "E_f2_gate": float(np.nanmean(p_gate_t ** 2)),
                     "pinned_m2": 0.060581047570230605}
print(json.dumps(R["test_moments"]), flush=True)

# centered-shape group agreement (test fingerprints)
gfp = {}
for g in ["G0", "G1", "G2"]:
    idx = np.where(grp == g)[0]
    fp = np.nanmedian(np.stack([bed_profile(TX_lin[i]) for i in idx[:400]]), axis=0)
    gfp[g] = fp
ag = {}
for g, fp in gfp.items():
    fpc_g = fp - fp.mean()
    d_lev = {c.split('_G')[0]: float(np.sqrt(np.nanmean((fp - cfp) ** 2))) for c, cfp in class_fp.items()}
    d_shp = {c.split('_G')[0]: float(np.sqrt(np.nanmean((fpc_g - cfp) ** 2))) for c, cfp in class_fp_c.items()}
    ag[g] = {"level": sorted(d_lev.items(), key=lambda kv: kv[1]),
             "shape": sorted(d_shp.items(), key=lambda kv: kv[1])}
R["group_agreement_level_shape"] = ag
print(json.dumps(ag, indent=1), flush=True)

np.savez(f"{OUT}/r8_test_diag.npz", e5=f5t, e5pcen=fpct, gateInv=p_gate_t,
         lgb_t1t2=p_lgb_t, grp=grp)
json.dump(R, open(f"{OUT}/r8_followup_report.json", "w"), indent=1, default=float)
print("saved ->", f"{OUT}/r8_followup_report.json", flush=True)
