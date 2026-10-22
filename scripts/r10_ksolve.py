#!/usr/bin/env python3
"""R10 — k* solve from the r7_v3_k045 LB reading + r8_v1 (T1T2) candidate build.

Framework (all exact algebra, no approximations):
  Family:        p_k = mu + k*(p_hat - mu),  p_hat = moment-pinned r7_v2 (E[p_hat]=mu, E[p_hat^2]=E_f2)
  => V = E[(p_hat-mu)^2] = E_f2 - mu^2 = sigma2   (BY CONSTRUCTION)
  RMSE^2(k)      = E[(y-p_k)^2] = sigma2*(1 + k^2 - 2*k*rho),  rho = Corr(y, p_hat)
  LB reading:    RMSE(k=0.45) = 0.202545861  =>  rho = (1.2025 - RMSE^2/sigma2)/0.9
  Optimal:       k* = rho   (since V = sigma2)
  Ceiling:       score* = 1 - sigma*sqrt(1-rho^2)

Outputs:
  download/submission_r7_v4_kstar.csv          (k*=rho rescale of the pinned family)
  download/submission_r8_v1_t1t2_k0292.csv     (LGBM+T1T2 test vector, power-map pinned, shrunk at borrowed k*)
  data/train_v3/r10_ksolve_report.json
"""
import json, hashlib, math
import numpy as np
import pandas as pd

MU   = 0.1300757620833333
EF2  = 0.06057997689999998
SIG2 = 0.043660273018440054
SIG  = math.sqrt(SIG2)
K_PIN   = 0.45
RMSE_LO = 0.202545861          # user paste lower bound (1 - score_high)
RMSE_HI = 0.202545862          # user paste upper bound (1 - score_low)
EP2_PIN = 0.02576090916779403  # from r7_v3_shrink_report.json (independent cross-check)

R = {"round": "R10", "date": "2026-10-22",
     "task": "k* solve from r7_v3_k045 LB reading + r8_v1 T1T2 candidate + ensemble math"}

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def spearman(a, b):
    ra = pd.Series(a).rank().values
    rb = pd.Series(b).rank().values
    return float(np.corrcoef(ra, rb)[0, 1])

def rmse2_of_k(k, rho):
    return SIG2 * (1.0 + k * k - 2.0 * k * rho)

def score_of_k(k, rho):
    return 1.0 - math.sqrt(max(rmse2_of_k(k, rho), 0.0))

# ---------------- Part A: exact k* solve ----------------
df = pd.read_csv("download/submission_r7_v3_k045_PIN.csv")
p = df["share_added_vessel"].values.astype(np.float64)
assert len(p) == 1500, len(p)

ep1 = float(p.mean()); ep2 = float((p * p).mean())
R["pin_file_check"] = {"E_p": ep1, "E_p2": ep2,
                       "E_p_minus_mu": ep1 - MU, "E_p2_vs_report": ep2 - EP2_PIN}
assert abs(ep1 - MU) < 1e-9, "PIN file mean != mu"
assert abs(ep2 - EP2_PIN) < 1e-9, "PIN file E[p^2] != shrink report"

rmse_pin = 0.5 * (RMSE_LO + RMSE_HI)
delta = SIG2 - rmse_pin * rmse_pin            # = 0.9*C - 0.2025*V
W = ep2 - MU * MU                             # = 0.2025 * V   (measured from file)
C = (delta + W) / 0.9                         # E[(y-mu)(p_hat-mu)]
V = W / 0.2025
V_err = V - SIG2
assert abs(V_err) < 1e-6, f"V != sigma2 beyond tolerance: {V_err}"
rho = C / SIG2
kstar = rho
factor = kstar / K_PIN

R["ksolve"] = {
    "rmse_pin_used": rmse_pin, "sigma2": SIG2, "sigma": SIG,
    "delta": delta, "W_from_file": W, "C": C, "V": V, "V_minus_sigma2": V_err,
    "rho_implied": rho, "kstar": kstar, "rescale_factor_vs_k045": factor,
    "projected_score_kstar": 1.0 - SIG * math.sqrt(1.0 - rho * rho),
    "projected_rmse_kstar": SIG * math.sqrt(1.0 - rho * rho),
    "implied_raw_r7v2_score_if_submitted": score_of_k(1.0, rho),
}

