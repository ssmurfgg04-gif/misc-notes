# R9-A intel report — VTUAD + vessel-noise literature/code deep-mine

**Agent:** general-purpose (R9-A). **Date:** 2026-10-21. **Probes:** ~36 web fetches
(arXiv API, Crossref API, Semantic Scholar, Zenodo API, GitHub API/raw, ar5iv fulltexts;
DDG/Bing/OpenAlex/IEEE-DataPort/preprints.org/grep.app were bot-walled or out of budget).

**Context assumed:** 25-band TOL 1-minute windows (15×25 context), predict
`share_added_vessel` (metric = 1 − RMSE), 10 SA train stations, 3 hidden test stations
(G0 west-coast-class / G1 St-Francis-class south coast / G2 harbour-class), engine =
quiet-baseline bump-reading + LGBM two-head (presence × conditional-share) on synthetic
mixtures of real vessel clips into real backgrounds. Known/excluded: VTUAD fixed-filter
97→84% bed confound; CATFISH metadata fusion 91.59→96.32%; Schoeman 2022 wind r>0.7
@1–2.5 kHz; Wenz/Knudsen; LGBM two-head; isotonic/distribution calibration;
self-training/mean-teacher; PANNs/BEATs embeddings (as a category).

---

## 0. The VTUAD lineage, pinned (resolves "which paper is VTUAD?")

- **Original benchmark paper** = Domingos, Santos, Skelton, Brinkworth, Sammut,
  "An Investigation of Preprocessing Filters and Deep Learning Methods for Vessel Type
  Classification With Underwater Acoustic Data", **IEEE Access 10:117582–117596, 2022,
  DOI 10.1109/ACCESS.2022.3220265** (open access; PDF bot-walled to us). Benchmark:
  1-s clips, Strait of Georgia (ONC icListen ICLISTENAF2523), 4 vessel classes +
  **background class from the same source**; 3 range scenarios
  (incl.2000/excl.4000, incl.3000/excl.5000, incl.4000/excl.6000 m); fixed-filter
  benchmark = 94.95/94.45/93.11 per-scenario, **84.13 combined**; Tug↔Background
  confusion 14%/6%.
- **Dataset re-release (2026, the "Yuan et al." descriptor):** Yuan, Wang, Li, Chen,
  Zeng, Liu, "**VTUAD: An AIS-Auto-Labeled Vessel-Type Underwater Acoustic Dataset
  Reconstructed from Ocean Networks Canada Archives**", Preprints
  **10.20944/preprints202609.0617.v2**; data on Zenodo **10.5281/zenodo.23037895**
  (v1.2.0; audio snapshot 10.5281/zenodo.22773623). 525 clips (~56 h, 32 kHz), 12
  classes, **133,784 precomputed 16 kHz/3 s/128-bin log-mel segments**, recording-level
  frozen split 369/80/76, per-clip MMSI + vessel dimensions + 22 CTD covariates,
  plus audit files `clip_acoustic_stats.csv`, `cut_rule_simulation_525clips.csv`,
  `wraparound_splice_clips_v1_README` (they audited the clip cut rule and wrap-around
  splice artifacts — a hint that **window boundary artifacts are real** even in
  band-domain pipelines). ResNet-18 reference baseline; labels explicitly
  "AIS-derived silver-standard".
- **Code:** original pipeline github.com/lucascesarfd/onc_dataset (13-step ONC+AIS+CTD
  labeling pipeline: single-vessel-in-inclusion-radius intervals, 1-min normalized
  audio pieces, CTD metadata fusion, balanced undersampling, random splits);
  baselines repo "nauta" github.com/mominali12/vtuad_personal (ResNet18/VGG/FFN over
  **mel / CQT / gammatone**, 3-representation stacking config); SOTA model CATFISH
  github.com/Jotels/CATFISH (EfficientLEAF Gabor frontend → EfficientNet-B0 → 2-D
  attention pool → CTDSV fusion; `tbn_median_filter`, `log1p_per_band`,
  `label_smoothing=0.1`).
