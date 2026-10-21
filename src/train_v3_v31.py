#!/usr/bin/env python3
"""train_v3_v31.py — R6: circularity-fixed decision table + honest blend.

FIX (user directive, R4b caveat #2 closed):
  Enforce BACKGROUND-WINDOW-LEVEL GROUP SPLITS in all Sigma-B-hat-family
  validation. Split pool rows G into G_train(80%)/G_val(20%) stratified by
  site (bg_split.csv, seed 7). Every model component (M2 two-head AND
  Sigma-B-hat lock) is trained ONLY on windows/backgrounds from G_train and
  evaluated ONLY on windows/backgrounds from G_val. No synth-val window
  shares its background row with any training input of any component.

Blends swept on the group-split val: p = (1-wL-wC)*M2 + wL*lock + wC*const.
Reported numbers are honest; expect them below the R4b 0.8741.

Pursue-real track (user directive): R_real two-head trained on REAL mixtures
only (real SA background x real VTUAD clip, H_A recipe), with clip-level
ref holdout AND background-window split. Blend R_real + lock on v3 H_B val.

Outputs -> data/train_v3/decision_table_v31.json, blend_report_v31.json,
           submissions r6_*.csv (deployment refits noted in JSON).
"""
import json, os, sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tournament import featurize
from generator_v2 import load_backgrounds, load_refs, transform_reference

OUT = "/home/z/my-project/data/train_v3"
D = "/home/z/my-project/data/synth_v3_mixed"
rng = np.random.default_rng(101)
R = {}


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y, dtype=float) - np.asarray(p, dtype=float)) ** 2)))


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


def predict_twohead(mc, mr, F):
    return np.clip(mc.predict_proba(F)[:, 1] * mr.predict(F), 0, 1)


# ---------------- load synth v3 + group split ----------------
X = np.load(f"{D}/X.npy"); f = np.load(f"{D}/f.npy")
aux = pd.read_csv(f"{D}/aux_with_split.csv")
assert len(aux) == len(f)
print("synth v3:", X.shape, "| splits:", aux["bg_split"].value_counts().to_dict(), flush=True)
F, names = featurize(X)
recipe = aux["recipe"].to_numpy()
va = (aux["bg_split"] == "val").to_numpy()
tr = ~va
split_meta = {"train_windows": int(tr.sum()), "val_windows": int(va.sum()),
              "val_H_B": int((va & (recipe == "H_B")).sum()),
              "val_H_A": int((va & (recipe == "H_A")).sum())}

# ---------------- M2 (group-split protocol) ----------------
mc, mr = twohead(F[tr], f[tr])
p_m2_val = predict_twohead(mc, mr, F[va])
R["M2_mixed_twohead_groupsplit"] = {
    "overall": rmse(f[va], p_m2_val),
    "on_H_A_windows": rmse(f[va][recipe[va] == "H_A"], p_m2_val[recipe[va] == "H_A"]),
    "on_H_B_windows": rmse(f[va][recipe[va] == "H_B"], p_m2_val[recipe[va] == "H_B"]),
    "auc": float(roc_auc_score((f[va] > 1e-9).astype(int), mc.predict_proba(F[va])[:, 1]))}
print("M2 group-split:", json.dumps(R["M2_mixed_twohead_groupsplit"]), flush=True)

# ---------------- M3 lockv2b (Sigma-B-hat, group-split) ----------------
bgfeat = np.load(f"{D}/bgfeat.npy")
bgsplit = pd.read_csv(f"{D}/bg_split.csv")
assert len(bgsplit) == bgfeat.shape[0]
bgsum = pd.read_csv(f"{D}/bg_sums.csv")
y_log = np.log10(bgsum["sumB"].to_numpy())
gtr = (bgsplit["split"] == "train").to_numpy()
gva = ~gtr
# scale-invariant feature subset (48 feats; excludes log_band_mean_*, log_total)
scale_inv = [i for i, n in enumerate(names)
             if not n.startswith("log_band_mean") and n != "log_total"]
assert len(scale_inv) == 48, len(scale_inv)
mlg = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                        subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                        random_state=0, verbose=-1, n_jobs=4)
mlg.fit(bgfeat[gtr][:, scale_inv], y_log[gtr])
err_log = mlg.predict(bgfeat[gva][:, scale_inv]) - y_log[gva]
R["M3_lockv2b_sumB_log10_err_groupsplit"] = {
    "p50": float(np.median(np.abs(err_log))),
    "p90": float(np.quantile(np.abs(err_log), 0.9))}
print("M3 sumB err (group-split, UNSEEN bg rows):",
      json.dumps(R["M3_lockv2b_sumB_log10_err_groupsplit"]), flush=True)