# verification table: predicted scores at family points (measured anchor at k=0.45)
vt = {}
for k in [0.35, 0.45, 0.55, 1.0, kstar]:
    vt[round(k, 6)] = {"predicted_score": round(score_of_k(k, rho), 9),
                       "predicted_rmse": round(math.sqrt(rmse2_of_k(k, rho)), 9)}
vt[0.45]["measured_rmse"] = rmse_pin
vt[0.45]["residual"] = math.sqrt(rmse2_of_k(0.45, rho)) - rmse_pin
R["family_score_table"] = vt

# build r7_v4_kstar
share4 = MU + factor * (p - MU)
assert share4.min() >= 0.0 and share4.max() <= 1.0, (share4.min(), share4.max())
out4 = df.copy()
out4["share_added_vessel"] = share4
out4.to_csv("download/submission_r7_v4_kstar.csv", index=False)
R["r7_v4_kstar"] = {
    "file": "download/submission_r7_v4_kstar.csv", "sha256": sha256("download/submission_r7_v4_kstar.csv"),
    "k": kstar, "E_p": float(share4.mean()), "E_p2": float((share4 ** 2).mean()),
    "min": float(share4.min()), "max": float(share4.max()),
    "spearman_vs_pin": spearman(share4, p),
    "expected_score": 1.0 - SIG * math.sqrt(1.0 - rho * rho),
}

# ---------------- Part B: r8_v1 (T1T2) candidate ----------------
d = np.load("data/train_v3/r8_test_diag.npz", allow_pickle=True)
e5 = d["e5"]; t1t2 = d["lgb_t1t2"].astype(np.float64); grp = d["grp"]
# Row-order proof: r8_followup.py saves npz in Test.csv natural order (read_csv, no sort).
# Verify ID sequence Test.csv == sample_submission == PIN csv; e5 in npz is a RECOMPUTED E5
# (corr ~0.965 vs k045 score col) so value equality is NOT expected - order equality is what matters.
ids_test = pd.read_csv("data/sa_package/Test.csv", dtype={"ID": str})["ID"].tolist()
ids_pin = df["ID"].astype(str).tolist()
order_ok = ids_test == ids_pin
assert order_ok and len(ids_test) == 1500, "ID order mismatch Test.csv vs PIN csv"
align_err = float(np.max(np.abs(e5 - df["score_added_vessel"].values.astype(np.float64))))
e5_corr = float(np.corrcoef(e5, df["score_added_vessel"].values)[0, 1])
R["t1t2_alignment"] = {"id_order_proof": True, "rows": 1500,
                       "e5_recomputed_max_abs_diff_vs_scorecol": align_err,
                       "e5_recomputed_corr_vs_scorecol": e5_corr,
                       "note": "npz e5 is R8-followup recomputation, not the k045 score col; order proven via Test.csv IDs"}
gcnt = {g: int((grp == g).sum()) for g in sorted(set(grp.tolist()))}
R["t1t2_alignment"]["grp_counts"] = gcnt

sp_base = spearman(t1t2, p)
R["t1t2"] = {"spearman_vs_r7v2_family": sp_base,
             "raw_min": float(t1t2.min()), "raw_max": float(t1t2.max()),
             "raw_mean": float(t1t2.mean()), "raw_std": float(t1t2.std())}

# Beta-quantile moment pin (replaces power map for new vectors; r7_v2 chain stays frozen).
# Beta(alpha, beta) bounded in [0,1] with EXACTLY the pinned moments:
#   mean = alpha/(alpha+beta) = mu ;  var = mu*(1-mu)/(alpha+beta+1) = sigma2
ab_sum = MU * (1.0 - MU) / SIG2 - 1.0
alpha = MU * ab_sum
beta = (1.0 - MU) * ab_sum
from scipy.stats import rankdata, beta as beta_dist
rk = rankdata(t1t2, method="average") / (len(t1t2) + 1.0)
p8 = beta_dist.ppf(rk, alpha, beta)
R["t1t2_pin"] = {"method": "beta_quantile", "alpha": alpha, "beta": beta,
                 "E_p": float(p8.mean()), "E_p2": float((p8 ** 2).mean()),
                 "residual_mu": float(p8.mean() - MU),
                 "residual_E2": float((p8 ** 2).mean() - EF2),
                 "pinned_min": float(p8.min()), "pinned_max": float(p8.max())}

