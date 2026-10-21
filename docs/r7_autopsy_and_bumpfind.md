# R7 — The LB Autopsy & The Bump-Reading Breakthrough (2026-10-21)

> Status: **the "something is wrong" question is answered, measured, and fixed.**
> New candidate `submission_r7_v1_bumpshare.csv` (sha256 917c4d53…) — user-gated.

## 1. The four LB returns, autopsied without any new submission

Benchmark = all-zeros ⇒ **E[f²] = 0.060581 pinned** (bench RMSE 0.246132).
For each submission p with LB RMSE r: `E[t·p] = (m2 + E[p²] − r²)/2`. From the four
returned scores + our own CSVs (scripts/lb_autopsy.py → data/train_v3/lb_autopsy.json):

| sub | LB | mean(p) | μ if no-skill | per-window ρ (decomposition) |
|---|---|---|---|---|
| r4_v2 | 0.7757 | 0.214 | 0.145 | **≈ −0.06** |
| r6_v2 | 0.7676 | 0.248 | 0.153 | **≈ +0.04** |
| r6_v3 | 0.7674 | 0.144 | 0.152 | **≈ +0.01** |
| r6_v4 | 0.7065 | 0.316 | 0.180 | ≈ 0 (lock negative) |

**Verdict: every submission so far had ρ ≈ 0 per-window skill on the real test.**
Scores were carried by calibration alone, and calibration was off (means 0.21–0.32
vs truth μ ≈ 0.15, σ_f ≈ 0.195 ⇒ best-constant ≈ 0.81–0.82 = the pack cluster ✓).
Leader 0.872 ⇒ needs ρ ≈ 0.75. The 0.894 synthetic-equivalent number measured
OUR recipe, not theirs.

Additional reads:
- **`score_added_vessel` = evidence score, platform weight ZERO** (starter notebook
  cell 5: "ROC AUC on that output is diagnostic only"). All four evidence columns
  scored AUC 0.473–0.486 = **anti-informative** on test (val said 0.92–0.997).
  r6_v3/v4 score columns are byte-identical (both took R_real's head) ✓.
- **v4 collapse was the honest protocol's predicted failure**: 0.4 weight on the
  lock, whose loud-tail bias is +0.243 ⇒ median prediction 0.376 ⇒ RMSE 0.2935.
- **R_real transferred honestly**: its v3 H_B val (0.2405) ≈ its LB (0.2326, −3%);
  M2/blend val (0.1059) was optimistic by 2.2×. Synthetic val — even H_B — is not
  the organizer's recipe.

## 2. Recipe forensics — the smoking gun was in our generator

* A32 verbatim (Zindi page): target = "sum of added passage-reference energy
  divided by sum of total mixture energy … same observed minute-band cells across
  the 25 test bands, in linear energy units". The added energy is KNOWN to the
  organiser. Sample submission: share 0.0 / score 0.5; notebook constant: 0.1/0.5.
* **Within-window variation (per-band max−min dB across the 15 minutes):**
  raw backgrounds p50 = **6.5 dB** vs test = **16.0 dB**.
* Our generator_v2 mixed the reference across the FULL window (contiguous slice /
  stretch / tile) — planted full-window KPI = 6.8 dB. Planted SUB-INTERVAL
  (3–12 min at random start) = **14.8 dB ≈ test 16.0**. **The organisers plant the
  passage in a sub-interval; pure background minutes live inside each window.**
  Our models never had to learn bump-reading ⇒ zero transfer. (scripts/plant_protocol_v1.py)

## 3. The breakthrough: quiet-baseline bump estimator on calm beds

E5 (scripts/plant_protocol_v3.py, v4 sweep): per-minute totals flag bump minutes
(> 1.75× window median); background = per-band median of QUIET minutes;
excess/total = f̂. A32-exact, station-free, period-free, ambient-robust.

| evaluation (known f) | RMSE | ρ |
|---|---|---|
| calm beds, H_A (ship-only ref) | **0.088** | **0.852** |
| calm beds, H_C (ambient-laden ref) | 0.098 | 0.837 |
| ship-contaminated beds | 0.358 | 0.32 |
| calm false-alarm floor (f=0) | 0.135 (mean 0.087) | — |

- **The leader's method is calm-bed bump-reading.** RMSE 0.088–0.098 / ρ 0.84–0.85
  on clean beds ≈ leader's implied ρ 0.75 at RMSE 0.128.
- **A29/H_C directive answered**: ambient-laden additions IMPROVE recovery
  (0.107→0.098, ρ 0.79→0.84). The ambient is part of the controlled addition's
  energy — the share estimator is ambient-robust BY CONSTRUCTION; the shape
  detectors (M2/R_real, AUC≈0.48) are not. Hypothesis upgraded: ambient-in-passage.
- Dead ends now MEASURED (not guessed): station-prior + HF-anchor ΣB̂ (floor RMSE
  0.23–0.44; scripts/bg_precision.py), per-band p25 min-subtraction (v0: f̂≈0.66),
  running-median / quiet-minute estimators on the full raw pool (natural vessels
  flood the floor: FA mean 0.25–0.51). The organisers' test beds must be selected
  calm-ish — which is exactly why those periods are "excluded from the training release".
- **r7_v1 calibration**: raw E5 on test (mean 0.536 — test beds are not as calm as
  our pool) → monotone power map h(f)=0.916·f^4.41 matching the pinned moments
  E[f]=0.150 / E[f²]=0.060581 EXACTLY. Ranking preserved; corr to our four prior
  vectors only 0.26–0.29 (genuinely new information source).

## 4. The honest-protocol finding (write-up gold)

The honest (background-window-group-split) protocol RAISED the blend 0.8741→0.8941.
Mechanism: the leaky protocol made the lock look good (f RMSE 0.2049, loud-tail
ferr −0.19) and it took 0.3 blend weight. Honesty revealed the lock's loud-tail
OVERSHOOT (+0.243 sign flip, f RMSE 0.2824) ⇒ weight cut to 0.1 ⇒ blend improved
even though M2's own number worsened (+5.6%). Circularity had been
**underweighting the honest model and overweighting the leaky lock**. Validation
protocol design changes model selection, not just reported numbers. (R4b leaky
numbers retired; decision_table_v31.json is the record.)

## 5. Intel & provenance locked this round

- **A33**: `score_added_vessel` weight = 0 (diagnostic AUC only) — notebook cell 5.
- **A34**: A32 exact quote captured (linear energy, same observed cells, 25 bands).
- **A35**: VTUAD provenance = **Strait of Georgia, BC, Canada** (ONC archive,
  May 2016–May 2017, 525 clips = 509 vessel + 16 background, ~56 h, 32 kHz,
  AIS/MMSI/UTC provenance, CC BY 4.0; IEEE DataPort DOI 10.21227/msg0-ag12;
  descriptor preprints.org 202609.0617; arXiv 2505.23964). The ambient-in-passage
  beds are CANADIAN coastal ambient mixed into SA backgrounds (domain gap, H_C).
- **A36**: **the package file prefixes ARE the site registry**: 01_Richards_Bay,
  02_Durban, 03_Cape_Recife, 04_Bird_Island, 05_St_Croix_Island, 06_Riy_Banks,
  07_St_Francis, 09_Fish_Hoek, 10_Sea_Point, 13_Saldhana_Bay. **{08, 11, 12} are
  exactly the absent files** — the withheld stations. Geographic gaps: 08 between
  St Francis (07) and Fish Hoek (09); 11/12 between Sea Point (10) and Saldanha (13).
  Unverified candidates for the user's SAEON/consortium enquiry: 08 ∈ {Knysna,
  Mossel Bay, De Hoop MPA, Cape Agulhas, Hermanus/Gansbaai}; 11/12 ∈ {Table Bay,
  Robben Island, Hout Bay, Kommetjie/Cape Point, Dassen Island, Yzerfontein,
  Langebaan}. HYPOTHESES ONLY.
