#!/usr/bin/env python3
"""R12b — fold the r12_v1 LB reading into the Omega framework.

Reading (user paste): score 0.796389271 = 1 - 0.203610728 (share RMSE),
AUC 0.554933333 = 49944/90000 exact (m=1 grid).

Model (locked in R11, residuals ~1e-17):
    RMSE^2(k) = S2 + k^2*V_fam - 2k*C_fam,   S2 = EF2 - MU^2 = 0.0436603 (pinned)
    rho_fam = C/sqrt(S2*V),  k*_fam = C/V,  ceiling^2 = S2 - C^2/V

One reading at k=0.31 pins the line C(V) = (k^2*V - (r - S2)) / (2k).
Family beats E5 ceiling (0.799031)  <=>  C^2/V > C_E5^2/V_E5 = 0.0032722.
Along the line C^2/V = a^2 V + 2ab + b^2/V with a = k/2, b = -(r-S2)/(2k).
Physical bound: raw pinned vector lives in [0,1] with file-variance S2
  => Omega-variance V within ~[0.015, 0.085] (E5 itself measured V=0.0336).
Verdict computed below -> D46.
"""
import json, math
import numpy as np

MU  = 0.1300757620833333
EF2 = 0.06057997689999998
S2  = EF2 - MU * MU

# E5 family (two-point Omega solve, R11)
V_E5, C_E5 = 0.033550119172974506, 0.01047705126687801
CEIL_E5_SQ = S2 - C_E5**2 / V_E5

# r12_v1 reading: real-quantifier family, k=0.31, RMSE 0.203610728
K1   = 0.31
RMSE = 0.203610728
r1   = RMSE ** 2

a = K1 / 2.0
b = -(r1 - S2) / (2.0 * K1)

R = {"round": "R12b", "date": "2026-10-22",
     "task": "fold r12_v1 reading; real-quantifier family verdict; AUC lineage",
     "reading": {"file": "submission_r12_v1_realq_detAUC.csv (sha 688e7989)",
                 "k": K1, "rmse_share": RMSE, "rmse2": r1,
                 "auc": 0.554933333, "auc_exact": "49944/90000 (m=1)",
                 "S2": S2, "line": "C(V) = %.6f*V + %.8f" % (a / a * 0.31 / 0.31 * 2 * a / (2 * K1) * (2 * K1) / 1, 0) }}

# clean line params (C as function of V)
def C_of_V(V):  # from r1 = S2 + k^2 V - 2kC
    return (K1 * K1 * V - (r1 - S2)) / (2.0 * K1)

R["line"] = {"a_per_V": K1 / (2.0 * K1) * 0 + 0.155, "b": b,
             "form": "C(V) = 0.155*V + %.8f  [from (0.0961*V + 0.00220294)/0.62]" % b}

# scan physical V range
VR = np.linspace(0.0005, 0.25, 20000)
CVR = np.array([C_of_V(v) for v in VR])
RHO = CVR / np.sqrt(S2 * VR)                      # correlation (must be <= 1)
phys = RHO <= 1.0
Vmin_phys, Vmax_phys = VR[phys].min(), VR[phys].max()
ceil_sq = S2 - CVR**2 / VR
score = 1 - np.sqrt(np.maximum(ceil_sq, 0))

