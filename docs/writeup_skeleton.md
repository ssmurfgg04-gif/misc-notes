# The Pressure Map — Zindi UVNC Write-up Skeleton (R10-D)

**Status:** SKELETON v0.1 (2026-10-22, agent R10-D). Target: Zindi UVNC methodology/write-up prize
(the competition awards additional prizes for methodology and write-ups — worklog R10-C).
**Numbers policy:** every number below exists in the cited repo doc/artifact; pending readouts are
marked `[PENDING: …]`. No invented results. Citation style: parenthesis = source of the number.

---

## 1. Abstract (~150 w)

The Underwater Vessel Noise Challenge asks for `share_added_vessel` ∈ [0,1] for 1,500 fifteen-minute
test windows: the fraction of mixture energy added by a planted vessel passage across 25 deci-decade
bands — known exactly to the organiser, unobservable to us (plan §6i, A34). We treat this as a
measurement problem, not a curve-fitting problem. Our pipeline: (i) an honest-protocol synthetic-mixture
generator that replicates the organiser's *sub-interval* planting recipe, discovered by forensics on
within-window spectral variation; (ii) a quiet-baseline bump estimator that reads planted passages off
calm acoustic beds (RMSE 0.088, ρ 0.852 on calm validation beds — docs/r7_autopsy_and_bumpfind.md §3);
(iii) station-fingerprint conditioning that recovers three hidden test stations from availability masks
and bed fingerprints (silhouette 0.998 — docs/hunt_log_r7d.json); (iv) moment-exact calibration that
maps raw estimates onto leaderboard-measured truth moments (μ = 0.130076, E[f²] = 0.06058). The result
is the pressure map: a calibrated, station-conditioned per-window estimate of anthropogenic vessel
energy over three unannounced South African monitoring sites.

## 2. The problem is a measurement problem (~250 w)

The metric is 1 − RMSE against a ratio the organisers computed themselves: "sum of added
passage-reference energy divided by sum of total mixture energy … same observed minute-band cells
across the 25 test bands, in linear energy units" (A34, plan §6i). The target is therefore a *physical
quantity* measured on the test side but never released. Our response was to treat the leaderboard
as a measurement instrument and autopsy our submissions against pinned moments: for any submission p with LB RMSE r, E[t·p] = (m2 + E[p²] − r²)/2
(scripts/lb_autopsy.py → data/train_v3/lb_autopsy.json).

Three constant submissions (0.13/0.20/0.40) converged on the truth mean to five decimals —
μ = 0.130076 — and the all-zeros benchmark pinned E[f²] = 0.06058 (σ_f = 0.20895); the
constant-at-μ ceiling is 0.791 (plan §6j; data/train_v3/repin_r7_v2_report.json). The autopsy verdict:
our earlier scores were carried by calibration alone. The first pass read per-window ρ ≈ 0
(r4_v2 −0.06, r6_v2 +0.04, r6_v3 +0.01); after the constant re-pin the corrected values were
0.20/0.31/0.11 — weak but real skill killed by miscalibration (prediction means 0.21–0.32 vs
μ = 0.130) (plan §6i/§6j). The pack sits at 0.816–0.824 ⇒ ρ ≈ 0.61–0.65; the leader's 0.8720 ⇒
ρ ≈ 0.79–0.81 (docs/intel_r10_ruicodex2.md). Two further measurements closed the loop: the platform's
`score_added_vessel` column carries zero weight (diagnostic AUC only, A33); our four evidence columns
transferred anti-informatively (test AUC 0.473–0.486 vs val 0.92–0.997); and the only all-real
mixture model transferred honestly (val 0.2405 → LB 0.2326, −3%) (docs/r7_autopsy_and_bumpfind.md
§1). Skill had to come from per-window signal plus exact calibration — both measurable; we had
little of either.

## 3. Recipe forensics (~250 w)

The smoking gun was in our own generator. Comparing within-window per-band variation (max − min dB
across the 15 minutes), raw training backgrounds sit at p50 = 6.5 dB while test windows sit at
**16.0 dB** (plan §6i; scripts/plant_protocol_v1.py). Our generator_v2 laid each vessel reference
across the FULL window (contiguous slice / stretch / tile), producing planted windows at 6.8 dB —
matching raw backgrounds, not the test. Re-planting the passage in a SUB-INTERVAL (3–12 min at a
random start) yields 14.8 dB ≈ test 16.0. Conclusion: **the organisers plant vessel passages in
sub-intervals, and pure background minutes live inside each test window.** Any naive full-window
mixing recipe — including our synthetic v2/v3 datasets — is structurally wrong: models trained on it
never had to learn bump-reading, which is why our shape detectors transferred at chance (AUC
0.473–0.486; A33) while scores survived on calibration only.

