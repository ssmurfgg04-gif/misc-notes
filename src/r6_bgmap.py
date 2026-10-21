#!/usr/bin/env python3
"""r6_bgmap.py — R6 circularity fix, stage 1.

Rebuild the deterministic background pool used by synth_v3_mixed (seed 43,
per_site_cap=1500) and map every synth window to its source background row
via (site, start_t). Then create the BACKGROUND-WINDOW-LEVEL group split:

    G_train (80%) / G_val (20%), stratified by site, seed 7.

Anti-circularity property enforced downstream (train_v3_v31.py):
  no synth-VAL window shares its background row with any training input of
  ANY component (M2 two-head OR Sigma-B-hat lock).

Outputs -> data/synth_v3_mixed/bg_split.csv  (bg_uid, site, start_t, split)
        -> data/synth_v3_mixed/map_report.json
"""
import json, os, sys
import numpy as np
import pandas as pd

sys.path.insert(0, "/home/z/my-project/src")
from generator_v2 import load_backgrounds

D = "/home/z/my-project/data/synth_v3_mixed"
SA = "/home/z/my-project/data/South_African_Real_Acoustics"

print("rebuilding pool (seed 43, per_site_cap 1500)...", flush=True)
bg, bg_meta = load_backgrounds(SA, per_site_cap=1500, seed=43)
print("pool:", bg.shape, flush=True)

aux = pd.read_csv(f"{D}/aux.csv")
print("synth windows:", len(aux), flush=True)

# --- map (site, bg_start) -> pool row ---
bg_meta["start_t"] = bg_meta["start_t"].astype(str)
key = bg_meta["site"].astype(str) + "|" + bg_meta["start_t"]
lut = {}
dup = 0
for i, k in enumerate(key):
    if k in lut:
        dup += 1
    lut[k] = i
aux_key = aux["site"].astype(str) + "|" + aux["bg_start"].astype(str)
mapped = aux_key.map(lut)
miss = int(mapped.isna().sum())
print(f"mapped {len(aux)-miss}/{len(aux)} | duplicate pool keys: {dup}", flush=True)

# sanity: loud_tail recomputation must match aux flag
sums = bg.astype(np.float64).sum(axis=(1, 2))
sum_db = 10 * np.log10(sums)
thr = np.quantile(sum_db, 0.75)
lt_recomputed = (sum_db[mapped.to_numpy().astype(int)] >= thr)
lt_match = float((lt_recomputed == aux["loud_tail"].to_numpy()).mean())
print(f"loud_tail flag agreement: {lt_match:.4f}", flush=True)

# --- site-stratified window-level split, seed 7 ---
rng = np.random.default_rng(7)
uids = np.arange(len(bg))
split = np.empty(len(bg), dtype=object)
for s in sorted(bg_meta["site"].unique()):
    rows = uids[(bg_meta["site"] == s).to_numpy()]
    rng.shuffle(rows)
    n_val = int(round(0.2 * len(rows)))
    split[rows[:n_val]] = "val"
    split[rows[n_val:]] = "train"
print("split counts:", pd.Series(split).value_counts().to_dict(), flush=True)

out = pd.DataFrame({
    "bg_uid": uids,
    "site": bg_meta["site"].astype(str),
    "start_t": bg_meta["start_t"],
    "split": split,
})
out.to_csv(f"{D}/bg_split.csv", index=False)

# per-site split table + synth-window split coverage
per_site = out.groupby(["site", "split"]).size().unstack(fill_value=0)
print(per_site, flush=True)
aux["bg_uid"] = mapped.astype(int)
aux["bg_split"] = mapped.map(pd.Series(split, index=uids))
print("synth windows by (bg_split, recipe):",
      aux.groupby(["bg_split", "recipe"]).size().to_dict(), flush=True)
aux.to_csv(f"{D}/aux_with_split.csv", index=False)

rep = {
    "pool_rows": int(len(bg)),
    "synth_windows": int(len(aux)),
    "unmapped_synth_windows": miss,
    "duplicate_pool_keys": int(dup),
    "loud_tail_agreement": lt_match,
    "split_seed": 7,
    "val_frac": 0.2,
    "split_counts": pd.Series(split).value_counts().to_dict(),
    "synth_by_split_recipe": {f"{a}|{b}": int(c) for (a, b), c in
                              aux.groupby(["bg_split", "recipe"]).size().items()},
}
with open(f"{D}/map_report.json", "w") as fh:
    json.dump(rep, fh, indent=1)
print(json.dumps(rep, indent=1), flush=True)
