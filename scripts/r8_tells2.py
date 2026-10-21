#!/usr/bin/env python3
"""r8_tells2.py — disambiguation follow-ups on the R8 tells.

  1. Partial-NaN census: which windows have internal (non-edge) missing minutes?
  2. Recalibrated vessel-proxy sweep (excess thresholds 6/10/14 dB) per test
     group and per train site -> per-station vessel-activity prior.
  3. Within-group 2-cluster characterization: per-cluster P20 broadband, tilt,
     and whether the centroid difference is a flat SHIFT (level/state factor)
     or a SHAPE change (different environment/station).
Output: docs/r8_tells2.json + digest.
"""
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA

ROOT = "/home/z/my-project"
PK = f"{ROOT}/data/sa_package"
BANDS = [31.6, 39.8, 50.1, 63.1, 79.4, 100, 125.9, 158.5, 199.5, 251.2, 316.2,
         398.1, 501.2, 631, 794.3, 1000, 1258.9, 1584.9, 1995.3, 2511.9,
         3162.3, 3981.1, 5011.9, 6309.6, 7943.3]
LOW = slice(0, 10)
R = {"round": "R8", "date": "2026-10-21"}

t = pd.read_csv(f"{PK}/Test.csv")
mins = [f"m{i:02d}" for i in range(1, 16)]
m01_na = t[[c for c in t.columns if c.startswith("m01_")]].isna().all(axis=1)
m15_na = t[[c for c in t.columns if c.startswith("m15_")]].isna().all(axis=1)
t["g"] = np.select([m01_na & ~m15_na, ~m01_na & m15_na, m01_na & m15_na],
                   ["G1_m01miss", "G2_m15miss", "NOISE_both"], default="G0_full")

# any-NaN census across all minutes
any_nan = t[[f"{m}_TOL_{b}" for m in mins for b in BANDS]].isna().any(axis=1)
per_win_nan_min = t[[f"{m}_TOL_31.6" for m in mins]].isna().sum(axis=1)
R["nan_census"] = {
    "windows_with_any_nan": int(any_nan.sum()),
    "windows_missing_only_m01": int((m01_na & ~m15_na).sum()),
    "windows_missing_only_m15": int((~m01_na & m15_na).sum()),
    "windows_missing_both": int((m01_na & m15_na).sum()),
    "windows_with_partial_minute_nan_other": int((any_nan & ~m01_na & ~m15_na).sum()),
    "nan_minute_count_distribution": per_win_nan_min[per_win_nan_min > 0].value_counts().to_dict(),
}

band_cols = [f"{m}_TOL_{b}" for m in mins for b in BANDS]
X = t[band_cols].values.reshape(len(t), 15, 25).astype(float)

def p20(a, axis=0):
    return np.nanpercentile(a, 20, axis=axis)

# recalibrated vessel proxies
vp = {}
for g in ["G0_full", "G1_m01miss", "G2_m15miss"]:
    sel = (t["g"] == g).values
    flat = X[sel].reshape(-1, 25)
    fp = p20(flat)
    qb_low = np.mean(10 ** (fp[LOW] / 10))
    minute_low = np.nanmean(10 ** (X[sel][:, :, LOW] / 10), axis=2)
    excess = 10 * np.log10(minute_low / qb_low)
    vp[g] = {f"bump_rate_thr{thr}": round(float(np.nanmean(excess > thr)), 4)
             for thr in [6, 10, 14]}
R["test_vessel_proxy_recal"] = vp

import os
ac = f"{PK}/South_African_Real_Acoustics/acoustics"
tvp = {}
for fn in sorted(os.listdir(ac)):
    if not fn.endswith(".parquet"):
        continue
    site = fn.replace(".parquet", "")
    df = pd.read_parquet(f"{ac}/{fn}", columns=[f"TOL_{b}" for b in BANDS])
    A = df.values.astype(float)
    sf = p20(A)
    qb_low = np.mean(10 ** (sf[LOW] / 10))
    minute_low = np.nanmean(10 ** (A[:, LOW] / 10), axis=1)
    excess = 10 * np.log10(minute_low / qb_low)
    tvp[site] = {f"bump_rate_thr{thr}": round(float(np.nanmean(excess > thr)), 4)
                 for thr in [6, 10, 14]}
R["train_vessel_proxy_recal"] = tvp

# within-group split characterization
logf = np.log10(BANDS)
sub = {}
for g in ["G0_full", "G1_m01miss", "G2_m15miss"]:
    sel = (t["g"] == g).values
    F = np.nanpercentile(X[sel], 40, axis=1)
    Fc = np.nan_to_num((F - F.mean(0)) / (F.std(0) + 1e-9))
    lab = KMeans(n_clusters=2, n_init=5, random_state=0).fit_predict(
        PCA(n_components=5, random_state=0).fit_transform(Fc))
    out = {}
    cdiff = []
    for k in [0, 1]:
        Fk = F[lab == k]
        fp = p20(Fk)
        bb = 10 * np.log10(np.mean(10 ** (fp / 10)))
        tilt = float(np.polyfit(logf, fp, 1)[0])
        out[f"c{k}"] = dict(n=int((lab == k).sum()), p20_bb_db=round(float(bb), 2),
                            tilt_db_dec=round(tilt, 2))
        cdiff.append(fp)
    diff = cdiff[0] - cdiff[1]
    flat = np.full(25, diff.mean())
    shape_resid = float(np.linalg.norm(diff - flat))
    shift_frac = float(np.linalg.norm(flat) / (np.linalg.norm(diff) + 1e-12))
    out["centroid_diff_flat_shift_fraction"] = round(shift_frac, 3)
    out["centroid_diff_shape_residual_db"] = round(shape_resid, 2)
    out["reading"] = ("level/state factor (flat shift dominates)"
                      if shift_frac > 0.7 else
                      "shape difference (possible distinct environment)")
    sub[g] = out
R["split_characterization"] = sub

with open(f"{ROOT}/docs/r8_tells2.json", "w") as f:
    json.dump(R, f, indent=1)
print(json.dumps({k: R[k] for k in ["nan_census", "test_vessel_proxy_recal",
                                    "split_characterization"]}, indent=1))
print("\ntrain bump thr10:")
for s, v in sorted(tvp.items(), key=lambda kv: -kv[1]["bump_rate_thr10"]):
    print(f"  {s}: {v['bump_rate_thr10']}")
