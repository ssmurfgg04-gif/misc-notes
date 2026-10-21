#!/usr/bin/env python3
"""Profile South African acoustics parquet files + Test.csv.
Outputs a compact JSON + markdown summary to /home/z/my-project/data/profile/.
"""
import pandas as pd
import numpy as np
import json, os, glob

DATA = "/home/z/my-project/data/South_African_Real_Acoustics"
OUT = "/home/z/my-project/data/profile"
os.makedirs(OUT, exist_ok=True)

report = {}

# ---------- stations & recorders ----------
stations = pd.read_csv(f"{DATA}/stations.csv")
recorders = pd.read_csv(f"{DATA}/recorders.csv")
report["stations"] = stations.to_dict(orient="records")
report["recorders"] = recorders.to_dict(orient="records")

# ---------- per-site parquet profiling ----------
site_rows = []
for f in sorted(glob.glob(f"{DATA}/acoustics/*.parquet")):
    site = os.path.basename(f).replace(".parquet", "")
    df = pd.read_parquet(f)
    tol_cols = [c for c in df.columns if c.startswith("TOL_")]
    r = {
        "site": site,
        "rows": len(df),
        "cols": len(df.columns),
        "n_tol_cols": len(tol_cols),
        "recorders": int(df["recorder"].nunique()) if "recorder" in df else None,
        "recorder_ids": df["recorder"].dropna().unique().tolist()[:12] if "recorder" in df else None,
        "file_kinds": df["file_kind"].value_counts().to_dict() if "file_kind" in df else None,
        "t_min": str(df["t"].min()) if "t" in df else None,
        "t_max": str(df["t"].max()) if "t" in df else None,
        "dur_stats": {
            "mean": round(float(df["dur"].mean()), 1) if "dur" in df else None,
            "frac_ge55": round(float((df["dur"] >= 55).mean()), 4) if "dur" in df else None,
        },
    }
    # band availability: count finite per band
    if tol_cols:
        finite_frac = {c: round(float(df[c].notna().mean()), 3) for c in tol_cols}
        r["band_finite_frac"] = finite_frac
        vals = df[tol_cols].to_numpy().ravel()
        vals = vals[np.isfinite(vals)]
        r["tol_levels"] = {
            "p01": round(float(np.percentile(vals, 1)), 1),
            "p50": round(float(np.percentile(vals, 50)), 1),
            "p99": round(float(np.percentile(vals, 99)), 1),
            "min": round(float(vals.min()), 1), "max": round(float(vals.max()), 1),
        }
        r["n_below_zero"] = int((vals < 0).sum())
        if (vals < 0).any():
            neg = vals[vals < 0]
            uniq, cnts = np.unique(np.round(neg, 2), return_counts=True)
            top = sorted(zip(cnts, uniq), reverse=True)[:5]
            r["negative_sentinels"] = {str(v): int(c) for c, v in top}
    for q in ["qc_duration_ge55", "qc_25band_finite", "qc_25band_spread_ge6"]:
        if q in df.columns:
            r.setdefault("qc", {})[q] = round(float(df[q].mean()), 4)
    site_rows.append(r)
    del df

report["sites"] = site_rows

# ---------- Test.csv ----------
test = pd.read_csv("/home/z/my-project/data/Test.csv")
tol_cols = [c for c in test.columns if c != "ID"]
miss = test[tol_cols].isna()
report["test"] = {
    "rows": len(test),
    "n_feature_cols": len(tol_cols),
    "missing_frac": round(float(miss.mean().mean()), 4),
    "rows_with_any_missing": round(float(miss.any(axis=1).mean()), 4),
    "min_val": round(float(np.nanmin(test[tol_cols].to_numpy())), 1),
    "max_val": round(float(np.nanmax(test[tol_cols].to_numpy())), 1),
}
# missingness by minute and by band position (features are minute-major: m01_TOL_31.6, m01_TOL_40, ...)
bands25 = sorted({c.split("TOL_")[1] for c in tol_cols}, key=lambda x: float(x))
by_min, by_band = [], []
for i in range(1, 16):
    cols = [c for c in tol_cols if c.startswith(f"m{i:02d}_")]
    by_min.append(round(float(test[cols].isna().mean().mean()), 4))
for b in bands25:
    cols = [c for c in tol_cols if c.endswith(f"TOL_{b}")]
    by_band.append(round(float(test[cols].isna().mean().mean()), 4))
report["test"]["missing_by_minute"] = {f"m{i:02d}": v for i, v in enumerate(by_min, 1)}
report["test"]["missing_by_band"] = dict(zip(bands25, by_band))

with open(f"{OUT}/profile.json", "w") as fh:
    json.dump(report, fh, indent=1, default=str)

# ---------- markdown summary ----------
lines = ["# SA Acoustics Profile (mirror, checksums OK)", ""]
lines.append("| site | rows | rec | t_min | t_max | dur>=55 | 25b finite | TOL p50 | p01–p99 |")
lines.append("|---|---|---|---|---|---|---|---|---|")
for r in site_rows:
    lines.append(f"| {r['site']} | {r['rows']:,} | {r['recorders']} | {str(r['t_min'])[:10]} | {str(r['t_max'])[:10]} | "
                 f"{r.get('qc',{}).get('qc_duration_ge55','-')} | {r.get('qc',{}).get('qc_25band_finite','-')} | "
                 f"{r.get('tol_levels',{}).get('p50','-')} | {r.get('tol_levels',{}).get('p01','-')}–{r.get('tol_levels',{}).get('p99','-')} |")
lines.append("")
t = report["test"]
lines.append(f"**Test.csv**: {t['rows']} rows × {t['n_feature_cols']} feats; missing {t['missing_frac']*100:.1f}% "
             f"(rows w/ any missing: {t['rows_with_any_missing']*100:.1f}%); range [{t['min_val']}, {t['max_val']}] dB")
lines.append(f"missing-by-minute: {report['test']['missing_by_minute']}")
with open(f"{OUT}/profile_summary.md", "w") as fh:
    fh.write("\n".join(lines))
print("\n".join(lines))
print("\nFull JSON ->", f"{OUT}/profile.json")
