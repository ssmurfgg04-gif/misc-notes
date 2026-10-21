#!/usr/bin/env python3
"""train_v3.py — recipe-robust candidates + decision table (R4/R5 bridge).

Candidates:
  M1 two-head on synth v2 PRIMARY (H_A only)          [existing submission_r4_v1]
  M2 two-head on synth v3 MIXED (H_A + H_B, loud-tail) [this script]
  M3 lock-v2: conditional sumB-hat regressor on REAL pool backgrounds
     (shape features -> log sumB), f = 1 - sumB_hat/sumM   [H_B-optimal]

Evaluation: synth v3 val split per RECIPE (H_A windows vs H_B windows) +
site-held-out protocol for M3 (test stations may be unseen).
Baselines: zero-const 0.244 / mean-const 0.141 / best-const-0.2 = 0.141.

Outputs: decision table json + three submission CSVs (user picks after smoke test).
"""
import json, os, sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tournament import featurize

OUT = "/home/z/my-project/data/train_v3"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(2)
R = {}


def rmse(y, p):
    return float(np.sqrt(np.mean((np.asarray(y, dtype=float) - np.asarray(p, dtype=float)) ** 2)))


def twohead(Ftr, ftr):
    y = (ftr > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=0, verbose=-1, n_jobs=2)
    mc.fit(Ftr, y)
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=0, verbose=-1, n_jobs=2)
    mr.fit(Ftr[y == 1], ftr[y == 1])
    return mc, mr


def predict_twohead(mc, mr, F):
    return np.clip(mc.predict_proba(F)[:, 1] * mr.predict(F), 0, 1)


# ---------------- load mixed synth ----------------
d = "/home/z/my-project/data/synth_v3_mixed"
X = np.load(f"{d}/X.npy"); f = np.load(f"{d}/f.npy")
aux = pd.read_csv(f"{d}/aux.csv")
print("mixed synth", X.shape, flush=True)
F, names = featurize(X)
recipe = aux["recipe"].to_numpy()
sites = aux["site"].astype(str).to_numpy()

# hold out 20% windows (stratified by recipe) for per-recipe val
va = np.zeros(len(f), dtype=bool)
for r_ in ("H_A", "H_B"):
    idx = np.where(recipe == r_)[0]
    va[rng.choice(idx, size=int(0.2 * len(idx)), replace=False)] = True
tr = ~va

# ---------------- M2: two-head on mixed ----------------
mc, mr = twohead(F[tr], f[tr])
p_m2 = predict_twohead(mc, mr, F[va])
R["M2_mixed_twohead"] = {
    "overall": rmse(f[va], p_m2),
    "on_H_A_windows": rmse(f[va][recipe[va] == "H_A"], p_m2[recipe[va] == "H_A"]),
    "on_H_B_windows": rmse(f[va][recipe[va] == "H_B"], p_m2[recipe[va] == "H_B"]),
    "auc": float(roc_auc_score((f[va] > 1e-9).astype(int), mc.predict_proba(F[va])[:, 1]))}
print("M2:", json.dumps(R["M2_mixed_twohead"]), flush=True)

# ---------------- M3: lock-v2 conditional sumB regressor ----------------
bgfeat = np.load(f"{d}/bgfeat.npy")
bg = pd.read_csv(f"{d}/bg_sums.csv")
y_log = np.log10(bg["sumB"].to_numpy())
bsite = bg["site"].astype(str).to_numpy()
us = np.unique(bsite)
hold_s = set(rng.choice(us, size=2, replace=False).tolist())
tr_s = ~np.isin(bsite, list(hold_s))
mlg = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                        subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                        random_state=0, verbose=-1, n_jobs=2)
mlg.fit(bgfeat[tr_s], y_log[tr_s])
# sumB-hat error on held-out sites (log10 dB):
err_log = mlg.predict(bgfeat[~tr_s]) - y_log[~tr_s]
R["M3_lockv2_sumB_log10_err"] = {"site_heldout_p50": float(np.median(np.abs(err_log))),
                                 "site_heldout_p90": float(np.quantile(np.abs(err_log), 0.9))}
print("M3 sumB err:", json.dumps(R["M3_lockv2_sumB_log10_err"]), flush=True)

