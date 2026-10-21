#!/usr/bin/env python3
"""r8_tells.py — R8 Rainbolt tell-mining on the 1,500 test windows.

Steps:
  1. Rebuild the 3 export-fingerprint groups (m01/m15 missingness) + noise.
  2. Per-group 25-band quiet-bed fingerprint (P20 per band) + broadband + tilt.
  3. Within-group substructure tests (KMeans k=2 silhouette + GMM BIC delta)
     -> duplicate/second-site check in band space (not just broadband).
  4. Vessel-proxy per group and per train site (low-band excess over site P20,
     >6 dB = bump; window share proxy = mean over minutes).
  5. Shape-space matching to the 10 train sites (centered 25-band P20 vectors,
     L2) with fall-off margins d2-d1, d3-d1 -> decision-tree branch quality.
  6. ID-order contiguity tell (run-length of group sequence along ID).

Output: docs/r8_tells.json (+ stdout digest).
"""
import json
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.mixture import GaussianMixture

ROOT = "/home/z/my-project"
PK = f"{ROOT}/data/sa_package"
OUT = f"{ROOT}/docs/r8_tells.json"
BANDS = [31.6, 39.8, 50.1, 63.1, 79.4, 100, 125.9, 158.5, 199.5, 251.2, 316.2,
         398.1, 501.2, 631, 794.3, 1000, 1258.9, 1584.9, 1995.3, 2511.9,
         3162.3, 3981.1, 5011.9, 6309.6, 7943.3]
LOW = slice(0, 10)  # 31.6..630 Hz vessel-band slice (first 10 bands)
rng = np.random.default_rng(7)

R = {"round": "R8", "date": "2026-10-21"}

# ---------- load test ----------
t = pd.read_csv(f"{PK}/Test.csv")
mins = [f"m{i:02d}" for i in range(1, 16)]
m01 = t[[c for c in t.columns if c.startswith("m01_")]]
m15 = t[[c for c in t.columns if c.startswith("m15_")]]
m01_na = m01.isna().all(axis=1)
m15_na = m15.isna().all(axis=1)
t["g"] = np.select(
    [m01_na & ~m15_na, ~m01_na & m15_na, m01_na & m15_na],
    ["G1_m01miss", "G2_m15miss", "NOISE_both"],
    default="G0_full")
R["group_counts"] = t["g"].value_counts().to_dict()

band_cols = [f"{m}_TOL_{b}" for m in mins for b in BANDS]
# values in dB; wide -> long minutes
X = t[band_cols].values.reshape(len(t), 15, 25).astype(float)

def p20(a, axis=0):
    return np.nanpercentile(a, 20, axis=axis)

groups = {}
for g in ["G0_full", "G1_m01miss", "G2_m15miss", "NOISE_both"]:
    sel = t["g"].values == g
    if sel.sum() == 0:
        continue
    Xm = X[sel]  # n_win x 15 x 25
    flat = Xm.reshape(-1, 25)
    fp = p20(flat)  # 25-vector quiet bed
    bb = float(np.mean(10 ** (fp / 10)))  # linear mean of band powers
    bb_db = 10 * np.log10(bb)
    logf = np.log10(BANDS)
    tilt = float(np.polyfit(logf, fp, 1)[0])
    # vessel proxy: low-band excess per minute over group quiet bed
    qb_low = np.mean(10 ** (fp[LOW] / 10))
    minute_low = np.nanmean(10 ** (Xm[:, :, LOW] / 10), axis=2)  # n x 15
    excess = 10 * np.log10(minute_low / qb_low)
    bump_rate = float(np.nanmean(excess > 6))          # per-minute bump rate
    win_share = float(np.nanmean(np.nanmean(excess > 6, axis=1)))
    win_share_p90 = float(np.nanpercentile(np.nanmean(excess > 6, axis=1), 90))
    groups[g] = dict(n=int(sel.sum()), fingerprint_db=[round(float(v), 2) for v in fp],
                     broadband_db=round(bb_db, 2), tilt_db_dec=round(tilt, 2),
                     bump_rate_min=round(bump_rate, 4),
                     win_share_proxy_mean=round(win_share, 4),
                     win_share_proxy_p90=round(win_share_p90, 4))
R["test_groups"] = groups

