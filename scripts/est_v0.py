#!/usr/bin/env python3
"""Estimator v0: per-window baseline subtraction (station-free, period-free).

Idea (R7): the controlled addition is intermittent within the 15-min window and
the pure background for THAT window lives in its own quiet minutes/bands.
  per band b: B_hat[b] = low quantile over observed minutes (passage-free proxy)
  excess[m,b] = max(0, P[m,b] - B_hat[b])   (linear power)
  f_hat = sum(excess) / sum(P)              over observed cells  (A32 convention)

Self-consistency without labels: if f_hat ~ truth + small noise, then
E[f_hat^2] should land near the pinned m2 = 0.060581 (>= m2 by noise var).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
M2 = (1.0 - 0.753867825) ** 2

test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str})
ids = test["ID"].to_numpy()
X = test.drop(columns=["ID"]).to_numpy(float).reshape(len(test), 15, 25)  # dB, NaN = unobserved
lin = 10.0 ** (X / 10.0)  # linear power

def estimate(lin, q=25.0, floor_only_observed=True):
    """Per-window bandwise low-quantile background + excess share."""
    N, M, B = lin.shape
    f = np.full(N, np.nan)
    excess_sum = np.zeros(N)
    total_sum = np.zeros(N)
    for i in range(N):
        w = lin[i]  # (15,25)
        obs = np.isfinite(w)
        # background per band: quantile over observed minutes
        Bh = np.full(B, np.nan)
        for b in range(B):
            col = w[:, b][obs[:, b]]
            if len(col):
                Bh[b] = np.percentile(col, q)
        exc = np.where(obs, np.maximum(w - Bh[None, :], 0.0), 0.0)
        excess_sum[i] = exc.sum()
        total_sum[i] = np.where(obs, w, 0.0).sum()
        f[i] = excess_sum[i] / total_sum[i] if total_sum[i] > 0 else 0.0
    return f, excess_sum, total_sum

def summarize(name, f):
    q = np.percentile(f, [0, 10, 25, 50, 75, 90, 100])
    print(f"{name:18} mean {f.mean():.4f}  std {f.std():.4f}  E[f2] {np.mean(f**2):.4f} "
          f"(pinned m2 {M2:.4f})  zeros<1e-4: {(f < 1e-4).mean()*100:.1f}%")
    print(f"{'':18} quantiles 0/10/25/50/75/90/100: {np.round(q,4)}")
    return dict(mean=float(f.mean()), std=float(f.std()), e_f2=float(np.mean(f**2)),
                zeros_pct=float((f < 1e-4).mean() * 100),
                q={str(k): float(v) for k, v in zip([0,10,25,50,75,90,100], q)})

# intermittency scan: per-window per-band dynamic range over minutes
print("=== intermittency scan (test windows) ===")
obs = np.isfinite(X)
rng_db = np.nanmax(X, axis=1) - np.nanmin(X, axis=1)   # (N,25) range across minutes
print(f"median per-band (max-min) dB across minutes: p25 {np.nanpercentile(rng_db,25):.1f} "
      f"p50 {np.nanpercentile(rng_db,50):.1f} p75 {np.nanpercentile(rng_db,75):.1f} p95 {np.nanpercentile(rng_db,95):.1f}")
# low-band (1-4) range: vessels live low
print(f"low bands (b0-b3) range p50/p90: {np.nanpercentile(rng_db[:, :4], 50):.1f} / {np.nanpercentile(rng_db[:, :4], 90):.1f} dB")

print("\n=== estimator v0 sweep (quantile for background) ===")
out = {}
for q in [0, 10, 25, 50]:
    f, es, ts = estimate(lin, q=q)
    out[f"q{q}"] = summarize(f"quantile q={q}", f)
    np.save(BASE / f"data/train_v3/est_v0_q{q}_share.npy", f)

# missingness check
print(f"\nm01 NaN fraction (test): {1 - obs[:, 0, :].mean():.3f}; any-NaN windows: {(1-obs.mean(axis=(1,2)) > 0).mean()*100:.1f}%")
json.dump(dict(pinned_m2=M2, intermittency=dict(
    rng_p25=float(np.nanpercentile(rng_db, 25)), rng_p50=float(np.nanpercentile(rng_db, 50)),
    rng_p75=float(np.nanpercentile(rng_db, 75)), rng_p95=float(np.nanpercentile(rng_db, 95)),
    low_band_p50=float(np.nanpercentile(rng_db[:, :4], 50)), low_band_p90=float(np.nanpercentile(rng_db[:, :4], 90))),
    sweep=out), open(BASE / "data/train_v3/est_v0_report.json", "w"), indent=1)
print("\nsaved -> data/train_v3/est_v0_report.json + est_v0_q*_share.npy")