- **CATFISH ablation (arXiv 2505.23964, Table 2)** — fine-grained beyond R7e's one-liner:
  learnable filters alone (max-pool, no metadata) = **91.59** combined; +CTDSV metadata
  (still max-pool) = **96.32**; +attention only = 96.23; both = 96.63. ⇒ **either**
  metadata fusion **or** better pooling recovers nearly all of the 12-pp gain — a
  strong prior that our cheap covariate route (T1 fingerprints) captures most of what
  a full NN branch would.

---

## 1. Sorted findings (CRITICAL → MEDIUM → LOW)

| # | Grade | Finding | One-line fit to our setup |
|---|-------|---------|---------------------------|
| F1 | **CRITICAL** | CORAL/moment-matching feature alignment between stations (2026 four-corpus UDA benchmark) | Closed-form, label-free band-power shift correction toward each test station; most reliable UDA family on the VTUAD domain; MMD shown to *negatively* transfer |
| F2 | **CRITICAL** | AdaBN/"BN-statistics alone suffice" SFUDA = test-station re-standardization of frozen features | Literature-validated recipe for T1: adapt only per-station location/scale stats of features, keep model frozen; robust to contamination; entropy-min/TENT-style adaptation collapses reproducibly |
| F3 | **CRITICAL** | CATFISH LogTBN per-band detrend: log1p w/ per-band gain + running **median** filter, raw+median dual channel | Directly implementable on 15×25 band powers: robust wind/background detrending features (bumps survive, slowly-varying bed removed) — from the VTUAD SOTA model's own config |
| F4 | **CRITICAL** | PCEN adaptive gain control (LEAF) on band-power time series | Data-driven per-band automatic gain control that suppresses stationary background and preserves transients; the principled version of "excess over quiet bed" |
| F5 | **CRITICAL** | UniqueShip leakage audit: random splits inflate UATR accuracy by 10–48 pp; **vessel diversity ≫ duration** | Hard evidence for vessel-ID-disjoint mixture-factory validation; says spend factory capacity on more unique vessel clips, not more segments |
| F6 | **CRITICAL** | CATFISH Δ-band diagnostic: discriminative band set **narrows with range** (only lowest bands survive at far range) | For faint windows, low bands carry nearly all signal → SNR-dependent band weighting / low-band-weighted presence features |
| F7 | **MEDIUM** | MFAV: Frequency-Amplitude-Variation statistic + statistical threshold for ship detection (JASA 2026, open-source) | Wind noise is spectrally *flat*, vessels are band-*variable* — add FAV-style cross-band and cross-time variation features to LGBM |
| F8 | **MEDIUM** | Sea-state study: model trained at **sea state 7 generalizes best** across states | Over-represent windy/heavy backgrounds in the mixture factory (hard negatives) for test-station robustness |
| F9 | **MEDIUM** | Spectral Probability Density (Merchant 2013) as per-band distribution features | Replace single P20 bed with full per-band level distribution (P5/P50/P95, mode, entropy, mass-above-threshold) per station context |
| F10 | **MEDIUM** | Piecewise log-linear wind→noise models + latent-wind tracking (Kalman) | Formalize T2: wind proxy from 1–2.5 kHz, predict per-band wind level, subtract; wind state as latent AR process tracked across windows |
| F11 | **MEDIUM** | Zero-inflated Beta / evidential heads + per-window risk (Hong 2026 UAMS-DSS) | Two-head = ZOIB; get per-window uncertainty → **adaptive shrinkage k per window** instead of one global k |
| F12 | **MEDIUM** | Weighted conformal prediction under covariate shift | Density-ratio-reweighted calibration residuals give label-free per-window intervals under site shift; supports deferral/shrinkage |
| F13 | **MEDIUM** | Mixture-consistency projection (source-separation classic) | Physics constraint: vessel+background = observed; closed-form projection of share estimates onto the per-station bed→vessel-template line; also a residual feature |
| F14 | **MEDIUM** | Sqrt-smoothed class weights + focal loss + macro-metric checkpointing (four-dataset direct-transfer benchmark) | Presence-head imbalance recipe; naive inverse-frequency weighting destabilizes |
| F15 | **MEDIUM** | Recording-identity probe (SimCLR study) as a shift-diagnostic | Cheap sanity check: how separable are stations from our features? Warns that SSL embeddings encode *station*, not vessel |
| F16 | **MEDIUM** | Frozen-FM transfer study: BEATs best on VTUAD macro-F1; AST/CLAP (environmental) beat speech FMs; scale doesn't help; source-validation selection works | Sharpens T5: prefer BEATs/CLAP-style embeddings; select probes by source-validation only; expectations modest (permutation control) |
| F17 | **MEDIUM** | Oceanship dataset (121 h, 15 classes, AIS metadata) | Extra real-vessel clip source for the mixture factory → vessel diversity per F5 |
| F18 | **LOW** | ERB/gammatone band recombination (Hearing-the-Ocean 2026) | Optional re-aggregation of deci-decades on ERB scale for features |
| F19 | **LOW** | Passive-sonar texture statistics (GLCM/AM–PM texture metrics, code released) | Cheap extra descriptors on the 15×25 matrix; explicit texture modeling beat CNNs on textured synthetic sonar |
| F20 | **LOW** | CQT + dynamic-programming change-point features (Li 2024 DDCLS, CAM++) | Per-band change-point statistics on the 15-min trajectory |
| F21 | **LOW** | HPT learnable soft-histogram layer (target-domain statistics injected into embeddings) | NN-only; its non-learnable shadow = per-feature histogram matching (fold into F2) |
| F22 | **LOW** | Adaptive cepstral filtering for multi-path (2512.11165) | Reverberation/multipath cleanup — raw-audio domain; band powers already integrate paths |
| F23 | **LOW** | ONC ecosystem code (api-python-client, oncdw, BC-ferries AIS notebooks, SSAMBA anomaly SSL) | Provenance/AIS-label tooling + anomaly-detection framing; no direct inference features |
| F24 | **LOW** | Wave parameters add <0.3 dB over wind speed alone for AN prediction (Rogers 2024) | Don't invest in swell-proxy features beyond existing state splits |

