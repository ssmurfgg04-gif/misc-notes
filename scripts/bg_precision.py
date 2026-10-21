#!/usr/bin/env python3
"""R7 estimator v1, part A: per-window background-energy precision on RAW data.

Question: how precisely can we predict a 15-min window's total linear background
energy sumB (25 competition bands, observed cells) from the window's own HF bands
+ site identity?  The residual = the f-estimation noise floor, since
    f_hat = 1 - sumB_hat/sumM   and on raw windows sumM = sumB (truth f = 0).

Outputs: data/train_v3/bg_precision_report.json
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
RAW = BASE / "data/South_African_Real_Acoustics/South_African_Real_Acoustics/acoustics"
OUT = BASE / "data/train_v3/bg_precision_report.json"
WIN = 15
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))

def comp_band_idx(tol_cols):
    freqs = np.array([float(c.replace("TOL_", "").replace("k", "e3")) for c in tol_cols])
    idx = []
    for cc in CENTRES:
        j = int(np.argmin(np.abs(np.log10(freqs) - np.log10(cc))))
        idx.append(j if abs(np.log10(freqs[j]) - np.log10(cc)) < 0.06 else -1)
    return idx

def site_windows(path):
    df = pd.read_parquet(path)
    df = df[df["file_kind"] == "MinRes"]                      # drop error rows
    tol_cols = [c for c in df.columns if c.startswith("TOL_")]
    keep = [k for k in comp_band_idx(tol_cols) if k >= 0]
    V = df[tol_cols].to_numpy(float)[:, keep]          # (T, <=25) dB, NaN unobserved
    tm = pd.to_datetime(df["t"]).to_numpy().astype("datetime64[m]").astype(np.int64)
    rec = df["recorder"].astype(str).to_numpy()
    # dedupe (recorder, minute): keep first occurrence, preserve time order
    dtmp = pd.DataFrame({"m": tm, "r": rec})
    keep_rows = ~dtmp.duplicated(subset=["r", "m"], keep="first").to_numpy()
    V, tm, rec = V[keep_rows], tm[keep_rows], rec[keep_rows]
    o = np.argsort(tm, kind="stable")
    V, tm, rec = V[o], tm[o], rec[o]
    tmin, tmin_arr = tm, tm
    L = 10.0 ** (V / 10.0)                             # linear power
    wins = []
    i = 0
    T = len(V)
    while i + WIN <= T:
        seg_ok = (tmin[i + WIN - 1] - tmin[i] == WIN - 1) and (len(set(rec[i:i + WIN])) == 1)
        if seg_ok and np.isfinite(L[i:i + WIN]).mean() > 0.9:
            w = L[i:i + WIN]
            obs = np.isfinite(w)
            wins.append(dict(
                sumB=float(np.nansum(w)),
                obs_frac=float(obs.mean()),
                hf_med=float(np.nanmedian(10 * np.log10(np.where(obs, w, np.nan))[:, 15:25])),
                hf_med2=float(np.nanmedian(10 * np.log10(np.where(obs, w, np.nan))[:, 20:25])),
                lf_med=float(np.nanmedian(10 * np.log10(np.where(obs, w, np.nan))[:, 0:10])),
            ))
            i += WIN
        else:
            i += 1
    return pd.DataFrame(wins)

tables = {}
for f in sorted(RAW.glob("*.parquet")):
    d = site_windows(f)
    if len(d) == 0:
        print(f"{f.stem:22} windows      0  SKIPPED (no contiguous 15-min runs)")
        continue
    tables[f.stem] = d
    print(f"{f.stem:22} windows {len(d):6d}  sumB CV {d['sumB'].std()/d['sumB'].mean():.3f}  "
          f"hf~sumB corr {np.corrcoef(np.log10(d['sumB']), d['hf_med'])[0,1]:.3f}")

# per-site anchor models (5-fold CV ridge on log-features), vs naive site-median
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold

def eval_model(X, y):
    kf = KFold(5, shuffle=True, random_state=7)
    pred = np.zeros_like(y)
    for tr, te in kf.split(X):
        m = Ridge(1.0).fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
    return pred

report = {}
res_all, res_naive_all = [], []
for site, d in tables.items():
    y = np.log10(d["sumB"].to_numpy())
    X = np.column_stack([d["hf_med"], d["hf_med2"], d["lf_med"], d["obs_frac"]])
    pred = eval_model(X, y)
    resid = pred - y                       # log10 relative error of sumB_hat
    f_hat_raw = np.clip(1 - 10 ** resid, 0, 1)   # estimator on f=0 windows
    naive = np.full_like(y, y.mean())
    r_naive = naive - y
    row = dict(
        n=int(len(d)),
        sumB_cv=float(d["sumB"].std() / d["sumB"].mean()),
        anchor_resid_p50=float(np.percentile(np.abs(resid), 50)),
        anchor_resid_p90=float(np.percentile(np.abs(resid), 90)),
        naive_resid_p50=float(np.percentile(np.abs(r_naive), 50)),
        fhat_floor_rmse=float(np.sqrt(np.mean(f_hat_raw ** 2))),
        fhat_floor_p50=float(np.percentile(f_hat_raw, 50)),
        fhat_floor_p90=float(np.percentile(f_hat_raw, 90)),
        fhat_floor_p99=float(np.percentile(f_hat_raw, 99)),
    )
    report[site] = row
    res_all.append(resid); res_naive_all.append(r_naive)
    print(f"{site:22} anchor|e|p50 {row['anchor_resid_p50']:.3f} dex (naive {row['naive_resid_p50']:.3f}) "
          f"-> f-hat floor p50 {row['fhat_floor_p50']:.3f} p90 {row['fhat_floor_p90']:.3f} rmse {row['fhat_floor_rmse']:.3f}")

res_all = np.concatenate(res_all); res_naive_all = np.concatenate(res_naive_all)
report["_overall"] = dict(
    anchor_resid_p50=float(np.percentile(np.abs(res_all), 50)),
    anchor_resid_p90=float(np.percentile(np.abs(res_all), 90)),
    naive_resid_p50=float(np.percentile(np.abs(res_naive_all), 50)),
    projected_f_rmse_at_f15=float((1 - 0.15) * 10 ** np.percentile(np.abs(res_all), 50) * 0.8),
    note="projected f error ~ (1-f) * relerr(sumB); rough scaling 0.8 for clipping at 0",
)
json.dump(report, open(OUT, "w"), indent=1)
print("\nOVERALL anchor |resid| p50/p90:",
      f"{report['_overall']['anchor_resid_p50']:.3f} / {report['_overall']['anchor_resid_p90']:.3f} dex",
      f"(naive p50 {report['_overall']['naive_resid_p50']:.3f})")
print("saved ->", OUT)