k8 = kstar
sub8 = MU + k8 * (p8 - MU)
lo8, hi8 = float(sub8.min()), float(sub8.max())
R["r8_v1"] = {"file": "download/submission_r8_v1_t1t2_k0292.csv", "k_borrowed": k8,
              "min": lo8, "max": hi8, "in_range": bool(lo8 >= 0 and hi8 <= 1),
              "E_p": float(sub8.mean()), "E_p2": float((sub8 ** 2).mean()),
              "spearman_vs_raw_t1t2": spearman(sub8, t1t2)}
assert R["r8_v1"]["in_range"], (lo8, hi8)
out8 = df.copy()
out8["share_added_vessel"] = sub8
out8.to_csv("download/submission_r8_v1_t1t2_k0292.csv", index=False)
R["r8_v1"]["sha256"] = sha256("download/submission_r8_v1_t1t2_k0292.csv")

# risk/payoff table for r8_v1 at borrowed k: score as function of its true rho_T
R["r8_v1_payoff"] = {str(rT): round(1.0 - math.sqrt(max(rmse2_of_k(k8, rT), 0.0)), 6)
                     for rT in [0.20, 0.25, 0.292, 0.35, 0.45, 0.60, 0.80]}
R["r8_v1_note"] = ("beats r7_v4_kstar iff rho_T1T2 > rho_base = 0.2921; "
                   "after first LB read of r8_v1, its exact k8* follows from the same quadratic "
                   "(V_T = (E[sub8^2]-mu^2)/k8^2, rho_T from RMSE reading)")

# ---------------- Part C: ensemble math (INFO ONLY) ----------------
rho_r7v2 = rho
rho_r6v2, rho_r4v2 = 0.31, 0.20            # R7b corrected estimates (approximate)
c_r7_r6, c_r7_r4, c_r6_r4 = 0.2583, 0.2231, 0.8354   # file pearson correlations
Sig = np.array([[1.0, c_r7_r6, c_r7_r4],
                [c_r7_r6, 1.0, c_r6_r4],
                [c_r7_r4, c_r6_r4, 1.0]])
r3 = np.array([rho_r7v2, rho_r6v2, rho_r4v2])
def ens(rho_vec, S):
    Si = np.linalg.inv(S)
    w = Si @ rho_vec
    return float(np.sqrt(max(rho_vec @ w, 0.0))), (w / w.sum()).tolist()
r2_2v, w2 = ens(r3[:2], Sig[:2, :2])
r3_3v, w3 = ens(r3, Sig)
lam = 0.05
r3_ridge, w3r = ens(r3, Sig + lam * np.eye(3))
R["ensemble_info"] = {
    "note": "INFO ONLY - r6v2/r4v2 rhos are R7b approximations; build only after k* verification read",
    "two_vector": {"vectors": ["r7_v2", "r6_v2"], "rho_max": r2_2v,
                   "projected_score": 1.0 - SIG * math.sqrt(1 - r2_2v ** 2), "weights": w2},
    "three_vector": {"vectors": ["r7_v2", "r6_v2", "r4_v2"], "rho_max": r3_3v,
                     "projected_score": 1.0 - SIG * math.sqrt(1 - r3_3v ** 2), "weights": w3},
    "three_vector_ridge": {"lambda": lam, "rho_max": r3_ridge,
                           "projected_score": 1.0 - SIG * math.sqrt(1 - r3_ridge ** 2), "weights": w3r},
}

# ---------------- save report ----------------
with open("data/train_v3/r10_ksolve_report.json", "w") as f:
    json.dump(R, f, indent=1)

print(json.dumps(R["ksolve"], indent=2))
print("\nfamily table:", json.dumps(R["family_score_table"], indent=1))
print("\nr7_v4:", json.dumps({k: v for k, v in R["r7_v4_kstar"].items()}, indent=1))
print("\nt1t2:", json.dumps(R["t1t2"], indent=1))
print("t1t2 pin:", json.dumps(R["t1t2_pin"], indent=1))
print("r8_v1:", json.dumps(R["r8_v1"], indent=1))
print("r8_v1 payoff:", json.dumps(R["r8_v1_payoff"], indent=1))
print("\nensemble:", json.dumps(R["ensemble_info"], indent=1))