sumB_hat_val = 10 ** mlg.predict(F[va][:, scale_inv])
sumM_val = np.nansum(X[va].astype(np.float64), axis=(1, 2))
p_lock_val = np.clip(1.0 - sumB_hat_val / np.maximum(sumM_val, 1e-30), 0, 1)
R["M3_lockv2b_groupsplit"] = {
    "overall": rmse(f[va], p_lock_val),
    "on_H_B_windows": rmse(f[va][recipe[va] == "H_B"], p_lock_val[recipe[va] == "H_B"]),
    "on_H_A_windows": rmse(f[va][recipe[va] == "H_A"], p_lock_val[recipe[va] == "H_A"])}
ferr = p_lock_val - f[va]
loud = aux["loud_tail"].to_numpy()[va]
R["M3_lockv2b_groupsplit"]["ferr_p50_loudtail"] = float(np.median(ferr[loud]))
R["M3_lockv2b_groupsplit"]["ferr_p50_quiet"] = float(np.median(ferr[~loud]))
print("M3 lock (group-split):", json.dumps(R["M3_lockv2b_groupsplit"]), flush=True)

# ---------------- honest blend sweep (3-component) ----------------
fva = f[va]
hb = recipe[va] == "H_B"
const = float(f[tr].mean())
rows = []
for wL in np.arange(0, 0.45, 0.05):
    for wC in [0.0, 0.1, 0.2, 0.3]:
        wM = 1.0 - wL - wC
        if wM < 0:
            continue
        p = wM * p_m2_val + wL * p_lock_val + wC * const
        rows.append({"w_M2": round(float(wM), 2), "w_lock": round(float(wL), 2),
                     "w_const": round(float(wC), 2),
                     "rmse_overall": rmse(fva, p), "rmse_HB": rmse(fva[hb], p[hb])})
sweep = pd.DataFrame(rows).sort_values("rmse_HB")
sweep.to_csv(f"{OUT}/blend_sweep_v31.csv", index=False)
best = sweep.iloc[0].to_dict()
best["score_HB"] = 1 - best["rmse_HB"]
best["score_overall"] = 1 - best["rmse_overall"]
R["blend_honest_best"] = best
print("HONEST blend best:", json.dumps(best), flush=True)
print(sweep.head(8).to_string(index=False), flush=True)

R["baselines_val"] = {"zero_const": rmse(fva, np.zeros(va.sum())),
                      "mean_const": rmse(fva, np.full(va.sum(), const)),
                      "const_0.2": rmse(fva, np.full(va.sum(), 0.2))}

# ---------------- R_real: real-mixture two-head (pursue-real) ----------------
print("\nbuilding REAL mixtures (real bg x real VTUAD refs, H_A)...", flush=True)
bg_all, bg_meta = load_backgrounds("/home/z/my-project/data/South_African_Real_Acoustics",
                                   per_site_cap=1500, seed=43)
refs = load_refs("/home/z/my-project/data/refs_vtuad_real")
clips = sorted(refs)
cva = set(rng.choice(len(clips), size=int(0.2 * len(clips)), replace=False).tolist())
gval_uids = set(bgsplit.loc[gva, "bg_uid"].tolist())
n_tr, n_va = 12800, 3200
Xr = np.empty((n_tr + n_va, 15, 25), dtype=np.float32)
fr = np.empty(n_tr + n_va)
meta_r = []
for i in range(n_tr + n_va):
    # background: train mixtures from G_train, val mixtures from G_val
    while True:
        bi = int(rng.integers(len(bg_all)))
        if (bi in gval_uids) == (i >= n_tr):
            break
    B = bg_all[bi]
    while True:
        ci = int(rng.integers(len(clips)))
        if (ci in cva) == (i >= n_tr):
            break
    uid = clips[ci]
    f_i = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
    if f_i == 0.0:
        Xr[i] = B
    else:
        V, _, _ = transform_reference(refs[uid], rng)
        alpha = f_i / (1 - f_i) * B.sum() / max(V.sum(), 1e-30)
        Xr[i] = B + alpha * V
    fr[i] = f_i
    meta_r.append({"i": i, "bg_uid": bi, "clip_uid": uid, "f_true": f_i})
    if (i + 1) % 4000 == 0:
        print(f"  real mixtures {i+1}/{n_tr+n_va}", flush=True)
Fr, _ = featurize(Xr)
tr_r = np.arange(n_tr); va_r = np.arange(n_tr, n_tr + n_va)
mc_r, mr_r = twohead(Fr[tr_r], fr[tr_r], seed=1)
p_r_val = predict_twohead(mc_r, mr_r, Fr[va_r])
R["R_real_twohead_clipANDbgsplit"] = {
    "overall": rmse(fr[va_r], p_r_val),
    "auc": float(roc_auc_score((fr[va_r] > 1e-9).astype(int), mc_r.predict_proba(Fr[va_r])[:, 1]))}
print("R_real (clip+bg group-split):", json.dumps(R["R_real_twohead_clipANDbgsplit"]), flush=True)
# R_real on synth H_B val (cross-domain honesty: H_A-trained model vs H_B windows)
p_r_on_v3hb = predict_twohead(mc_r, mr_r, F[va][hb])
R["R_real_on_v3_HB_val"] = rmse(fva[hb], p_r_on_v3hb)
print("R_real on v3 H_B val:", round(R["R_real_on_v3_HB_val"], 4), flush=True)