---

## 2. Per-finding details

### F1 — CORAL moment matching between stations · **CRITICAL**
- **Source:** Yuan, Wang, Li, Chen, Huang, Li, "Unsupervised Domain Adaptation for
  Cross-Water Underwater Acoustic Target Recognition: A Four-Corpus Benchmark",
  Preprints 10.20944/preprints202609.1124 (2026); artifacts 10.5281/zenodo.23028253.
- **Technique:** Benchmarks source-only vs CORAL vs multi-kernel MMD vs DANN/CDAN on
  4 UATR corpora. CORAL = align source feature covariance to target covariance
  (whitening+re-coloring); moment matching is consistently **more stable than
  adversarial** training; on the VTUAD domain CORAL is the most reliable method while
  MMD produced the study's significant **negative transfer** (−0.190 macro-F1);
  adaptation is direction-asymmetric; even when oracle-locked, UDA's measurable value
  includes **accuracy-variance compression and class-bias correction**.
- **Fit:** We have band-power feature matrices per station; CORAL is a closed-form
  matrix transform — map each test station's windows with train-pool statistics
  (or per-source-station pooled CORAL). No labels, no raw audio, trivially inside
  LGBM pipeline (transform features at inference). The paper's negative-transfer
  warning says: prefer CORAL over MMD-style alignment, and validate direction.
  Plausibly ≥0.005 via de-confounding G0/G1/G2 level/tilt shifts.
- **Caveats:** CORAL on all 25+engineered dims can amplify noisy bands; align on
  robust band subset first. Keep the identity transform as an ensemble member.

### F2 — AdaBN-equivalent: test-station re-standardization of frozen features · **CRITICAL**
- **Source:** Yuan et al., "Source-Free Domain Adaptation for UATR: When Batch
  Normalization Statistics Alone Suffice", 10.20944/preprints202609.1126 (2026);
  companion "Open-World Source-Free Adaptation … Adaptation Survives, Post-hoc
  Rejection Does Not", 10.20944/preprints202609.1683 (2026).