# ---------- within-group substructure (band space) ----------
sub = {}
for g in ["G0_full", "G1_m01miss", "G2_m15miss"]:
    sel = t["g"].values == g
    if sel.sum() < 40:
        continue
    # window-level feature: per-window P40 per band (robust)
    F = np.nanpercentile(X[sel], 40, axis=1)  # n x 25
    Fc = (F - F.mean(0)) / (F.std(0) + 1e-9)
    Fc = np.nan_to_num(Fc)
    Z = PCA(n_components=5, random_state=0).fit_transform(Fc)
    km = KMeans(n_clusters=2, n_init=5, random_state=0).fit(Z)
    sil2 = float(silhouette_score(Z, km.labels_, sample_size=min(2000, len(Z)), random_state=0))
    gm1 = GaussianMixture(1, random_state=0).fit(Z)
    gm2 = GaussianMixture(2, random_state=0).fit(Z)
    dbic = float(gm2.bic(Z) - gm1.bic(Z))  # >0 => 1 component preferred
    sub[g] = dict(k2_silhouette=round(sil2, 3), gm_bic_delta_2minus1=round(dbic, 1),
                  split_sizes=[int((km.labels_ == 0).sum()), int((km.labels_ == 1).sum())])
R["substructure"] = sub

# ---------- train site fingerprints + shape-space matching ----------
ac = f"{PK}/South_African_Real_Acoustics/acoustics"
sites = {}
import os
for fn in sorted(os.listdir(ac)):
    if not fn.endswith(".parquet"):
        continue
    site = fn.replace(".parquet", "")
    df = pd.read_parquet(f"{ac}/{fn}", columns=[f"TOL_{b}" for b in BANDS])
    A = df.values.astype(float)
    fp = p20(A)
    sites[site] = fp
R["train_fingerprints"] = {k: [round(float(v), 2) for v in v_]
                           for k, v_ in sites.items()}

match = {}
for g, gi in groups.items():
    if g == "NOISE_both":
        continue
    fp = np.array(gi["fingerprint_db"])
    c = fp - fp.mean()
    d_shape, d_level = {}, {}
    for s, sf in sites.items():
        d_shape[s] = float(np.linalg.norm(c - (sf - sf.mean())))
        d_level[s] = float(np.linalg.norm(fp - sf))
    top_shape = sorted(d_shape.items(), key=lambda kv: kv[1])
    top_level = sorted(d_level.items(), key=lambda kv: kv[1])
    match[g] = {
        "shape_top4": [(s, round(d, 2)) for s, d in top_shape[:4]],
        "shape_margin_d2_d1": round(top_shape[1][1] - top_shape[0][1], 2),
        "level_top4": [(s, round(d, 2)) for s, d in top_level[:4]],
        "level_margin_d2_d1": round(top_level[1][1] - top_level[0][1], 2),
    }
R["matching_margins"] = match

# ---------- train site vessel proxies (same estimator) ----------
tvp = {}
for s, sf in sites.items():
    df = pd.read_parquet(f"{ac}/{s}.parquet", columns=[f"TOL_{b}" for b in BANDS])
    A = df.values.astype(float)
    qb_low = np.mean(10 ** (sf[LOW] / 10))
    minute_low = np.nanmean(10 ** (A[:, LOW] / 10), axis=1)
    excess = 10 * np.log10(minute_low / qb_low)
    tvp[s] = dict(bump_rate_min=round(float(np.nanmean(excess > 6)), 4),
                  n_min=int(A.shape[0]))
R["train_vessel_proxy"] = tvp

# ---------- ID contiguity tell ----------
seq = t["g"].values
runs, cur, n = [], seq[0], 1
for v in seq[1:]:
    if v == cur:
        n += 1
    else:
        runs.append((cur, n)); cur, n = v, 1
runs.append((cur, n))
R["id_order"] = {"n_runs": len(runs), "max_run": max(n for _, n in runs),
                 "first_20_runs": runs[:20]}

with open(OUT, "w") as f:
    json.dump(R, f, indent=1)

print(json.dumps({k: R[k] for k in ["group_counts", "substructure",
                                    "matching_margins", "id_order"]}, indent=1))
print("vessel proxies:")
for g, gi in groups.items():
    print(f"  {g}: bump/min={gi['bump_rate_min']}, shareP90={gi['win_share_proxy_p90']}")
print("saved ->", OUT)