# f_lock2 on mixed-synth val: features of the MIXED window -> sumB_hat -> f
sumM = np.nansum(X[va].astype(np.float64), axis=(1, 2))
sumB_hat = 10 ** mlg.predict(F[va])
p_m3 = np.clip(1.0 - sumB_hat / np.maximum(sumM, 1e-30), 0, 1)
R["M3_lockv2"] = {
    "overall": rmse(f[va], p_m3),
    "on_H_B_windows": rmse(f[va][recipe[va] == "H_B"], p_m3[recipe[va] == "H_B"]),
    "on_H_A_windows": rmse(f[va][recipe[va] == "H_A"], p_m3[recipe[va] == "H_A"])}
print("M3:", json.dumps(R["M3_lockv2"]), flush=True)

# M3 residual f-error vs window loudness (is the lock biased in the loud tail?)
ferr = p_m3 - f[va]
loud = aux["loud_tail"].to_numpy()[va]
R["M3_lockv2"]["ferr_p50_loudtail"] = float(np.median(ferr[loud]))
R["M3_lockv2"]["ferr_p50_quiet"] = float(np.median(ferr[~loud]))

# ---------------- baselines on same val ----------------
R["baselines"] = {"zero_const": rmse(f[va], np.zeros(va.sum())),
                  "mean_const": rmse(f[va], np.full(va.sum(), f[tr].mean())),
                  "const_0.2": rmse(f[va], np.full(va.sum(), 0.2))}

# ---------------- M1 reference (H_A-only model on this mixed val) ----------------
# quick retrain of the primary H_A model for an apples-to-apples row
dv2 = "/home/z/my-project/data/synth_v2/G_unif_04"
X2 = np.load(f"{dv2}/X.npy"); f2 = np.load(f"{dv2}/f.npy")
F2, _ = featurize(X2)
mc1, mr1 = twohead(F2, f2)
p_m1 = predict_twohead(mc1, mr1, F[va])
R["M1_HA_twohead"] = {
    "overall": rmse(f[va], p_m1),
    "on_H_A_windows": rmse(f[va][recipe[va] == "H_A"], p_m1[recipe[va] == "H_A"]),
    "on_H_B_windows": rmse(f[va][recipe[va] == "H_B"], p_m1[recipe[va] == "H_B"])}
print("M1:", json.dumps(R["M1_HA_twohead"]), flush=True)

# ---------------- test inference for M2 / M3 / M1 ----------------
test = pd.read_csv("/home/z/my-project/data/Test.csv")
cols = [c for c in test.columns if c != "ID"]
T = test[cols].to_numpy(dtype=np.float64).reshape(-1, 15, 25)
T_lin = 10 ** (T / 10.0)
Ft, _ = featurize(T_lin)

for name, model in [("r4_v2_mixed", (mc, mr)), ("r4_v3_HA", (mc1, mr1))]:
    p = predict_twohead(model[0], model[1], Ft)
    sub = pd.DataFrame({"ID": test["ID"], "share_added_vessel": p,
                        "score_added_vessel": np.clip(model[0].predict_proba(Ft)[:, 1], 0, 1)})
    sub.to_csv(f"{OUT}/submission_{name}.csv", index=False)
    R[f"submission_{name}"] = {"mean_share": float(p.mean()),
                               "quantiles": {str(q): float(np.quantile(p, q)) for q in [0.1, 0.5, 0.9]}}

sumB_hat_t = 10 ** mlg.predict(Ft)
sumM_t = np.nansum(T_lin, axis=(1, 2))
p_l2 = np.clip(1.0 - sumB_hat_t / np.maximum(sumM_t, 1e-30), 0, 1)
pd.DataFrame({"ID": test["ID"], "share_added_vessel": p_l2,
              "score_added_vessel": np.zeros(len(p_l2))}).to_csv(
    f"{OUT}/submission_r4_v4_lockv2.csv", index=False)
R["submission_r4_v4_lockv2"] = {"mean_share": float(p_l2.mean()),
                                "quantiles": {str(q): float(np.quantile(p_l2, q)) for q in [0.1, 0.5, 0.9]}}

with open(f"{OUT}/decision_table.json", "w") as fh:
    json.dump(R, fh, indent=1)
print(json.dumps(R, indent=1))