- **Technique:** First SFUDA benchmark for UATR. bn_adapt (AdaBN: re-estimate BN
  mean/var on unlabeled target; zero gradients, 15–25 s) is the strongest SFUDA
  method, statistically indistinguishable from best source-data UDA; restores a
  collapsed class from 0/1214 to 380/1214. Gradient SFUDA (TENT) reproducibly
  collapses to one class (its own label-free selection then picks the collapsed
  model); SHOT drifts class-biased. Under 3–6× unknown-class contamination,
  BN-stats adaptation loses ≤0.009 macro-F1. Post-hoc rejection (MSP/Energy/OpenMax)
  fails (AUROC ≈ chance) — "adaptation survives, post-hoc rejection does not".
- **Fit:** Our tabular analogue of AdaBN = per-station re-standardization
  (robust median/MAD or bed-anchored) of every feature before the LGBM —
  essentially T1's per-station SNR normalization, now literature-backed with the
  specific recipe *adapt only normalization stats, never the model, at test time*.
  Also a warning for T4: entropy-driven self-training can collapse; keep
  confidence-filtering + diversity checks (we knew; this quantifies the risk).
- **Grade:** CRITICAL — direct, cheap, targets exactly our G0/G1/G2 shift.

### F3 — LogTBN: per-band log1p gain + running-median dual channel · **CRITICAL**
- **Source:** CATFISH code, github.com/Jotels/CATFISH (`classifier_config.yaml`,
  `train.py`, EfficientLEAF frontend); Schlüter & Gutenbrunner, EfficientLEAF,
  EUSIPCO 2022; arXiv 2505.23964.
- **Technique:** The SOTA VTUAD frontend replaces PCEN with a compression block:
  per-band trainable log-gain `y=log(1+10^a_k·x)` followed by **Temporal BatchNorm
  with a median filter** (config: `tbn_median_filter: true`,
  `tbn_median_filter_append: true` → the network consumes **two channels: raw and
  median-filtered** per band). Median filtering removes slowly-varying background
  while preserving transient structure; the appended raw channel keeps absolute level.
- **Fit:** Fully implementable in band-power space: per band over the 15×25 context
  (or a longer train-side history per station), compute `x / running_median(x)` (or
  `x − running_median` in dB), plus log1p-with-per-band-gain compression, and feed
  BOTH raw and median-detrended channels as features (the explicit dual-channel
  trick is the steal). This is a drop-in feature block for the LGBM and a better
  bump-readout basis.
- **Grade:** CRITICAL — cheap, comes from the exact model that fixed the VTUAD
  background confound.

### F4 — PCEN on band-power time series · **CRITICAL**
- **Source:** Zeghidour et al., "LEAF: A Learnable Frontend for Audio
  Classification", arXiv 2101.08596 (PCEN: Wang, Dehak et al. lineage); PCEN
  parameters used in LEAF code: s=0.04, α=0.96, δ=2.0, r=0.5; CATFISH repo
  (`from leaf.leaf import PCEN`).
- **Technique:** Per-Channel Energy Normalization: an EMA background estimate per
  band (agc strength s), followed by exponential compression — `PCEN[t] =
  (ε + EMA[t])^α · (x[t]/(ε + EMA[t]))^... ` family — i.e., automatic gain control
  that whittles stationary/slowly varying noise (wind, swell, rig hum) and keeps
  onsets/transients with a soft dynamic-range compression.
- **Fit:** Our windows are ordered in time within station sequences; PCEN across
  windows per band = a data-driven, smoothing-parameter-controlled version of
  "excess over quiet bed", with different time constants than the P20 bed
  (multi-scale: two PCEN layers with different s = two background trackers).
  Band-level only; no raw audio needed; site-robust because it's *relative*.
- **Grade:** CRITICAL (as engineered features; s must be tuned on group-split val).

### F5 — UniqueShip leakage audit + vessel-diversity law · **CRITICAL**
- **Source:** "UniqueShip: Mitigating Data Leakage in Acoustic Ship Classification
  Benchmark Datasets", arXiv 2609.13659 (2026); 2,460 h, 4,218 unique ONC vessels;
  uniqueshipdata.org.
- **Technique:** Shows typical random partitioning inflates UATR test accuracy by
  **10–48 pp** vs vessel-disjoint partitioning; ablations: **doubling unique vessels
  +2.4–2.6 pp vs doubling duration +0.8–1.3 pp**; vessel metadata predicts
  classification difficulty better than distance alone.