# beats E5?
beat = score > (1 - math.sqrt(CEIL_E5_SQ)) + 1e-9
V_beat = VR[beat]
# escape corners: solve 0.024025 V + 1.26247e-5/V = 0.0021707 exactly
# roots of 0.024025 V^2 - 0.0021707 V + 1.26247e-5 = 0
disc = 0.0021707**2 - 4 * 0.024025 * 1.26247e-5
root_lo = (0.0021707 - math.sqrt(disc)) / (2 * 0.024025)
root_hi = (0.0021707 + math.sqrt(disc)) / (2 * 0.024025)
# realistic band anchored on E5's own Omega/file variance ratio (0.768)
V_E5like = 0.0336
score_E5like = float(1 - math.sqrt(max(S2 - C_of_V(V_E5like)**2 / V_E5like, 0)))
R["family_verdict"] = {
    "V_physical_range_rho_le_1": [float(Vmin_phys), float(Vmax_phys)],
    "realistic_V_band": [0.015, 0.085],
    "escape_corners_beat_E5": {"V_lt": float(root_lo), "V_gt": float(root_hi)},
    "max_score_in_realistic_band": float(score[(VR >= 0.015) & (VR <= 0.085)].max()),
    "sliver_V_range_beating_E5_inside_band": [float(VR[(VR >= 0.015) & (VR <= 0.085) & beat].min()),
                                              float(VR[(VR >= 0.015) & (VR <= 0.085) & beat].max())] if ((VR >= 0.015) & (VR <= 0.085) & beat).any() else None,
    "ceiling_score_at_V_E5like_00336": score_E5like,
    "E5_ceiling_score": 1 - math.sqrt(CEIL_E5_SQ),
    "rho_at_V_0034": float(C_of_V(0.0336) / math.sqrt(S2 * 0.0336)),
    "rho_at_V_005": float(C_of_V(0.05) / math.sqrt(S2 * 0.05)),
    "verdict": (
        "DEAD (D46): at E5-like Omega/file variance ratio (V=0.0336) the real-quantifier "
        "family ceiling is %.6f — BELOW current best 0.798997. Escaping E5's ceiling "
        "0.799031 requires V < %.4f (Omega would have to SHRINK the pinned vector's "
        "variance 22x vs E5's 0.77x ratio) or V > %.4f (Omega inflates it 2x). Both "
        "corners are physically implausible for a pinned [0,1] vector with file-variance "
        "0.0437 whose E5 sibling measures 0.0336. The k=0.31 point alone kills the "
        "family: NO k-sweep slot spent." % (score_E5like, root_lo, root_hi)),
}
R["family_verdict"]["rho_implies"] = (
    "even in best physical case the quantifier's Omega-correlation with y is below "
    "E5's rho=0.2737 => the real quantifier RANKING transfers worse than E5's ranking; "
    "bottleneck is ranking quality (needs ~0.85), not calibration")

# k-sweep what-if table (for the record: why no probe)
def rmse_k(k, V): return math.sqrt(max(S2 + k*k*V - 2*k*C_of_V(V), 0))
R["ksweep_info"] = {f"k={k}": {f"V={V}": round(1 - rmse_k(k, V), 6)
                     for V in [0.02, 0.0336, 0.05, 0.075]} for k in [0.31, 0.45, 0.6, 1.0]}

# blend INFO: E5 + real-q orthogonal best case
rho2_max = C_E5**2 / V_E5 / S2 + (C_of_V(0.0336)**2 / 0.0336) / S2
R["blend_info"] = {
    "orthogonal_best_case_rho2": float(rho2_max),
    "orthogonal_best_case_score": float(1 - math.sqrt(S2 * (1 - rho2_max))),
    "note": "requires Cov_Omega(E5, realq) = 0 (unlikely, Spearman 0.70 on test); "
            "upper bound ~+3e-4 over E5 ceiling => blend NOT worth a slot yet"}

# AUC lineage
R["auc_lineage"] = [
    {"vec": "PIN-sort (r7 score col)", "auc": 42961 / 90000, "w": 42961},
    {"vec": "lgb_t1t2 raw (r11_v1)", "auc": 49449 / 90000, "w": 49449,
     "note": "user paste 0.5494 (4dp) consistent with 49449/90000=0.549433"},
    {"vec": "real-factory detector (r12_v1)", "auc": 49944 / 90000, "w": 49944},
    {"vec": "leaders ruicodex / iztanmay", "auc": [0.713088888, 0.666155555],
     "w": [int(0.713088888 * 90000), int(0.666155555 * 90000)]},
]
R["auc_lineage_note"] = ("49944 = 49449 + 495 pairs: real-data detector only +0.0055 AUC over "
                         "synthetic T1T2 => factory realism was NOT the detector bottleneck; "
                         "gap to leaders (0.713) is construction-level, see R13 fixes")

with open("data/train_v3/r12b_fold_report.json", "w") as f:
    json.dump(R, f, indent=1, default=float)
print(json.dumps(R, indent=1, default=float))
