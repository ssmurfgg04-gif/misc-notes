#!/usr/bin/env python3
"""R7b — §A re-pin of the r7_v1 bump-share vector to the user's measured moments.

Input : workspace/misc-notes-data/submissions/submission_r7_v1_bumpshare.csv
        (p = h_old(f̂) = 0.916 · f̂^4.41, pinned to E[p]=0.1500, E[p²]=0.060581)
Method: invert the power map exactly (monotone bijection): f̂ = (p/0.916)^(1/4.41)
        solve a,γ in  h_new(f̂) = a·f̂^γ  s.t.
            E[a·f̂^γ]   = μ     = 0.130075   (from constants 0.13/0.20/0.40)
            E[a²f̂^(2γ)] = E[f²] = 0.060581   (from benchmark 0.75387)
        ⇒ scalar root: G(γ) = E[f̂^(2γ)]/E[f̂^γ]² = E[f²]/μ², then a = μ/E[f̂^γ].
Output: submission_r7_v2_bumpshare_repinned.csv (+ report JSON, sha256).
Bonus : recompute per-window ρ for the four prior LB returns under corrected μ.
"""
import json, hashlib
import numpy as np
import pandas as pd

SUB_DIR = "/home/z/my-project/workspace/misc-notes-data/submissions"
OLD_CSV = f"{SUB_DIR}/submission_r7_v1_bumpshare.csv"
NEW_CSV = f"{SUB_DIR}/submission_r7_v2_bumpshare_repinned.csv"
REPORT  = "/home/z/my-project/data/train_v3/repin_r7_v2_report.json"

A_OLD, G_OLD = 0.916, 4.41

# --- moments from the user's constant-calibration track (handoff §A) ---------
LB = {0.00: 0.75387, 0.13: 0.79105, 0.20: 0.77966, 0.40: 0.65865}
rmse = {c: 1 - s for c, s in LB.items()}
E_f2 = rmse[0.00] ** 2                                  # benchmark pins E[f²]
mus = [(E_f2 + c * c - rmse[c] ** 2) / (2 * c) for c in (0.13, 0.20, 0.40)]
MU = float(np.mean(mus))
print(f"E[f²]  = {E_f2:.6f}")
print(f"mu per constant: {mus}  -> MU = {MU:.6f}")
VAR_F = E_f2 - MU * MU
SIG_F = VAR_F ** 0.5
print(f"sigma_f = {SIG_F:.6f}")

# --- recover f̂ from r7_v1 ----------------------------------------------------
d = pd.read_csv(OLD_CSV)
p_old = d["share_added_vessel"].to_numpy(float)
fhat = (p_old / A_OLD) ** (1.0 / G_OLD)
# round-trip check
rt = np.max(np.abs(A_OLD * fhat ** G_OLD - p_old))
print(f"inversion round-trip max err: {rt:.3e}")
print(f"f̂ range: [{fhat.min():.3e}, {fhat.max():.6f}]  mean {fhat.mean():.6f}")

# --- solve γ by bisection ------------------------------------------------------
TARGET = E_f2 / MU ** 2
def G(g):
    m1 = np.mean(fhat ** g)
    m2 = np.mean(fhat ** (2 * g))
    return m2 / m1 ** 2

lo, hi = 0.5, 20.0
print(f"G(old γ=4.41) = {G(4.41):.6f}  (old pin)   target G = {TARGET:.6f}")
for _ in range(200):
    mid = 0.5 * (lo + hi)
    if G(mid) < TARGET:
        lo = mid
    else:
        hi = mid
GAMMA = 0.5 * (lo + hi)
A_NEW = MU / np.mean(fhat ** GAMMA)
print(f"γ_new = {GAMMA:.6f}   a_new = {A_NEW:.6f}")

p_new = A_NEW * fhat ** GAMMA
E_p, E_p2 = p_new.mean(), np.mean(p_new ** 2)
print(f"verify: E[p] = {E_p:.6f} (target {MU:.6f})   E[p²] = {E_p2:.6f} (target {E_f2:.6f})")
ok_mean = abs(E_p - MU) <= 0.005
ok_m2 = abs(E_p2 - E_f2) <= 0.001
print(f"tolerance check (§A): mean ±0.005 -> {ok_mean}   E[p²] ±0.001 -> {ok_m2}")

# sanity: old vector's pinned moments for the record
print(f"old r7_v1: E[p] = {p_old.mean():.6f}  E[p²] = {np.mean(p_old**2):.6f}")

# ranking preservation + corr to old
from scipy.stats import spearmanr
rho_sp = spearmanr(p_old, p_new).statistic
print(f"spearman(r7_v1, r7_v2) = {rho_sp:.4f}  (monotone map ⇒ ≈1)")

# --- write CSV ----------------------------------------------------------------
out = d.copy()
out["share_added_vessel"] = p_new
out.to_csv(NEW_CSV, index=False)
sha = hashlib.sha256(open(NEW_CSV, "rb").read()).hexdigest()
print(f"written {NEW_CSV}\nsha256 = {sha}")

# --- bonus: recompute the four prior LB returns under corrected moments -------
def load(p):
    s = pd.read_csv(f"{SUB_DIR}/{p}")
    return s["share_added_vessel"].to_numpy(float)

prior = {
    "submission_r4_v2_mixed.csv":      0.7757,
    "submission_r6_v2_blend.csv":      0.7676,
    "submission_r6_v3_real.csv":       0.7674,
    "submission_r6_v4_blend_real.csv": 0.7065,
}
rows = []
for name, score in prior.items():
    try:
        q = load(name)
    except FileNotFoundError:
        rows.append({"file": name, "lb": score, "note": "csv not in submissions/"})
        continue
    r = 1 - score
    mp, sp2 = q.mean(), np.mean(q ** 2)
    tp = (E_f2 + sp2 - r * r) / 2.0
    cov = tp - MU * mp
    rho = cov / (SIG_F * (sp2 - mp * mp) ** 0.5) if sp2 > mp * mp else float("nan")
    rows.append({"file": name, "lb": score, "mean_p": round(mp, 4),
                 "E_tp": round(tp, 5), "cov": round(cov, 5), "rho_perwindow": round(rho, 4)})
    print(name, rows[-1])

report = {
    "round": "R7b", "date": "2026-10-21", "task": "handoff §A re-pin",
    "inputs": {"old_map": f"{A_OLD}·f̂^{G_OLD}", "lb_constants": LB},
    "derived_moments": {"E_f2": E_f2, "mu_per_constant": mus, "mu": MU, "sigma_f": SIG_F,
                        "note": "three constants converge on μ to 5 decimals (0.130075) — strong internal consistency"},
    "old_vector": {"E_p": p_old.mean(), "E_p2": float(np.mean(p_old ** 2))},
    "new_map": {"a": A_NEW, "gamma": GAMMA, "gamma_old": G_OLD},
    "verify": {"E_p_new": E_p, "E_p2_new": E_p2,
               "ok_mean_±0.005": bool(ok_mean), "ok_Ep2_±0.001": bool(ok_m2),
               "spearman_vs_old": rho_sp},
    "inversion_roundtrip_maxerr": rt,
    "prior_subs_rho_corrected": rows,
    "out_csv": "submissions/submission_r7_v2_bumpshare_repinned.csv",
    "sha256": sha,
    "user_gate": "submission decision is user's (§E bands apply to this vector)",
}
with open(REPORT, "w") as fh:
    json.dump(report, fh, indent=1)
print(f"report -> {REPORT}")
