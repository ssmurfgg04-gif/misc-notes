#!/usr/bin/env python3
"""recipe_discrimination.py — decide between two mixing-recipe hypotheses.

H_A (vessel-shaped addition, R2/R4 generator):  M = B + alpha*V, V from VTUAD
H_B (background-matched addition, hunt-note claim): M = B/(1-f)  (no shape signal)

Experiment P (positive control): plant H_A additions into REAL SA background
windows; the R4 presence head must detect them (AUC high). Guards against
"my model is just broken".

Experiment R (matched-level shape residuals): for each TEST window, find the
nearest public background window by total level; compare band-dB vectors.
  Under H_B: residuals ~ 0 in ALL bands (addition has background's shape).
  Under H_A: positive residuals concentrated in vessel-characteristic bands.
Caveat: matched-level != matched-condition; interpret with the sign structure,
not raw magnitudes. Under H_A, E[residual] >= 0 in EVERY band regardless.
"""
import json, sys, os
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tournament import featurize
from generator_v2 import load_backgrounds, load_refs, transform_reference
import lightgbm as lgb

OUT = "/home/z/my-project/data/train_v2/recipe_discrimination.json"
rng = np.random.default_rng(0)

# ---------------- data ----------------
print("loading backgrounds...", flush=True)
bg, bg_meta = load_backgrounds("/home/z/my-project/data/South_African_Real_Acoustics",
                               per_site_cap=1500, seed=42)
bg_sum_db = 10 * np.log10(bg.astype(np.float64).sum(axis=(1, 2)))
print("bg windows:", bg.shape, flush=True)

test = pd.read_csv("/home/z/my-project/data/Test.csv")
cols = [c for c in test.columns if c != "ID"]
T = test[cols].to_numpy(dtype=np.float64).reshape(-1, 15, 25)
T_lin = 10 ** (T / 10.0)
t_sum_db = 10 * np.log10(np.nansum(T_lin, axis=(1, 2)))  # observed cells only
print("test windows:", T.shape, "| sum dB p50 %.2f vs bg p50 %.2f" %
      (np.median(t_sum_db), np.median(bg_sum_db)), flush=True)

refs = load_refs("/home/z/my-project/data/refs_vtuad_real")
clip_ids = sorted(refs)

# ---------------- Experiment P: plant positive control ----------------
print("training presence head on synth (quick)...", flush=True)
# quick synth subset: 6000 windows from bg pool + vessel-shaped additions
n = 6000
Xs = np.empty((n, 15, 25)); fs = np.empty(n)
for i in range(n):
    B = bg[rng.integers(len(bg))]
    f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
    if f == 0.0:
        Xs[i] = B
    else:
        uid = clip_ids[rng.integers(len(clip_ids))]
        V, _, _ = transform_reference(refs[uid], rng)
        alpha = f / (1 - f) * B.sum() / max(V.sum(), 1e-30)
        Xs[i] = B + alpha * V
    fs[i] = f
Fs, _ = featurize(Xs)
mc = lgb.LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31,
                        random_state=0, verbose=-1, n_jobs=2)
mc.fit(Fs, (fs > 1e-9).astype(int))

# plant into fresh REAL background windows (positive control)
np_ = 2000
Xp = np.empty((np_, 15, 25)); fp = np.empty(np_)
for i in range(np_):
    B = bg[rng.integers(len(bg))]
    f = float(rng.choice([0.1, 0.2, 0.3, 0.4]))
    uid = clip_ids[rng.integers(len(clip_ids))]
    V, _, _ = transform_reference(refs[uid], rng)
    alpha = f / (1 - f) * B.sum() / max(V.sum(), 1e-30)
    Xp[i] = B + alpha * V
    fp[i] = f
Fp, _ = featurize(Xp)
p_plant = mc.predict_proba(Fp)[:, 1]
auc_plant = float(np.mean(p_plant > 0.5))
print("P: planted (f>=0.1) detect rate P(present)>0.5 =", round(auc_plant, 4), flush=True)

# negative control: untouched real backgrounds
Fn, _ = featurize(bg[:2000])
p_bg = mc.predict_proba(Fn)[:, 1]
print("P: real background P(present) p50 =", round(float(np.median(p_bg)), 4), flush=True)

# test windows through the same head
Ft, _ = featurize(T_lin)
p_test = mc.predict_proba(Ft)[:, 1]
print("P: raw TEST P(present) p10/p50/p90 =",
      [round(float(q), 3) for q in np.quantile(p_test, [.1, .5, .9])], flush=True)

# ---------------- Experiment R: matched-level shape residuals ----------------
print("R: matching test windows to backgrounds by total level...", flush=True)
# per test window: nearest bg by |sum_db| difference
order = np.argsort(bg_sum_db)
bg_sorted_db = bg_sum_db[order]
residuals = np.empty((len(T), 25))
matched_d = np.empty(len(T))
for i in range(len(T)):
    j = order[min(np.searchsorted(bg_sorted_db, t_sum_db[i]), len(bg) - 1)]
    # compare the MEDIAN minute of each (robust to trajectory variation)
    t_band_db = 10 * np.log10(np.nanmedian(T_lin[i], axis=0) + 1e-30)
    b_band_db = 10 * np.log10(np.nanmedian(bg[j], axis=0) + 1e-30)
    residuals[i] = t_band_db - b_band_db
    matched_d[i] = abs(t_sum_db[i] - bg_sum_db[j])

med = np.median(residuals, axis=0)
q25 = np.quantile(residuals, 0.25, axis=0)
print("R: median residual per band (dB):", np.round(med, 2).tolist(), flush=True)
print("R: q25 residual per band:", np.round(q25, 2).tolist(), flush=True)
neg_bands = int((med < -0.5).sum())
print("R: bands with median residual < -0.5 dB:", neg_bands, "/25", flush=True)

# control: background-vs-background matched-level residuals (null distribution)
idx = rng.choice(len(bg), size=1500, replace=False)
res_bg = np.empty((1500, 25))
for k, i in enumerate(idx):
    j = order[min(np.searchsorted(bg_sorted_db, bg_sum_db[i]), len(bg) - 1)]
    b1 = 10 * np.log10(np.nanmedian(bg[i], axis=0) + 1e-30)
    b2 = 10 * np.log10(np.nanmedian(bg[j], axis=0) + 1e-30)
    res_bg[k] = b1 - b2
med_bg_null = np.median(res_bg, axis=0)
print("R: null (bg-vs-bg) median residual:", np.round(med_bg_null, 2).tolist(), flush=True)

out = {
    "P_plant_detect_rate": auc_plant,
    "P_bg_p50": float(np.median(p_bg)),
    "P_test_quantiles": [float(q) for q in np.quantile(p_test, [.1, .5, .9])],
    "R_test_median_residual_db": med.tolist(),
    "R_test_q25_residual_db": q25.tolist(),
    "R_null_bg_vs_bg_median_residual_db": med_bg_null.tolist(),
    "R_negative_bands_lt_-0.5dB": neg_bands,
    "R_matched_level_gap_p50_db": float(np.median(matched_d)),
    "verdict_notes": {
        "H_B_predicted": "residuals ~0 all bands (bg shape); negative residuals allowed only as noise",
        "H_A_predicted": "E[residual]>=0 every band; positive excess in vessel bands",
    },
}
with open(OUT, "w") as fh:
    json.dump(out, fh, indent=1)
print("saved ->", OUT, flush=True)
