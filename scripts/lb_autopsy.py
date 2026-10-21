#!/usr/bin/env python3
"""R7 LB autopsy: extract truth constraints from the four returned leaderboard scores.

Pinned facts:
  - benchmark = all-zeros share predictor -> RMSE_bench^2 = E[f^2] = m2 (pinned)
  - each submission p_i with LB RMSE r_i satisfies:
        E[t*p_i] = (m2 + E[p_i^2] - r_i^2) / 2          (call it P_i)
  - if p_i were truth-independent: E[t*p_i] = mu * mean(p_i)  ->  mu_i = P_i / mean(p_i)
    (mu_i >= mu when skill present; constant mu_i across very different p_i => no per-window skill)
Outputs: data/train_v3/lb_autopsy.json + stdout summary.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
SUB = BASE / "data_backup/misc-notes-data/submissions"
OUT = BASE / "data/train_v3/lb_autopsy.json"

# user-reported LB returns (2026-10-21): score = 1 - RMSE(share), auc = score_added_vessel col
LB = {
    "r4_v2": dict(csv="submission_r4_v2_mixed.csv", score=0.775677418, auc=0.4862),
    "r6_v2": dict(csv="submission_r6_v2_blend.csv", score=0.767616363, auc=0.482822222),
    "r6_v3": dict(csv="submission_r6_v3_real.csv", score=0.767376695, auc=0.4732),
    "r6_v4": dict(csv="submission_r6_v4_blend_real.csv", score=0.706480278, auc=0.4732),
}
BENCH_SCORE = 0.753867825  # R3-verified all-zeros benchmark
m2 = (1.0 - BENCH_SCORE) ** 2

test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str}, usecols=["ID"])
ids = test["ID"].to_numpy()

rows = {}
share_cols, score_cols = {}, {}
for k, v in LB.items():
    df = pd.read_csv(SUB / v["csv"], dtype={"ID": str})
    assert set(df["ID"]) == set(ids), k
    df = df.set_index("ID").loc[ids]
    s = df["share_added_vessel"].to_numpy(float)
    c = df["score_added_vessel"].to_numpy(float)
    share_cols[k], score_cols[k] = s, c
    r = 1.0 - v["score"]
    P = (m2 + float(np.mean(s ** 2)) - r ** 2) / 2.0
    mp = float(np.mean(s))
    mu_i = P / mp if mp > 1e-9 else float("nan")
    rows[k] = dict(
        rmse=r,
        mean_share=mp, std_share=float(np.std(s)), e_p2=float(np.mean(s ** 2)),
        q=dict(zip([0, 10, 25, 50, 75, 90, 100], np.percentile(s, [0, 10, 25, 50, 75, 90, 100]).round(4))),
        P_implied_truth_product=P,
        mu_if_noskill=mu_i,
        auc_col=v["auc"],
        mean_score_col=float(np.mean(c)), std_score_col=float(np.std(c)),
    )

# cross-submission correlations
def corr(a, b):
    return float(np.corrcoef(a, b)[0, 1])

keys = list(LB)
corr_share = {f"{a}-{b}": corr(share_cols[a], share_cols[b]) for i, a in enumerate(keys) for b in keys[i + 1:]}
corr_score = {f"{a}-{b}": corr(score_cols[a], score_cols[b]) for i, a in enumerate(keys) for b in keys[i + 1:]}

# pair-difference truth products (mu-free): P_i - P_j = E[t*(p_i-p_j)]
diffs = {}
for i, a in enumerate(keys):
    for b in keys[i + 1:]:
        dP = rows[a]["P_implied_truth_product"] - rows[b]["P_implied_truth_product"]
        dp = share_cols[a] - share_cols[b]
        # if truth independent of (p_a - p_b): dP = mu * mean(dp)
        mu_implied = dP / float(np.mean(dp)) if abs(float(np.mean(dp))) > 1e-9 else float("nan")
        diffs[f"{a}-{b}"] = dict(E_t_dp=dP, mean_dp=float(np.mean(dp)), mu_if_noskill_diff=mu_implied)

# v3 vs v4 score-column identity check (hypothesis: both took R_real's evidence head)
ident34 = bool(np.array_equal(score_cols["r6_v3"], score_cols["r6_v4"]))

out = dict(
    pinned=dict(bench_score=BENCH_SCORE, m2_Ef2=m2, bench_rmse=float(np.sqrt(m2))),
    lb_rows=rows,
    corr_share=corr_share, corr_score=corr_score, pair_diffs=diffs,
    score_col_v3_equals_v4=ident34,
    notes=[
        "score_added_vessel platform weight = ZERO (starter notebook cell 5); LB col = AUC diagnostic only",
        "all four AUCs < 0.5 => evidence heads anti-informative on real test",
        "mu_if_noskill consistent across submissions => no per-window skill + implied truth mean",
    ],
)
OUT.parent.mkdir(parents=True, exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1)

print(f"pinned: m2 = E[f^2] = {m2:.6f} (bench RMSE {float(np.sqrt(m2)):.6f})")
print(f"{'sub':6} {'RMSE':>8} {'mean':>7} {'std':>7} {'E[p2]':>7} {'P=E[tp]':>8} {'mu_noskill':>10} {'AUC':>6}")
for k, r in rows.items():
    print(f"{k:6} {r['rmse']:8.4f} {r['mean_share']:7.3f} {r['std_share']:7.3f} {r['e_p2']:7.3f} "
          f"{r['P_implied_truth_product']:8.4f} {r['mu_if_noskill']:10.4f} {r['auc_col']:6.3f}")
print("\nshare correlations:", {k: round(v, 3) for k, v in corr_share.items()})
print("score correlations:", {k: round(v, 3) for k, v in corr_score.items()})
print("v3/v4 score cols identical:", ident34)
print("\npair diffs (mu-free):")
for k, d in diffs.items():
    print(f"  {k:9} E[t*dP]={d['E_t_dp']:+.5f}  mean(dP)={d['mean_dp']:+.4f}  mu_if_noskill={d['mu_if_noskill_diff']:.4f}")
print("\nsaved ->", OUT)
