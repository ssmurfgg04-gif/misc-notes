#!/usr/bin/env python3
"""Merge shard outputs from output/ into output/aggregated.json (stub)."""
import argparse, glob, json, os

ap = argparse.ArgumentParser()
ap.add_argument("--dir", default="output/")
a = ap.parse_args()

merged = {"shards": []}
for p in sorted(glob.glob(os.path.join(a.dir, "shard_*_result.json"))):
    with open(p) as f:
        merged["shards"].append({"file": os.path.basename(p), "result": json.load(f)})

os.makedirs(a.dir, exist_ok=True)
with open(os.path.join(a.dir, "aggregated.json"), "w") as f:
    json.dump(merged, f, indent=1)
print(f"aggregated {len(merged['shards'])} shards")