- **Fit:** (1) Validate the mixture factory with vessel-ID-disjoint splits
  (plan §6h/§7g already prescribes hull-ID enforcement — this paper quantifies the
  stakes). (2) Factory curation: prioritize number of distinct vessel clips/tonals
  over clip count. (3) Difficulty covariates from vessel metadata (length/speed
  class) — we don't have AIS at inference but can use them to *weight training
  mixtures* (e.g., more small-vessel diversity ≈ our faint-bump regime).
- **Grade:** CRITICAL — protects every validation number we will report.

### F6 — Δ-band diagnostic: discriminative bands narrow with range · **CRITICAL**
- **Source:** CATFISH paper §"Filter activation variability" (arXiv 2505.23964),
  Figs 4–5; class-conditional mean activation delta (Tug−Background) per filter.
- **Technique:** Δ-spectrograms show discriminative filter range contracting from
  ≈0–60 (close) to ≈0–10 (far): at low SNR only the lowest-frequency filters retain
  vessel-vs-background contrast.
- **Fit:** Mirror as an interpretable band-power diagnostic (per station, Δ between
  high-share and near-zero windows, over the 25 deci-decades) and *use it as a
  feature/factor*: at low estimated SNR, down-weight high bands (which wind owns)
  and up-weight low-band excess. Cheap, deterministic, explainable in the write-up.
- **Grade:** CRITICAL — a physics-consistent gating rule for the presence head.

### F7 — MFAV / FAV band-variation statistic · **MEDIUM**
- **Source:** Jedari-Eyvazi, Frazão, Halliday, Gehrmann, Menelon, Dingwall, Whidden,
  Dowd, "Advancing passive acoustic ship detection in the Western Canadian Arctic:
  Signal processing and deep learning approaches", JASA 2026, 10.1121/10.0043937;
  open-source tool per paper (repo not yet surfaced by search).
- **Technique:** Modified Frequency Amplitude Variation (MFAV) — a statistic of
  amplitude variation across frequency (+ statistical threshold) for ship-noise
  detection; CNN beats it by 1–8 pp F1 overall, but MFAV **improves small-boat
  detection by up to 22%** and stays interpretable.
- **Fit:** Band-level features: cross-band dispersion of excess (e.g., std/range of
  band excess after bed removal), temporal amplitude variation per band across the
  15 windows; vessels (engine/propeller bands) are *variable*, wind is *flat*.
  Direct LGBM features; also an interpretable threshold rule like our bump reader.
- **Grade:** MEDIUM — conceptual fit strong; needs our re-derivation since the
  exact statistic is behind the paper/tool.

### F8 — Train on the roughest conditions to generalize · **MEDIUM**
- **Source:** "Passive Acoustic Classification of Marine Vessels under the Influence
  of Range, Sea States and Seasonal Changes in Sound Speed Profiles", J. Vib. Eng.
  & Technol. 2026, 10.1007/s42417-025-02295-6.
- **Technique:** Simulation study (Bellhop propagation + sea-state ambient); CNN
  trained on sea state 7 **generalized best** across all sea states; ~30% drop at
  25 km range; classification critically range-dependent in convergence/shadow zones.
- **Fit:** Mixture-factory scenario: over-sample windy/heavy-sea real backgrounds
  (and faint far-vessel injections) as hard negatives/positives; check per-sea-state
  validation deltas. Zero new inference cost.
- **Grade:** MEDIUM — one-line change to scenario weights.

### F9 — Spectral Probability Density features · **MEDIUM**
- **Source:** Merchant, Barton, Thompson, "Spectral probability density as a tool
  for ambient noise analysis", JASA 2013, 10.1121/1.4794934 (105+ cites);
  implemented in `pypam` (lifewatch/pypam).
- **Technique:** Instead of medians/means, model each band's *full distribution* of
  levels over time; report percentiles, modal level, spread, exceedance — non-vessel
  periods concentrate; events populate tails.
- **Fit:** Per station per band: P5/P20/P50/P80/P95, mode, IQR, tail mass above
  P80 — richer than our single P20 bed; powers F6/F7/F10 features; all band-level
  and station-relative.
