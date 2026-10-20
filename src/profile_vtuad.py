#!/usr/bin/env python3
"""Profile vessel classes from VTUAD metadata + registry -> vessel taxonomy for the plan."""
import pandas as pd, numpy as np, json

meta = pd.read_csv("/home/z/my-project/data/vtuad_metadata.csv")
reg = pd.read_csv("/home/z/my-project/data/vtuad_registry.csv")

out = {}
# class-level profile
g = meta.groupby("label").agg(
    clips=("clip_uid", "count"),
    total_hours=("duration_sec", lambda s: round(s.sum()/3600, 1)),
    mean_len_m=("length", "mean"),
    min_len_m=("length", "min"),
    max_len_m=("length", "max"),
    mean_beam_m=("beam", "mean"),
    mean_speed=("s1", "mean") if "s1" in meta.columns else ("clip_uid", "count"),
).sort_values("total_hours", ascending=False)
print("=== VTUAD class profile ===")
print(g.to_string())
out["vtuad_classes"] = g.reset_index().to_dict(orient="records")

# hull uniqueness
print(f"\nunique hulls (registry): {reg['hull_id'].nunique() if 'hull_id' in reg.columns else 'n/a'}")
print("registry cols:", list(reg.columns))

# length distribution buckets
bins = [0, 10, 25, 55, 100, 200, 400]
meta["len_bucket"] = pd.cut(meta["length"], bins)
lb = meta.groupby("len_bucket", observed=True).agg(clips=("clip_uid","count"), classes=("label", lambda s: sorted(s.unique())))
print("\n=== length buckets ===")
print(lb.to_string())
out["length_buckets"] = lb.reset_index().astype(str).to_dict(orient="records")

# date range + per-class dates
out["date_range"] = [str(meta["utc_begin"].min()), str(meta["utc_begin"].max())]

# sample rate
out["sample_rates"] = meta["sample_rate"].value_counts().to_dict()

with open("/home/z/my-project/data/profile/vessels_vtuad.json","w") as f:
    json.dump(out, f, indent=1, default=str)
print("\nsaved -> data/profile/vessels_vtuad.json")
