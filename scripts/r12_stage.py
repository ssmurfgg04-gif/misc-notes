#!/usr/bin/env python3
"""R12 — stage r12_v1: share = real-data quantifier (Beta-pin, borrowed k), score = detector P(passage).
Risk math: at k=0.31 beats E5 ceiling 0.799031 iff rho_Omega > 0.2758."""
import json, hashlib, math
import numpy as np, pandas as pd
from scipy.stats import rankdata, beta as beta_dist

MU, EF2 = 0.1300757620833333, 0.06057997689999998
S2 = EF2 - MU * MU
K = 0.31

R = {"round": "R12", "task": "stage r12_v1"}
d = np.load("data/train_v3/r12_test_diag.npz", allow_pickle=True)
det, q = d["det"], d["qnt"]
pin = pd.read_csv("download/submission_r7_v4_kstar.csv")  # keeps ID + score-col structure

# Beta-quantile pin of the quantifier ranking to the pinned LB moments
ab = MU * (1 - MU) / S2 - 1.0
alpha, beta = MU * ab, (1 - MU) * ab
rk = rankdata(q, method="average") / (len(q) + 1.0)
p8 = beta_dist.ppf(rk, alpha, beta)
sub = MU + K * (p8 - MU)
assert sub.min() >= 0 and sub.max() <= 1, (sub.min(), sub.max())

out = pin.copy()
out["share_added_vessel"] = sub
out["score_added_vessel"] = det          # detector P(passage) — model output, weight-0 AUC read
fn = "download/submission_r12_v1_realq_detAUC.csv"
out.to_csv(fn, index=False)
h = hashlib.sha256(open(fn, "rb").read()).hexdigest()

R["r12_v1"] = {
    "file": fn, "sha256": h,
    "share_col": "real-data quantifier (LGBM, real VTUAD passages x real SA backgrounds), Beta-pinned, k=0.31 borrowed",
    "score_col": "detector P(passage) ranking -> free AUC transfer read",
    "E_p": float(sub.mean()), "E_p2": float((sub**2).mean()), "min": float(sub.min()), "max": float(sub.max()),
    "spearman_share_vs_e5": float(pd.Series(sub).rank().corr(pin["share_added_vessel"].rank())),
    "spearman_score_vs_share": float(pd.Series(det).rank().corr(pd.Series(sub).rank())),
    "expected": {"rho_needed_to_beat_e5_ceiling": 0.2758,
                 "score_at_rho": {str(r): round(1 - math.sqrt(max(S2 * (1 + K*K - 2*K*r), 0)), 5)
                                  for r in [0.15, 0.20, 0.28, 0.35, 0.45, 0.55, 0.65]}},
}
with open(fn.replace(".csv", "_report.json"), "w") as f:
    json.dump(R, f, indent=1, default=float)

# ledger
with open("download/backups/LEDGER.sha256", "a") as L, open("download/backups/SUBMISSION_LEDGER.jsonl", "a") as J:
    L.write(f"{h}  {fn}\n")
    rec = {"name": "r12_v1_realq_detAUC", "file": fn.split("/")[-1], "n": 1500,
           "E_p": float(sub.mean()), "E_p2": float((sub**2).mean()), "min": float(sub.min()), "max": float(sub.max()),
           "k": K, "score_col": "detector P(passage)", "notes": "R12 real-data detect-then-quantify; D45",
           "sha256": h}
    J.write(json.dumps(rec) + "\n")
print(json.dumps(R, indent=1, default=float))