- **Grade:** MEDIUM — cheap feature expansion; marginal over P20 alone but
  stacks.

### F10 — Piecewise log-linear wind models + latent-wind tracking · **MEDIUM**
- **Sources:** Ragland & Abadi 2025 ESSOAr preprint 10.22541/essoar.175611483.33956799
  (OOI 8-yr, piecewise log-linear AN-vs-wind fits, 0.1–90 Hz); Cho, Kim, Kang,
  Ocean Engineering 2021, 10.1016/j.oceaneng.2021.108653 (shallow-water
  wind-dependent ANL estimation); "Sequential filtering for surface wind speed
  estimation from ambient noise", China Ocean Eng. 2017, 10.1007/s13344-017-0009-2
  (Kalman tracking of wind from noise); Rogers et al. 2024, arXiv 2403.18728 (wave
  parameters improve wind-only AN prediction by <0.3 dB).
- **Technique:** Ambient-noise-vs-wind is piecewise log-linear per band (Wenz);
  wind can be *tracked* as a latent slowly-varying state from noise measurements
  via sequential filtering; extra wave params are marginal.
- **Fit:** T2 formalization: per station, estimate a wind-state proxy from the
  1–2.5 kHz-ish high bands (Schoeman: r>0.7), fit/assume piecewise log-linear
  responses for other bands, subtract predicted wind level → wind-detrended excess
  features; optionally smooth the wind state across consecutive windows (Kalman or
  simple EMA) to resist local outliers.
- **Grade:** MEDIUM — exactly T2, with a principled shape (piecewise linear in
  log-level) and a tracking upgrade; not more than that since we have no true wind.

### F11 — Zero-inflated Beta / evidential per-window risk → adaptive shrinkage · **MEDIUM**
- **Sources:** Hong, "A Trustworthy Expert Decision-Support System for Underwater
  Acoustic Vessel Classification under Domain Shift", SSRN 10.2139/ssrn.7359216
  (2026) — evidential uncertainty + OOD scoring + risk-aware actions; ZIB
  regression: Liu et al., arXiv 2112.07249.
- **Technique:** Separate *recognition evidence* from *reliability estimation*;
  produce calibrated uncertainty per sample and act on it (accept/monitor/defer).
  For 0–1 targets with zeros, ZOIB (zero-inflated beta) is the proper likelihood.
- **Fit:** Our two-head *is* a ZOIB structure; upgrade = fit a small post-hoc
  beta calibration on the conditional-share head (mean + dispersion as functions
  of predicted share and OOD proxy) → per-window predictive variance → replace the
  single global shrinkage k by k(window) (e.g., shrink toward per-station μ by
  a factor decreasing with confidence). This directly targets RMSE: shrink more
  exactly where the head is uncertain (G1-like windows).
- **Grade:** MEDIUM — plausible ≥0.005 if G1 concentration of error is as large
  as our A60/A62 analysis suggests.

### F12 — Weighted conformal prediction under covariate shift · **MEDIUM**
- **Sources:** arXiv 2501.11413 (weighted conformal risk control), 2404.15018
  (conformal predictive systems under covariate shift), Tibshirani et al. 2019
  lineage.
- **Technique:** Reweight calibration residuals by an estimate of the
  target/source covariate density ratio; yields valid prediction intervals for
  shifted targets without target labels.
- **Fit:** Density ratio between each test station's window features and the train
  pool (estimated on 2–4 robust dims or a domain classifier) → weighted quantiles
  of validation residuals → per-window interval width = per-window shrinkage
  signal (composes with F11).
- **Grade:** MEDIUM — principled but density-ratio estimation noise in 25 dims;
  keep it coarse.

### F13 — Mixture-consistency projection · **MEDIUM**
- **Source:** Source-separation literature (mixture consistency, Wisdom et al.
  2019; still standard, e.g., arXiv 2609.07226, 2510.08914).
- **Technique:** Constrain/adjust model outputs so sources sum to the mixture:
  the projection is closed-form and improves any separation-style estimator.