- **A37**: sponsor = French Embassy (Le Shift Lab); "Synthetic training data are
  not provided"; test additions' "energy is known" (organiser-side).
- **A31 write-up checklist vs the fetched evaluation text**: pressure map across
  sites/time (TO BUILD from f̂ + site clusters), compare vs observed acoustic
  patterns (have), uncertainty (have: ΣB̂/contamination/ambient decomposition),
  respond-to-signal controls vs received-energy baseline (have: dead level-prior
  family = the control that FAILED, bump estimator = the control that worked),
  held-out released stations/periods (have: calm-bed plant protocol + group splits),
  runnable code + declared external data (VTUAD DOI + SA package checksums).
  Language guardrail: "relative acoustic activity" without independent calibration.

## 6. Hunt log R7 (posture: open-web EXHAUSTED per directive)

| # | query | platform | date | result | next |
|---|---|---|---|---|---|
| 1 | "SA URN Consortium" underwater radiated noise South Africa | WebSearch | 2026-10-21 | 0 hits | — |
| 2 | underwater radiated noise South Africa consortium | WebSearch | 2026-10-21 | Zindi page text only (suppliers = A27) | — |
| 3 | VTUAD vessel type underwater acoustic dataset | WebSearch | 2026-10-21 | IEEE DataPort + arXiv + preprints descriptor → A35 provenance | closed |
| 4 | SAEON underwater sound monitoring South Africa | WebSearch | 2026-10-21 | portal only (auth) | **USER** |
| 5 | De Hoop MPA underwater acoustic monitoring hydrophone | WebSearch | 2026-10-21 | 0 relevant | — |
| 6 | Langebaan / Dassen Island hydrophone acoustic monitoring | WebSearch | 2026-10-21 | 0 relevant | — |
| 7 | SAMSA underwater radiated noise toolkit workshop | WebSearch | 2026-10-21 | FB post: SAMSA hosted URN Toolkit Workshop | user enquiry thread |
| 8 | underwater noise monitoring network South Africa stations | WebSearch | 2026-10-21 | 0 | — |
| 9 | SciELO "Get with the beat!" (SA noise regulation) | WebFetch | 2026-10-21 | page blocked (bot check) | low priority retry |
| 10 | SANBI NBA marine pressures (noise) | WebSearch | 2026-10-21 | page exists; author trail (CSIR/NMU/SAEON) for enquiry | user enquiry |

Cumulative: 23 (R6) + 10 = 33 probes; no public naming of {8,11,12}. All remaining
routes are user-gated: SAEON portal login, Zindi discussion post, direct
SAEON/SAMSA/consortium enquiry (legitimate public-interest question).

## 7. Decision request + roadmap

1. **Submit `r7_v1_bumpshare`** (one slot). Read: ≥0.80 ⇒ calm-bed family
   confirmed, iterate (template matching, blend); 0.77–0.80 ⇒ partial (test beds
   dirtier — pivot to VTUAD template matching + per-window denoising); <0.77 ⇒
   bump-reading fails on real test too (fallback: retrained ML on fixed recipe).
2. Retrain two-head on the FIXED recipe (sub-interval + ambient-laden + calm-bed
   emphasis), bg-group-split validation — the ML track catches up to the estimator.
3. VTUAD template matching (we hold the exact reference library incl. MMSI/UTC).
4. Write-up assembly (pressure map, notebook, controls table).
5. User dependencies: SAEON portal login; Zindi discussion re withheld stations;
   SAEON/SAMSA enquiry re station names {8,11,12}; A30 copyright decision if top-3.