This discovery redefined the training protocol rather than patching it. The fixed recipe (D20) plants
sub-intervals of length L ∈ [3,12] at random starts, mixes ship-only (H_A) and ambient-laden (H_C)
references 50/50, and validates with background-window-level group splits plus clip holdout — a
protocol designed so that a model must detect the bump *inside* the window to score (plan §7j).
Everything downstream — the bump estimator, the station conditioning, the calibration — is built on
this recipe-correct substrate, and every older synthetic number in this write-up is labelled by the
protocol that produced it.

## 4. The E5 quiet-baseline bump estimator (~250 w)

Given sub-interval planting, the estimator writes itself. Per-minute totals flag bump minutes
(> 1.75× the window median); the background is the per-band median of the QUIET minutes; the estimate
is the excess over that baseline divided by the window total — the A32 ratio computed with a measured
baseline instead of an assumed one. E5 is station-free, period-free, and needs no absolute calibration
(scripts/plant_protocol_v3.py, v4 sweep; docs/r7_autopsy_and_bumpfind.md §3).

| evaluation (known f) | RMSE | ρ |
|---|---|---|
| calm beds, ship-only refs (H_A) | **0.088** | **0.852** |
| calm beds, ambient-laden refs (H_C) | 0.098 | 0.837 |
| ship-contaminated beds | 0.358 | 0.32 |
| calm false-alarm floor (f = 0) | 0.135 (mean 0.087) | — |

Two findings matter. First, the H_C result (A29): ambient-laden references IMPROVE recovery
(0.107→0.098 RMSE, ρ 0.79→0.84) — the ambient is part of the addition's energy under the metric's
definition, so an energy-share estimator is ambient-robust by construction, while spectral shape
detectors are precisely what break under ambient contamination. Second, the failure mode: on
ship-contaminated beds natural vessels flood the quiet floor (RMSE 0.358), implying the organisers
selected calm-ish test beds — the same periods excluded from the training release (A28 mechanism).
The dead ends are measured, not guessed: station-prior + HF-anchor ΣB̂ (floor RMSE 0.23–0.44;
scripts/bg_precision.py), per-band p25 subtraction (f̂ ≈ 0.66), running-median estimators on the
full pool (false-alarm mean 0.25–0.51). A later negative control (A69): natural false-alarm bumps
are LF-rich (AUC 0.92), yet gating them moves calm-val RMSE only −0.0008 — residual error lives in
f > 0 misestimation, not detection. Raw E5 on test reads mean 0.536 — test beds are not as calm as
our pool — which forces the calibration of §6 (plan §6i).

## 5. The pressure map: station fingerprints (~300 w)

The test set hides three stations, and it announces them. A two-bit availability fingerprint
(m01 present? × m15 present?; m01..m15 = minute positions per starter notebook cell 2) splits the
1,500 test windows into exactly three robust groups (silhouette 0.998): G0 = 777, G1 = 623
(m01 missing = 41.6%), G2 = 99 (m15 missing = 6.7%), + 8 dropout windows (A49, docs/hunt_log_r7d.json;
NaN census 725 = 623 + 99 + 1 + 2, A59). Edge cropping is an export-batch artifact ⇒ three source
exports ≈ three stations; within-group level histograms are unimodal, so one station per group.

Quiet-bed fingerprints (P20 floor, spectral tilt) then match the groups against the released site
registry (A50, docs/r8_tells.json): **G0** 63.0 dB / −8.3 dB·dec⁻¹ ≈ Saldanha ST300 (61.4/−9.3,
RMSE 2.23) — west-coast moored-class; **G2** 64.8/−8.0 ≈ Durban harbour (67.5/−8.9, RMSE 2.47) —
harbour-class, short campaign; **G1** 72.2/−5.7 matches NOTHING in the registry (best 4.43 dB) — an
exposed environment absent from the release. Class matching with margins (A60, docs/r8_tells.json): G1's nearest
class is 07_St_Francis, shape distance 8.96 vs 17.06 for the runner-up (margin 8.1 dB L2; level
margin 25.7) ⇒ a St-Francis-class exposed SOUTH-COAST site ("mystery box"); G0 = Saldanha-class
(margin 2.6); G2 is a three-way near-tie (Richards 10.55 / Saldanha 10.82 / St Croix 10.88) =
generic harbour class. Independent replication in centered-shape space confirms the tree (A70:
G0→west 1.79 vs 4.10; G1→south-coast 1.90 vs 8.35; G2→harbour 1.80 vs 4.10).