# real blend sweep: R_real + lock on synth H_B val (decision-relevant)
p_lock_hb = p_lock_val[hb]
rows_r = []
for wL in np.arange(0, 1.01, 0.1):
    p = (1 - wL) * p_r_on_v3hb + wL * p_lock_hb
    rows_r.append({"w_lock": round(float(wL), 2), "rmse_HB": rmse(fva[hb], p)})
sweep_r = pd.DataFrame(rows_r).sort_values("rmse_HB")
sweep_r.to_csv(f"{OUT}/blend_sweep_real_v31.csv", index=False)
R["blend_real_best"] = sweep_r.iloc[0].to_dict()
print("real-blend best:", json.dumps(R["blend_real_best"]), flush=True)

with open(f"{OUT}/decision_table_v31.json", "w") as fh:
    json.dump({"split_meta": split_meta, **R}, fh, indent=1)

# ---------------- deployment refits + submissions ----------------
print("\ndeployment refits (all data) + test inference...", flush=True)
test = pd.read_csv("/home/z/my-project/data/Test.csv")
cols = [c for c in test.columns if c != "ID"]
T = test[cols].to_numpy(dtype=np.float64).reshape(-1, 15, 25)
T_lin = 10 ** (T / 10.0)
Ft, _ = featurize(T_lin)
sub_meta = {}

# lock on ALL bg rows (deployment)
mlg_all = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                            subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                            random_state=0, verbose=-1, n_jobs=4)
mlg_all.fit(bgfeat[:, scale_inv], y_log)
sumB_hat_t = 10 ** mlg_all.predict(Ft[:, scale_inv])
sumM_t = np.nansum(T_lin, axis=(1, 2))
p_lock_t = np.clip(1.0 - sumB_hat_t / np.maximum(sumM_t, 1e-30), 0, 1)

# M2 refit on all synth windows
mc_a, mr_a = twohead(F, f, seed=0)
p_m2_t = predict_twohead(mc_a, mr_a, Ft)
sub = pd.DataFrame({"ID": test["ID"], "share_added_vessel": p_m2_t,
                    "score_added_vessel": np.clip(mc_a.predict_proba(Ft)[:, 1], 0, 1)})
sub.to_csv(f"{OUT}/submission_r6_v1_mixed.csv", index=False)
sub_meta["r6_v1_mixed"] = {"q10/50/90": [float(q) for q in np.quantile(p_m2_t, [.1, .5, .9])]}

# blend at honest best w (deployment refit)
wL, wC = best["w_lock"], best["w_const"]
wM = 1 - wL - wC
p_blend_t = np.clip(wM * p_m2_t + wL * p_lock_t + wC * const, 0, 1)
pd.DataFrame({"ID": test["ID"], "share_added_vessel": p_blend_t,
              "score_added_vessel": np.clip(mc_a.predict_proba(Ft)[:, 1], 0, 1)}
             ).to_csv(f"{OUT}/submission_r6_v2_blend.csv", index=False)
sub_meta["r6_v2_blend"] = {"w": [float(wM), float(wL), float(wC)],
                           "q10/50/90": [float(q) for q in np.quantile(p_blend_t, [.1, .5, .9])]}

# R_real refit on all real mixtures
mc_r2, mr_r2 = twohead(Fr, fr, seed=1)
p_r_t = predict_twohead(mc_r2, mr_r2, Ft)
pd.DataFrame({"ID": test["ID"], "share_added_vessel": p_r_t,
              "score_added_vessel": np.clip(mc_r2.predict_proba(Ft)[:, 1], 0, 1)}
             ).to_csv(f"{OUT}/submission_r6_v3_real.csv", index=False)
sub_meta["r6_v3_real"] = {"q10/50/90": [float(q) for q in np.quantile(p_r_t, [.1, .5, .9])]}

# real blend at honest best w_lock (R_real + lock)
wL_r = float(R["blend_real_best"]["w_lock"])
p_rb_t = np.clip((1 - wL_r) * p_r_t + wL_r * p_lock_t, 0, 1)
pd.DataFrame({"ID": test["ID"], "share_added_vessel": p_rb_t,
              "score_added_vessel": np.clip(mc_r2.predict_proba(Ft)[:, 1], 0, 1)}
             ).to_csv(f"{OUT}/submission_r6_v4_blend_real.csv", index=False)
sub_meta["r6_v4_blend_real"] = {"w_lock": wL_r,
                                "q10/50/90": [float(q) for q in np.quantile(p_rb_t, [.1, .5, .9])]}

rep = {"decision_table": {**R}, "submissions": sub_meta,
       "protocol": "background-window-level group splits (seed 7) enforced for "
                   "every component; deployment refits use all data but all "
                   "REPORTED metrics come from the split protocol"}
with open(f"{OUT}/blend_report_v31.json", "w") as fh:
    json.dump(rep, fh, indent=1)
print(json.dumps(sub_meta, indent=1), flush=True)
print("DONE", flush=True)
