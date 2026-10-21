#!/usr/bin/env python3
"""R7c: shrinkage-calibrated variants of the pinned bump-reading vector.

Model: p_k = mu + k * (p_pinned - mu),  mu = 0.13007576 (measured from LB constants).

Theory (per user §calibration): with truth variance sigma_f^2 = E[f^2] - mu^2,
  RMSE^2(k) = sigma_f^2 * (1 - 2*k*rho + k^2)
  -> optimal k* = rho; constant (k=0) beats pinned (k=1) iff rho < 0.5.
k=0.45 beats constant iff rho > 0.225, beats pinned iff rho < 0.725.

Outputs: r7_v3_k035 / r7_v3_k045 (primary hedge) / r7_v3_k055.
No clipping needed: for k<1, p_k in [mu*(1-k), mu + k*(1-mu)] ⊂ (0,1).
"""
import json
import hashlib
import numpy as np
import pandas as pd

MU = 0.1300757620833333      # measured from three LB constants (R7b)
E_F2 = 0.06057997689999998   # measured truth second moment
SRC = "/home/z/my-project/workspace/misc-notes-data/submissions/submission_r7_v2_bumpshare_repinned.csv"
OUTDIR = "/home/z/my-project/workspace/misc-notes-data/submissions"
REPO = "/home/z/my-project/data/train_v3"

KS = [0.35, 0.45, 0.55]

df = pd.read_csv(SRC)
id_col = df.columns[0]
val_col = "share_added_vessel"   # the scored column; 'score_added_vessel' is zero-weight aux (A33)
assert val_col in df.columns, f"{val_col} not in {list(df.columns)}"
assert len(df) == 1500, f"expected 1500 rows, got {len(df)}"
p = df[val_col].to_numpy(dtype=float)
assert np.isfinite(p).all() and p.min() >= 0.0 and p.max() <= 1.2  # pinned vector can exceed 1 (power map tail)

# verify source is the pinned vector
E_p2_src = float(np.mean(p * p))
print(f"source: {val_col}  E[p]={p.mean():.6f}  E[p^2]={E_p2_src:.6f}  "
      f"(target pinned: mu={MU:.6f}, E[p^2]={E_F2:.6f})")

sigma_f2 = E_F2 - MU * MU
print(f"sigma_f^2 = {sigma_f2:.6f}  sigma_f = {np.sqrt(sigma_f2):.4f}")

report = {"round": "R7c", "date": "2026-10-21", "task": "shrinkage hedge r7_v3 family",
          "mu": MU, "E_f2": E_F2, "sigma_f2": sigma_f2, "source_sha_input": SRC,
          "variants": []}

for k in KS:
    q = MU + k * (p - MU)
    assert np.isfinite(q).all() and q.min() > 0.0 and q.max() < 1.0
    E_q = float(q.mean())
    E_q2 = float(np.mean(q * q))
    expected_Eq2 = MU * MU + k * k * (E_F2 - MU * MU)
    out = df.copy()
    out[val_col] = q
    name = f"submission_r7_v3_k{int(k*100):03d}.csv"
    path = f"{OUTDIR}/{name}"
    out.to_csv(path, index=False)
    sha = hashlib.sha256(open(path, "rb").read()).hexdigest()
    # theoretical LB score as a function of true rho
    def score(rho):
        rmse2 = sigma_f2 * (1 - 2 * k * rho + k * k)
        return 1.0 - np.sqrt(max(rmse2, 0.0))
    entry = {
        "file": name, "k": k, "sha256": sha,
        "E_p": E_q, "E_p2": E_q2, "expected_E_p2": expected_Eq2,
        "sigma_p": float(np.sqrt(max(E_q2 - E_q * E_q, 0.0))),
        "min": float(q.min()), "max": float(q.max()),
        "spearman_vs_pinned": float(pd.Series(q).corr(pd.Series(p), method="spearman")),
        "score_if_rho=0.3": round(float(score(0.3)), 4),
        "score_if_rho=0.5": round(float(score(0.5)), 4),
        "score_if_rho=0.7": round(float(score(0.7)), 4),
        "beats_constant_iff_rho>": round(0.5 * (1 - k * k) / k, 3),
    }
    report["variants"].append(entry)
    print(f"k={k}: {name}  E[p]={E_q:.6f}  E[p^2]={E_q2:.6f} (exp {expected_Eq2:.6f})  "
          f"sigma={entry['sigma_p']:.4f}  sha={sha[:12]}…  "
          f"LB@rho0.3={entry['score_if_rho=0.3']} 0.5={entry['score_if_rho=0.5']} 0.7={entry['score_if_rho=0.7']}")

# correlations of the primary hedge with prior submitted vectors (fleet context)
for ref in ["submission_r4_v2_mixed.csv", "submission_r6_v2_blend.csv", "submission_r6_v3_real.csv"]:
    try:
        r = pd.read_csv(f"{OUTDIR}/{ref}")
        rc = "share_added_vessel" if "share_added_vessel" in r.columns else r.columns[-1]
        rv = r[rc].to_numpy(dtype=float)
        if len(rv) == 1500:
            report.setdefault("corr_to_fleet", {})[ref] = {
                "pearson_vs_k045": float(np.corrcoef(MU + 0.45 * (p - MU), rv)[0, 1]),
                "pearson_vs_pinned": float(np.corrcoef(p, rv)[0, 1]),
            }
    except Exception as e:  # file missing in this sandbox
        report.setdefault("corr_to_fleet", {})[ref] = f"unavailable: {e}"

# update SHA256SUMS_submissions.txt (append/replace these files)
sums_path = f"{OUTDIR}/SHA256SUMS_submissions.txt"
lines = []
if open(sums_path).read():
    lines = [l for l in open(sums_path).read().splitlines()
             if not any(v["file"] in l for v in report["variants"])]
for v in report["variants"]:
    lines.append(f"{v['sha256']}  {v['file']}")
open(sums_path, "w").write("\n".join(lines) + "\n")

with open(f"{REPO}/r7_v3_shrink_report.json", "w") as f:
    json.dump(report, f, indent=1)
print("SHA256SUMS updated; report -> data/train_v3/r7_v3_shrink_report.json")
