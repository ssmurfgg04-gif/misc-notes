#!/usr/bin/env python3
"""R7 detective: is the 16-dB within-window variation in TEST windows natural
(present in raw backgrounds) or constructed (= the controlled addition)?

Compare per-15-min-window per-band (max-min) dB between:
  (a) raw training-release recordings (10 sites, no controlled additions), and
  (b) the 1,500 test windows.
Both restricted to the 25 competition band centres (31.6 .. 7943 Hz).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
RAW = BASE / "data/South_African_Real_Acoustics/South_African_Real_Acoustics/acoustics"
COMP_CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))  # 31.6 .. 7943 Hz

def comp_band_cols(tol_cols):
    """Map raw TOL columns to the 25 competition centres (nearest in log10)."""
    freqs = np.array([float(c.replace("TOL_", "").replace("k", "e3")) for c in tol_cols])
    out = []
    for cc in COMP_CENTRES:
        j = int(np.argmin(np.abs(np.log10(freqs) - np.log10(cc))))
        out.append(j if abs(np.log10(freqs[j]) - np.log10(cc)) < 0.06 else -1)
    return out

def window_ranges(vals_db, win=15):
    """vals_db: (T, B) minute x band dB with NaN; contiguous non-NaN 15-min windows."""
    T, B = vals_db.shape
    rngs, starts = [], []
    i = 0
    while i + win <= T:
        w = vals_db[i:i + win]
        if np.isfinite(w).mean() > 0.95:
            r = np.nanmax(w, axis=0) - np.nanmin(w, axis=0)
            rngs.append(r)
            starts.append(i)
            i += win
        else:
            i += 1
    return np.array(rngs), starts

# (a) raw backgrounds
all_raw = []
per_site = {}
for f in sorted(RAW.glob("*.parquet")):
    df = pd.read_parquet(f)
    tol_cols = [c for c in df.columns if c.startswith("TOL_")]
    keep = comp_band_cols(tol_cols)
    vals = df[tol_cols].to_numpy(float)[:, [k for k in keep if k >= 0]]
    # convert to the competition's dB convention if needed (they are already dB TOLs)
    rngs, _ = window_ranges(vals, 15)
    if len(rngs):
        per_site[f.stem] = dict(n=len(rngs), p50=float(np.nanpercentile(rngs, 50)),
                                p25=float(np.nanpercentile(rngs, 25)),
                                p75=float(np.nanpercentile(rngs, 75)))
        all_raw.append(rngs)
        print(f"{f.stem:24} n15min={len(rngs):6d}  band-range p25/p50/p75 = "
              f"{per_site[f.stem]['p25']:.1f}/{per_site[f.stem]['p50']:.1f}/{per_site[f.stem]['p75']:.1f} dB")

raw_all = np.vstack(all_raw)
print(f"\nRAW BACKGROUND overall: n={len(raw_all)} windows, per-band range "
      f"p25 {np.nanpercentile(raw_all,25):.1f} / p50 {np.nanpercentile(raw_all,50):.1f} / "
      f"p75 {np.nanpercentile(raw_all,75):.1f} / p95 {np.nanpercentile(raw_all,95):.1f} dB")

# (b) test windows (same stat as est_v0 scan)
test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str})
X = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, 15, 25)
rngs_test = np.nanmax(X, axis=1) - np.nanmin(X, axis=1)
print(f"TEST WINDOWS: n={len(rngs_test)}, per-band range "
      f"p25 {np.nanpercentile(rngs_test,25):.1f} / p50 {np.nanpercentile(rngs_test,50):.1f} / "
      f"p75 {np.nanpercentile(rngs_test,75):.1f} / p95 {np.nanpercentile(rngs_test,95):.1f} dB")

json.dump(dict(raw_per_site=per_site,
               raw_overall=dict(p25=float(np.nanpercentile(raw_all,25)), p50=float(np.nanpercentile(raw_all,50)),
                                p75=float(np.nanpercentile(raw_all,75)), p95=float(np.nanpercentile(raw_all,95)),
                                n=int(len(raw_all))),
               test=dict(p25=float(np.nanpercentile(rngs_test,25)), p50=float(np.nanpercentile(rngs_test,50)),
                         p75=float(np.nanpercentile(rngs_test,75)), p95=float(np.nanpercentile(rngs_test,95)),
                         n=int(len(rngs_test)))),
          open(BASE / "data/train_v3/variation_comparison.json", "w"), indent=1)
print("\nsaved -> data/train_v3/variation_comparison.json")