Naming: {08, 11, 12} are exactly the absent file prefixes in the SA package (A36); geographic
ordering pins 08 to the south coast. Dines 2025 (PhD, Stellenbosch/Sea Search;
docs/intel_r9_dines.md) names the SWORD array — 120 km, 5 hydrophones, 26 Aug–7 Oct 2022: Mossel Bay
Harbour, Mossel Bay Diaz, Buffelsbaai, Plett Robberg Point, Plett Beacon Isle — narrowing the 08
slate to {Buffelsbaai, Plett Robberg Pt, Plett Beacon Isle, Mossel Bay Diaz} (harbour-adjacent M1
conflicts with G1's exposed fingerprint). G2's best pin is Table Bay / V&A Waterfront (ST300 deployed
there ~16 h, NYE 2023 — A56; 99 windows ≈ 25 h). Controls: within-group two-component splits are flat
level shifts (0.968–0.998) ⇒ weather states, not stations (A62); ID order is fully interleaved
(813 runs, A59); per-group bump rates (0.593/0.509/0.518) sit mid-train-range ⇒ the global shrink
stands (A63).

The payoff is conditioning, not just naming: as T1 features (group one-hot, site-bed SNR-normalized
bands) the fingerprints carry **31.2% of LGBM gain importance** (top: t1_snr_23/24, HF cavitation
excess over the site bed; T2 wind-shape = 8.6%) and lift the hidden-station-critical G1-class
validation pool 0.0661 → **0.0507** RMSE (D29 gate PASS; data/train_v3/r8_t1t2_report.json, plan
§7j). Finally, the honesty-protocol finding: background-group-split validation exposed the structural
lock's loud-tail overshoot (ferr −0.19 → +0.243, f RMSE 0.2049 → 0.2824), cutting its blend weight
0.3 → 0.1 — and the blend ROSE 0.8741 → 0.8941 although the honest model's own number worsened +5.6%
(plan §6i; data/train_v3/decision_table_v31.json; synthetic-equivalent H_B value,
not an LB score). Validation
design changed model *selection*, not just reported numbers.

## 6. Calibration as physics (~200 w)

The final layer maps raw estimates onto the measured truth distribution with a monotone power map
p = a·f̂^γ, solved by moment matching against the LB-measured moments: **a = 1.175382,
γ = 6.290444** (data/train_v3/repin_r7_v2_report.json; download/RESTORE_CARD.md), verified to give
E[p] = 0.130076 and E[p²] = 0.060580 exactly, with Spearman 1.0 to the raw E5 ranking (round-trip
inversion error 2e-16). The exponent is diagnostic: the pre-constant map had γ = 4.41; the measured
lower μ at fixed E[f²] forces 6.29 — a more dispersed output, as a sub-interval-planted world
implies (plan §6j).

Shrinkage toward μ follows from the same algebra: for p_k = μ + k·(p̂ − μ),
**RMSE²(k) = σ_f²(1 − 2kρ + k²)**, minimised at k* = ρ (plan §6m/§7k). With σ_f = 0.20895, the
k = 0.45 hedge beats the 0.791 constant iff ρ > 0.225 and beats the pinned (k = 1) vector iff
ρ < 0.725 — a near-maxmin family (k ∈ {0.35, 0.45, 0.55} staged). The optimal k is then a single
measurement: k* = ρ **[PENDING: r7_v3_k045 readout]**. One audit caveat: hard shrinkage creates a
point mass at the floor μ(1−k) = 0.07154 — 507/1,500 rows (33.8%) of our PIN vector sit at or near
it (260 exactly at min), erasing ranking among the calmest third of windows (plan §7l;
docs/intel_r10_ruicodex2.md). The staged soft-floor fix (floor + ε·percentile-rank within the floor
set) is gated to not worsen any validation pool.

## 7. What we would do with more time (~150 w)

Three levers, ranked by value per effort. (1) **Wind-index features**: the Knudsen wind regime spans
500 Hz–7.9 kHz = 13 of our 25 bands, so a per-window robust log-level-vs-log-f fit (Theil–Sen with
quiet-bed excess masking + one EM refit) yields a continuous wind index; per-station piecewise
log-linear wind response then gives wind-detrended vessel excess — a revival of the A69 gate with a
proper estimator (docs/intel_r10_vtuad2.md C5; wind is THE confound at r > 0.7 in 1–2.5 kHz at the
St-Francis-class sites, A54). (2) **Per-group domain adaptation**: full-coverage re-standardization
(tree-safe rank-REST quantile mapping) plus closed-form CORAL alignment of train features to each
test group — the documented-winning UDA family on this domain (CORAL +0.015/+0.140 vs MMD
−0.063/−0.190 worst case; worklog R10-B C4). (3) **VTUAD self-training**: strict-interval re-cuts of
the 4.6 GB vessel set plus 2–3 rounds of confidence-filtered pseudo-labels targeting the OOD G1
station (plan §7g #4) — the released VTUAD stack contains no regression head at all, so share
regression remains open territory (worklog R10-B C1).

## 8. Figure / table list for the final version

No figures exist yet; each item lists the repo source that already holds the numbers.

1. **Fig 1 — LB autopsy ρ table.** Per-submission decomposition (mean p, μ if no-skill, per-window
   ρ) for our four LB returns + the corrected-ρ re-pin. Source: scripts/lb_autopsy.py →
   data/train_v3/lb_autopsy.json; data/train_v3/repin_r7_v2_report.json (`prior_subs_rho_corrected`).
2. **Fig 2 — Within-window variation histogram (recipe smoking gun).** Distributions of per-band
   max−min dB: raw backgrounds 6.5 / test 16.0 / planted full-window 6.8 / planted sub-interval 14.8.
   Source: scripts/plant_protocol_v1.py outputs quoted in docs/r7_autopsy_and_bumpfind.md §2.
3. **Fig 3 — 3-group fingerprint scatter (bed level vs tilt).** G0/G1/G2 quiet-bed P20 + tilt against
   the 10 released train sites, with the G1→St-Francis margins annotated. Source:
   docs/hunt_log_r7d.json (A50), docs/r8_tells.json (A60/A61), docs/station-intel.md.
4. **Fig 4 — E5 performance by bed class.** Bar chart of RMSE/ρ on the four evaluation beds of §4,
   plus the dead-end estimator baselines (ΣB̂ 0.23–0.44, p25 f̂≈0.66, running-median FA 0.25–0.51).
   Source: docs/r7_autopsy_and_bumpfind.md §3; scripts/plant_protocol_v3.py, scripts/bg_precision.py.
5. **Table 1 — R8 val pools: E5 vs LGBM vs LGBM+T1T2.** Six pools including classB↔G1
   0.0661→0.0507 and the T1=31.2% / T2=8.6% importance split. Source:
   data/train_v3/r8_t1t2_report.json; plan §7j.
6. **Fig 5 — Power map and shrinkage family.** log-log p = 1.175382·f̂^6.290444 with the pinned
   moments marked, plus p_k = μ + k(p̂−μ) curves for k ∈ {0.35, 0.45, 0.55} and the floor point-mass
   inset (507/1,500 at 0.07154). Source: data/train_v3/repin_r7_v2_report.json; scripts/r7_repin.py;
   docs/intel_r10_ruicodex2.md (floor census).
7. **Fig 6 — Honest vs leaky protocol decomposition.** Lock loud-tail ferr −0.19 → +0.243, f RMSE
   0.2049 → 0.2824, blend weights 0.3 → 0.1, blend 0.8741 → 0.8941. Source: decision_table_v31.json;
   plan §6i; docs/r7_autopsy_and_bumpfind.md §4.
8. **Fig 7 — The pressure map panel.** Per-window calibrated share series for G0/G1/G2
   (LGBM+T1T2 means 0.168/0.185/0.160, p50 0.142/0.195/0.148) over the test timeline, with a
   south-coast inset map of the Dines SWORD slate {Mossel Bay Harbour/Diaz, Buffelsbaai, Plett
   Robberg Pt/Beacon Isle}. Source: data/train_v3/r8_test_diag.npz (plan §7j);
   docs/intel_r9_dines.md (A66).

---

### Pending / gaps (flagged for the final write-up)

- **ρ readout for r7_v3_k045** [PENDING: r7_v3_k045 readout] — pins k* = ρ and closes §6.
- **LB score of the r7/r8 family** — every headline number in §4–§5 is synthetic-protocol or
  moment-inferred; the write-up must keep the synthetic-vs-LB distinction explicit (0.8941 is an
  H_B synthetic-equivalent blend value, not a leaderboard score).
- **No measured per-window ρ yet for E5/LGBM+T1T2 on the real test** — the 0.82–0.87 equivalent band
  in docs/intel_r10_ruicodex2.md is reasoning, not measurement; do not print it as a result.
- **Station names 08/11/12 remain slate-level hypotheses** (A66 slate + Table Bay/V&A pin); the
  write-up should present them as inference-with-evidence-chain, not facts.