- **Fit:** In power domain our band levels are approximately additive:
  `x_b ≈ s·V_b + (1−s)·B_b`. With a per-station background template B and a
  vessel template/dictionary V (from bump profiles), the LS-optimal share on the
  line between B and V is a closed-form projection: `s = ⟨x−B, V−B⟩/‖V−B‖²`
  clipped to [0,1]. Use as (a) a strong engineered feature ("projection share"),
  (b) a sanity-blend component for the final estimator, (c) an audit of what the
  LGBM learned. This is the physics version of our bump reading and is
  deterministic per station.
- **Grade:** MEDIUM — cheap, explainable, likely wins on near-zero windows via
  shrinkage-friendly residuals.

### F14 — Sqrt-smoothed class weights + focal loss + metric checkpointing · **MEDIUM**
- **Source:** Yuan et al., "Cross-Archive Generalization … Four-Dataset
  Direct-Transfer Benchmark", 10.20944/preprints202609.0919 (2026); artifacts
  10.5281/zenodo.23312809.
- **Technique:** Under 4,278:1 imbalance, sqrt-smoothed weights raise macro-F1
  (0.1302→0.1452) while inverse-frequency destabilizes; focal loss +
  macro-metric checkpoint selection win the ablation; direct cross-dataset
  transfer collapses in all 12 directions (same-region pair 0.9%!) ⇒ dataset shift
  is label-provenance/scenario/sensor driven, not just water.
- **Fit:** Presence-head loss/weighting recipe; and a sobering expectation-setter:
  raw cross-station transfer will fail — station-relative (T1/F1/F2) features are
  the right response, not more raw capacity.
- **Grade:** MEDIUM.

### F15 — Recording-identity probe as shift diagnostic · **MEDIUM**
- **Source:** Yuan et al., "Evaluating In-Corpus SimCLR Pretraining for UATR Under
  Recording-Disjoint Splits", 10.20944/preprints202609.0999 (2026); artifacts
  10.5281/zenodo.23411528.
- **Technique:** In-corpus contrastive SSL *under-delivered*: features encoded
  recording identity (recording-ID probe reads IDs near-perfectly), with val-test
  gaps; prescribes cross-site pretraining, channel-varying augmentation, balanced
  sampling, recording-identity controls.
- **Fit:** (1) Cheap diagnostic for us: train LGBM to predict station from our
  feature vector; inspect what it uses (should be bed/tilt/masking — if it keys on
  vessel bands, leakage risk in synthetic val). (2) Warning for T5/embedding
  branches: frozen embeddings may encode station, inflating fingerprint features
  and hurting share regression — normalize per station before any embedding probe
  (matches Hummel caveat already in plan).
- **Grade:** MEDIUM — zero-risk diagnostic, informs both T4/T5 safety.

### F16 — Frozen-FM transfer: model choice + selection rule · **MEDIUM**
- **Source:** Yuan et al., "…Zero-Target-Label Cross-Water Transfer of Frozen
  General-Purpose Audio Foundation Models…", 10.20944/preprints202609.1744 (v3,
  2026); artifacts 10.5281/zenodo.23345657.
- **Technique:** 8 FMs × 4 corpora: BEATs leads on VTUAD macro-F1 (slightly above
  the trained ResNet-18 reference on ShipsEar); AST/CLAP (environmental pretraining)
  beat speech-pretrained in 6/8 cells; wav2vec2-large never beats base; cross-corpus
  frozen-FM probes beat trained-model zero-shot in 11/12 directions; a
  **source-validation selection rule** beats trained baselines in 7–11/12
  directions; permutation controls keep claims modest.
- **Fit:** If T5 runs: pick BEATs/CLAP-class embeddings, per-station normalize,
  select any probe by source-validation only, and demand the same permutation
  control we already use.
- **Grade:** MEDIUM — refines an existing plan item rather than adding one.

### F17 — Oceanship as extra vessel-diversity source · **MEDIUM**
- **Source:** "Oceanship: A Large-Scale Dataset for Underwater Audio Target
  Recognition", arXiv 2401.02099 / 10.1007/978-981-97-5591-2_40.
- **Technique:** 121 h, 15 vessel categories, AIS-derived metadata (coordinates,
  speed, timestamps) from ONC archives.
