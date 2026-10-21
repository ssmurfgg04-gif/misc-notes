#!/usr/bin/env python3
"""r6_sitecheck.py — secondary control: site-held-out Sigma-B-hat (continuity
with R4b numbers) + format validation of r6 submissions."""
import json, sys, os
import numpy as np
import pandas as pd
import lightgbm as lgb

sys.path.insert(0, "/home/z/my-project/src")
from tournament import featurize

D = "/home/z/my-project/data/synth_v3_mixed"
OUT = "/home/z/my-project/data/train_v3"
rng = np.random.default_rng(3)

bgfeat = np.load(f"{D}/bgfeat.npy")
bgsum = pd.read_csv(f"{D}/bg_sums.csv")
bgsplit = pd.read_csv(f"{D}/bg_split.csv")
y_log = np.log10(bgsum["sumB"].to_numpy())
bsite = bgsplit["site"].astype(str).to_numpy()

names = None
# scale-invariant feature indices must match train_v3_v31.py (48 feats)
import tournament
# rebuild names via featurize on a tiny probe (cheap, deterministic)
probe = np.zeros((1, 15, 25), dtype=np.float32)
_, names = tournament.featurize(probe)
scale_inv = [i for i, n in enumerate(names)
             if not n.startswith("log_band_mean") and n != "log_total"]
assert len(scale_inv) == 48

out = {}
# 3-fold site-held-out: hold 2 sites at a time (site-extrapolation control)
us = sorted(set(bsite))
folds = []
for k in range(3):
    hold = set(rng.choice(us, size=2, replace=False).tolist())
    if hold in folds:
        continue
    folds.append(hold)
errs = []
for hold in folds:
    tr = ~np.isin(bsite, list(hold))
    va = ~tr
    m = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                          subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                          random_state=0, verbose=-1, n_jobs=4)
    m.fit(bgfeat[tr][:, scale_inv], y_log[tr])
    e = m.predict(bgfeat[va][:, scale_inv]) - y_log[va]
    errs.append(e)
    out[f"hold_{'+'.join(sorted(hold))}"] = {"p50": float(np.median(np.abs(e))),
                                             "p90": float(np.quantile(np.abs(e), 0.9))}
e = np.concatenate(errs)
out["site_heldout_all_folds"] = {"p50": float(np.median(np.abs(e))),
                                 "p90": float(np.quantile(np.abs(e), 0.9))}

# format validation of r6 submissions
test = pd.read_csv("/home/z/my-project/data/Test.csv")
for f in ["submission_r6_v1_mixed.csv", "submission_r6_v2_blend.csv",
          "submission_r6_v3_real.csv", "submission_r6_v4_blend_real.csv"]:
    s = pd.read_csv(f"{OUT}/{f}")
    ok = (list(s.columns) == ["ID", "share_added_vessel", "score_added_vessel"]
          and len(s) == 1500 and s["ID"].equals(test["ID"])
          and s["share_added_vessel"].between(0, 1).all()
          and np.isfinite(s["share_added_vessel"]).all())
    out[f"format_{f}"] = bool(ok)
    print(f, "OK" if ok else "FAIL", flush=True)

with open(f"{OUT}/sitecheck_v31.json", "w") as fh:
    json.dump(out, fh, indent=1)
print(json.dumps(out, indent=1))