- **Fit:** More unique vessel clips → mixture factory diversity (per F5, this is
  the high-yield axis). Requires the same band-power inverse transform we already
  run for VTUAD clips.
- **Grade:** MEDIUM (data work, not inference).

### F18–F24 — LOW band
- **F18 ERB/gammatone aggregation** (Tripathi et al., arXiv 2605.04839,
  "Hearing the Ocean"): recombine deci-decades on an ERB scale (weights), cheap
  feature variant. LOW — our bands are already deci-decade fixed.
- **F19 Sonar texture statistics** (arXiv 2504.14843 +
  github.com/Advanced-Vision-and-Learning-Lab/Passive_Sonar_Texture_Analysis):
  GLCM/statistical texture metrics on spectrograms; explicit texture modeling beat
  CNNs on statistically textured sonar. LOW — a handful of extra LGBM features on
  the 15×25 matrix.
- **F20 Change-point features** (Li et al., DDCLS 2024, 10.1109/ddcls61622.2024.10606598):
  CQT + dynamic-programming change-point statistics + CAM++; 98.15% on VTUAD S1.
  LOW — per-band segmentation stats on the 15-window trajectory.
- **F21 HPT** (arXiv 2504.15214, 91.8 vs 89.8 on VTUAD): learnable soft-histogram
  (RBF bins) layer aligning target-domain statistics; NN-only; non-learnable
  shadow = histogram matching per feature (fold into F2). LOW.
- **F22 Cepstral adaptive filtering** (arXiv 2512.11165): multipath/reflection
  removal in spectrograms; raw-audio domain. LOW.
- **F23 ONC ecosystem** (github.com/OceanNetworksCanada: api-python-client, oncdw,
  python-community-notebooks incl. BC-ferries AIS pairing, selfsupervision_anomalies_onc
  = SSAMBA masked-audio-Mamba anomaly detection): useful if we ever fetch ONC AIS/
  hydrophone archives for SA-adjacent silver labels; SSAMBA is raw-audio. LOW.
- **F24 Wave parameters** (arXiv 2403.18728): <0.3 dB RMSE gain of wave params over
  wind speed for AN prediction ⇒ don't build swell proxies. LOW (negative result,
  saves time).

---

## 3. What NOT to adopt (checked and rejected)

- **MMD-style alignment** (documented negative transfer −0.190 macro-F1 on the
  VTUAD domain; F1 uses CORAL instead).
- **Entropy-minimization test-time adaptation (TENT-style)** for self-training:
  reproducible collapse in 2–5 of 5 seeds, and its label-free selection criterion
  *prefers* the collapsed model (F2 sources).
- **Post-hoc rejection scores (MSP/Energy/OpenMax)** as our OOD gate: pooled AUROC
  ≈ chance in the OSFUDA study; if we need an OOD proxy, use feature-space /
  density-ratio signals (F11/F12) instead.
- **Naive inverse-frequency weighting** of the presence head (F14).
- **In-corpus SSL pretraining as a shortcut** (F15): encodes recording identity.

## 4. Suggested build order (delta to plan §7h; decisions belong to the main agent)

1. F3+F4 (LogTBN-style median-detrend dual channels + PCEN multi-scale) as pure
   feature block in train_v3_v31 — composes with T1 fingerprints.
2. F2 (test-station robust re-standardization of the full feature vector; the
   AdaBN analogue) — formalizes T1.
3. F1 (CORAL alignment on robust band subset, train→test-station; keep identity
   as ensemble arm).
4. F6+F7 (low-band weighting at low SNR; FAV-style dispersion features).
5. F13 (projection-share feature + optional blend), F5 (factory: vessel-ID
   disjoint splits + diversity weighting; F8 rough-condition over-sampling).
6. F11/F12 (per-window adaptive shrinkage from ZOIB-calibrated variance or
   weighted-conformal intervals) — replaces/augments the single global k.
7. F15 (station-identity probe) as a standing diagnostic; F9/F14/F10 as
   opportunistic additions.

Everything above is band-power-level or post-hoc tabular — nothing needs raw audio
at inference, and all validation hooks (group-split, permutation, vessel-ID
disjointness) already exist in the plan.
