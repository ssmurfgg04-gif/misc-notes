# R10-B intel report — VTUAD round 2: full-text/code-level extraction + new sweeps

**Agent:** general-purpose (R10-B). **Date:** 2026-10-22. **Probes:** ~60 network probes
(Zenodo API + file downloads ×~35, Crossref ×~12, arXiv API ×~7, Semantic Scholar ×~12,
preprints.org ×4, jina proxy, GitHub codeload/raw, GitHub HTML). **preprints.org remains
bot-walled (403) for HTML+PDF and r.jina.ai now demands auth — full text was obtained
instead from the authors' own released artifacts (code + audit packs), which is better
than prose because it is the exact executable pipeline.**

**Context assumed (unchanged from R9-A):** 25-band TOL minute windows (15×25),
`share_added_vessel` regression (metric 1 − RMSE), 10 SA train stations, 3 hidden test
stations; quiet-baseline bump + LGBM two-head; R8 validated T1/T2; planned CORAL/AdaBN,
PCEN, LogTBN median-detrend. Rival ruicodex declared "VTUAD rebuilt v1.3.2 + minute
deci-decade band power from the starter conversion".

**Local artifacts added this round** (all downloaded + extracted, cached in
`data/zenodo_r10/`): `v120/` = the released VTUAD-rebuild construction + benchmark code;
`per_seed_test_predictions_s42-46.csv` (5×18,202 rows); companions `paper2_code/`
(UDA), `paper4/` (SFUDA + BN-layer ablation), `paper3_code/`, `paper8_a10_supplement_v3/`,
`paper2_uda_v2_oracle_summary/`; `CATFISH-main/` full repo; audit-pack docs
(`static_audit_README.md`, wraparound README, `rev1_paired_bootstrap_s42-46.json`).

---

## 0. The rival's foundation, pinned at code level (resolves target #1)

The Yuan et al. 2026 preprint (10.20944/preprints202609.0617, Crossref abstracts only —
v1 and v2 retrieved; no full-text HTML reachable) is fully reconstructible from the
**released v1.2.0 code zip** inside Zenodo 10.5281/zenodo.23037895
(file `zenodo_vtuad_v1.2.0.zip`, 163 KB → `code/`): this is the six-stage pipeline's
actual implementation (Domingos 13-step code with the rebuild's frozen config), plus the
v1.3.1/v1.3.2 audit pack docs. Everything ruicodex builds on is below.

### C1 · CRITICAL — Exact feature + baseline recipe of the "VTUAD rebuilt" stack
- **Log-mel config (frozen, `code/benchmark/preprocess_audio.py`):** resample 32 kHz →
  **16 kHz**; segment **3 s, hop 1.5 s** (50% overlap); `n_fft=1024, hop_length=320`
  (20 ms), **n_mels=128**, power=2.0, `librosa.power_to_db(ref=np.max)` — i.e. **per-3s-segment
  max reference**, not absolute dB (relative-to-max spectrograms). Segments <3 s dropped
  (`pad_short=False` in the released v1.2.0 store). Mono = channel mean.
  LOFAR/DEMON channels exist in code **as stubs only** (placeholders, "TODO paper 3").
- **ResNet-18 baseline (`code/benchmark/train_baseline.py`):** torchvision ImageNet1k
  weights, conv1 collapsed to 1 channel by summing; AdamW lr 1e-3, wd 1e-4, cosine
  T_max=epochs, epochs 30, batch 64, patience 8, AMP, seed 42–46; **SpecAugment optional**
  (2 freq masks ≤16, 2 time masks ≤24, zero-fill); optional inverse-frequency class
  weights with power exponent (0.5 = sqrt); global mean/std from ≤3,000 train segments.
- **Six-stage label rules (`code/src/`):** per-1-minute AIS scan (pandas Grouper,
  label=left); vessel scenario = **exactly 1 unique MMSI within exclusion radius AND all
  messages inside exclusion radius also within inclusion radius**, ≥2 consecutive minutes
  (`minimum_consecutive_minutes=2`); background = **0 vessels within exclusion radius,
  ≥30 consecutive minutes**; radius ladder 1–10 km step 1 km, **exclusion = inclusion +
  2,000 m** (`get_exclusion_radius`), released tier = in_4000/out_6000; uniqueness by
  ceding intervals from larger radii down to smaller; AIS track **linear interpolation for
  gaps 20 s–1,200 s** (positions, SOG, COG, heading; static fields ffill) before the
  minute scan; equal-difference minute grouping (drops the first minute of every run;
  bridges constant-step gaps — quantified in the audit pack).
- **Split:** GroupShuffleSplit recording-level, 369/80/76 clips; segments
  95,103/20,479/18,202 = 133,784 (asserted in `v120_build/s3_features.py`).
- **Benchmark scores (from `rev1_paired_bootstrap_s42-46.json` + per-seed predictions,
  computed locally):** pooled 5-seed segment macro-F1 **0.2492 [0.167, 0.285]**, recording
  macro-F1 0.3048; per-class F1 (seed 42): sailing 0.752, passengership 0.628, cargo 0.563,
  tug 0.517, other 0.373, background 0.220, pleasurecraft 0.233, fishing 0.012, dredger
  0.022, tanker/pilotvessel/rescue 0 (no test support). **The baseline is NOT statistically
  better than majority-class (tug, 0.3851) at segment level: paired Δacc = +0.0205,
  CI [−0.059, +0.109], boot p = 0.604.** Dominant confusion: **everything → tug**
  (background→tug 1,659/2,555; fishing→tug 524/1,195; pleasurecraft→tug 380/916;
  tug→background 1,092/7,009). Seed spread is huge (seg F1 0.204–0.277).
- **Fit to us (T3/T6 intel, validation anchor):** ruicodex's surface = 16 kHz/3 s/128-mel
  log-mel + a near-majority classifier. There is **no regression head anywhere** in the
  released VTUAD stack — only 12-class classification. Their declared "minute deci-decade
  band power from the starter conversion" is the SAME 25-band TOL table we use; zero data
  asymmetry (R9-B), and now zero *recipe* asymmetry. The VTUAD background confound is
  precisely a **tug↔background** confusion — our quiet-baseline/bump framing attacks the
  same weak point from the regression side. Keep per-class F1 table as the documented
  weakness of any classifier-first rival pipeline. **Effort S** (all cached locally).

### C2 · CRITICAL — Audit-pack internals: cut rules, wraparound, first-minute drop
- **URLs:** https://zenodo.org/records/23037895 (files `interval_audit_readme.md`,
  `cut_rule_simulation_525clips.csv`, `vtuad_wraparound_splice_clips_v1_README.md`,
  `static_audit_README.md`, `wrap_feature_recompute_check.csv`).
- **What it says:** spell chain 541→511→509 closes exactly (110 spells ceded to smaller
  tiers, 40.4 h edge-trimmed, 75 spells split into 155 sub-intervals); the released
  grouping **drops the first minute of every run** (effective floors 3/31 min) and can
  bridge constant-step gaps (1 instance found at 3,000 m tier); MMSI continuity never
  tested (13/13 auditable clips clean). **Wrap-around splicing affects exactly 167
  single-source clips** (container = span + 300 s; the tail re-reads audio from *before*
  the labelled interval; 17 further multi-source extensions not wrapped); released
  features reproduce it (per-segment correlation ≥ 0.99996, mean |Δ| ≤ 0.07 dB vs
  independent recompute). Strict-interval re-cuts (v1.3.0+) remove it.
- **Fit (T4 data rule):** if/when we mine VTUAD strict WAVs for self-training, use the
  strict re-cuts (`vtuad_strict_wav_*.zip`) or trim containers to `utc_begin/utc_end`;
  for any comparability claim, container-level scores are the released reference. The
  first-minute-drop/gap-bridging defects are label-noise patterns our per-window
  regression is robust to, but they tell us the *labels* have ±1 min boundary slop —
  never anchor hard thresholds to VTUAD boundaries. **Effort S.**

---

## 1. Companion deposits opened at code level (target #2)

### C3 · CRITICAL — AdaBN (bn_adapt) exact recipe + BN-layer ablation (SFUDA paper 4)
- **URL:** https://zenodo.org/records/23455106 (`paper4_supplementary_repository_v4.zip`;
  `scripts/train_sfuda.py`, `docs/paper4_seeds5_bnlayer.md`, `scripts/eval_bn_layer_ablation.py`).
- **Exact config:** bn_adapt = reload frozen source-only ckpt → **reset ALL BatchNorm
  running stats → re-estimate with unlabeled target batches, cumulative moving average
  (`momentum=None`), batch 64, `drop_last=True`, NO augmentation during stats estimation
  (clean stats), zero gradients**. Model selection is label-free; TENT selects on target
  entropy (collapses), SHOT on IM loss.
- **BN-layer ablation (11 variants × 2 directions × 3 seeds, forward-only):** full 20-layer
  re-estimation best in both directions (o2q F1 0.4994, q2o 0.5140 vs source_only
  0.4482/0.3579); gains are **distributed** — q2o rises monotonically with layer coverage
  (first_half 0.4110 → first_75 0.4286 → all_but_bn1 0.4868 → full 0.5140); deep layers
  are the biggest single subsets (stage4_only best of singles both directions); **shallow-only
  re-estimation is harmful** (o2q stem_stage1 −0.121, stage2_only −0.119); first BN layer
  adds a small extra gain on top of all-but-bn1 (+0.032/+0.027). Re-normalizing the *input*
  per target instead (ablation `inputnorm`) hurts o2q badly (F1 0.3393).
- **n=5 headline upgrades:** bn_adapt significantly better than TENT both directions
  (paired t p=0.030/0.048) and SHOT o2q (p=0.044); TENT collapses 2/5 seeds exactly to the
  majority point; `tent_affine_only` collapses 5/5; SHOT drifts class-biased (acc always
  below majority, F1 near bn_adapt). bn_adapt vs best source-data UDA: not significant on
  o2q (vs CDAN p=0.098); on q2o MMD 0.5971 vs bn_adapt 0.4818 likely real (paired t p=0.039,
  permutation p=0.125).
- **Fit (T5 lock):** our tabular AdaBN = re-standardize **every feature block** (raw 25
  bands AND all engineered features) per test station from clean target windows using
  robust location/scale (median/MAD as the cumulative-MA analogue); **do NOT adapt only a
  subset or only raw bands**; do NOT re-scale inputs without re-standardizing downstream
  blocks. Shrinkage: their whitening/CORAL code contains **no shrinkage anywhere**
  (grep whiten/shrink/ledoit = 0 hits) — diagonal loading / Ledoit-Wolf is our own safety
  addition, justified by their variance findings. **Effort S.**

### C4 · CRITICAL — UDA benchmark exact configs + VTUAD-domain result matrix (paper 2)
- **URL:** https://zenodo.org/records/23028253 (`paper2_code.zip`; `PAPER2_UDA_RESULTS.md`,
  `VTUAD_THIRD_DOMAIN_RESULTS.md`, `train_uda.py`, `review4_experiments/DESIGN.md`).
- **Exact configs:** normalization for ALL UDA methods = **source-train mean/std**
  (standardization order: normalize with source stats, then align in feature space;
  target_oracle is the only exception, using target stats). Deep CORAL: ‖C_s−C_t‖²_F/4d²
  on 512-d penultimate features, weight 1.0, added to CE. MMD: multi-kernel RBF,
  bandwidths median-heuristic base = 1/(2·median(d²)), γ ∈ base·{2⁻²..2²} (5 kernels),
  weight 1.0. Shared training: 30 ep, lr 3e-4 AdamW, batch 64, SpecAugment, sqrt class
  weights (power 0.5), source-val early stop/selection only.
- **Numbers on the VTUAD domain (n=3, macro-F1):** oceanship→vtuad: source_only 0.4054,
  CORAL **0.4202**, MMD 0.3421, oracle 0.8237. qiandaoear22→vtuad: source_only 0.2741,
  **CORAL 0.4136**, MMD 0.3880. vtuad→oceanship: 0.4032 / CORAL 0.4586 / MMD 0.4685.
  vtuad→qiandaoear22: source_only 0.4000 / CORAL 0.3119 / **MMD 0.2103 (−0.190 negative
  transfer)**. So on the VTUAD domain CORAL is reliable, MMD is direction-dependent
  (best +0.236 on q2o where it reaches 83% of oracle F1; catastrophic −0.190 into
  qiandaoear22). Cross-corpus zero transfer with unmapped classes ≈ 0 (all 12 directions;
  same-water ONC→ONC′ also collapses ⇒ shift is label-provenance/sensor/scenario, not
  just water).
- **Fit (T5):** closed-form CORAL (whitening+recoloring) per test station on a robust band
  subset, source-pool statistics as the anchor, **keep identity transform as ensemble arm**
  (R9 F1 confirmed); direction: train→test-station only; never MMD. Also gives us the
  sqrt-class-weight + macro-metric checkpoint recipe for the presence head (R9 F14) now at
  code level (`--class-weight-power 0.5`). **Effort S/M** (closed-form CORAL is ~20 lines).

### C5 · CRITICAL — Knudsen/Wenz wind-fit: feasible on our columns, with two safeguards
- **Sources:** Wenz 1962 JASA 34:1936, 10.1121/1.1909155 (wind-dependent noise 50 Hz–20 kHz,
  composite spectrum); "Maximum likelihood separation of anthropogenic and wind-generated
  underwater noise", JASA 2022, **10.1121/10.0013887** (single hydrophone; wind = Gaussian
  with wind-speed-dependent mean, anthropogenic = time-invariant distribution; joint ML/EM
  estimate of both PSD distributions); Cauchy et al. 2019, IEEE TGRS **10.1109/TGRS.2018.2871422**
  (acoustical meteorology: wind speed from ambient noise, validated vs surface data);
  Ragland & Abadi 2025 (R9 F10, piecewise log-linear per band); Schoeman 2022 (r>0.7 at
  1–2.5 kHz in our exact region).
- **Feasibility on OUR table:** our 25 deci-decades span **31.6 Hz–7,943 Hz**
  (`tol_convert.py`: centres 10^(1.5+0.1k)). The clean wind-dominated Knudsen regime
  (~500 Hz–5 kHz, above most propeller/blade excess, below swell/thermal rolls) is fully
  covered by bands **k≈12–24 (≈500 Hz–7.9 kHz) = 13 columns**. Per window: robust fit of
  dB level vs log10(f) over those columns (Theil–Sen / median regression, masking bands
  whose excess over the station quiet bed exceeds threshold) → slope + intercept = per-
  window **wind index**; per station, learn the piecewise log-linear response of every
  band to the wind index (Ragland shape), subtract predicted wind level → **wind-detrended
  excess** = T2 on steroids. Two safeguards: (i) index, not absolute m/s — no co-located
  anemometer, so it anchors only to relative changes (exactly what detrending needs);
  (ii) vessel-heavy windows bias the fit → iterate: fit → excess gate → refit (EM-style,
  mirroring the 2022 ML-separation paper which is the principled version: per-station
  per-band mixture of a time-invariant anthropogenic distribution + wind Gaussian).
  This also revives the A69 negative result: the FA gate failed because the wind estimate
  was crude — a per-window continuous index is a different estimator, not the same gate.
- **Fit:** T2 upgrade (wind index + detrended bands as LGBM features + PCEN-style
  background tracker cross-check). **Effort M** (~half a day; no raw audio, pure 25-column
  arithmetic). Rank: highest value-per-effort of this round.

### C6 · CRITICAL — TTA for tabular: the literature is thin, and it agrees with stat-only
- **Sources:** "Fully Test-time Adaptation for Tabular Data" (FTAT), AAAI 2024,
  arXiv **2412.10871** (c18): label+covariate shift, **no effective augmentations, high
  adaptation sensitivity** → adaptation via normalization/statistics + robust objectives,
  explicitly not TENT-style entropy on tabular; "AdapTable", arXiv **2407.10784** (c8):
  shift-aware **uncertainty calibrator** + label-distribution handler, model-agnostic.
- **What it says:** TTA methods that rely on architecture hooks (BN affine, entropy) fail
  or are inapplicable on gradient-boosted trees; what transfers is (a) re-estimated
  normalization stats per batch/station, (b) prediction calibration under shift.
- **Fit (T5/T3):** exactly closes our question "does TTA work for tabular features?" —
  answer: stat-re-estimation + uncertainty calibration only; entropy-min impossible
  (no BN) and undesirable (collapses per C3). Our planned AdaBN+CORAL per test station IS
  the literature-recommended tabular TTA. **Effort S** (no new code; a citation + a guard).

---

## 2. CATFISH code-level details R9 didn't have (target #3)

### M7 · MEDIUM — Metadata-fusion architecture, exact fusion point & normalization
- **URL:** https://github.com/Jotels/CATFISH (tarball cached `data/zenodo_r10/CATFISH-main/`).
- **What it says (`classifier.py` + `classifier_config.yaml`):** aux features = **5 CTD
  scalars** — `t1_norm, c1_norm, p1_norm, sal_norm, sv_norm` (temperature, conductivity,
  pressure/depth, salinity, sound speed) — **pre-normalized upstream at metadata-build
  time** (the `_norm` columns are written by the dataset builder, not the network).
  Fusion: `Linear(5→128)+ReLU` → concatenated with the pooled 1280-d EfficientNet-B0
  vector (AdaptiveMaxPool2d(1)) → final `Linear(1280+128 → n_classes)`. I.e. fusion at the
  penultimate layer, tiny aux MLP, **max-pooling** (no attention) in the shipped config,
  label_smoothing 0.1, AdamW lr 3e-4 wd 0, batch 32, max_epochs 1000 with 6.5-day wall
  clock. Shipped config has `use_aux: False` (the +4.7 pp CTDSV ablation number comes from
  toggling it).
- **Fit (T1):** our T1 fingerprint conditioning already out-features this (we condition on
  station bed/tilt/shape; they only condition on CTD). Validation that "5 normalized
  scalars at the penultimate layer" is all CATFISH needed for +4.7 pp ⇒ our richer T1 has
  headroom. No build change; write-up ammo. **Effort S.**

### M8 · MEDIUM — LogTBN exact params: the "median filter" is a FULL-AXIS median, not rolling
- **URL:** same repo (`leaf/efficientleaf.py`).
- **What it says:** `LogTBN(a=5, trainable=True, per_band=True, median_filter=True,
  append_filtered=True)`: y = log(1 + 10^a_k·x) with per-band learnable a init 5; median
  computed **once per band over the whole time axis** (`x.median(-1)`) and the residual
  `x − m` appended as a second channel (per_channel BN, 2 channels); TBN = BatchNorm1d
  over (batch,bands) treating each time frame as a batch element, affine. **PCEN variant
  defaults: s=0.04, α=0.96, δ=2, r=0.5, eps=1e-12, clamp=1e-5, learn_logs=False**
  (`pcen_learn_logs: False` in config). EfficientLEAF: 80 Gabor filters, 60–7800 Hz
  @32 kHz, 25 ms window / 10 ms stride, 8 groups, stride_factor 16.
- **Fit (T6):** corrects our mental model from R9 F3 — the detrend basis is the **median
  over the full context** (for us: per-band median over the 15-minute window, or over a
  longer per-station history), NOT a running median; dual-channel = (level, level −
  median). Pin PCEN params exactly as above for the PCEN arm. **Effort S** (one-line
  change to the planned LogTBN implementation).

### M9 · MEDIUM — Δ-band diagnostic mapped to our deci-decades (no code in repo)
- **URL:** arXiv 2505.23964 (paper) — repo contains no analysis script; mapping done here.
- **What it says:** discriminative filter range contracts 0–60 → 0–10 (of 80 filters,
  60–7800 Hz, mel-spaced) from close to far range. Mel spacing ⇒ filters 0–10 ≈ 60–300 Hz
  ⇒ on our grid **bands k≈1–5 (≈40–200 Hz)** are the far-range survivors; wind-affected
  high bands are the first to lose signal.
- **Fit (T6/T3):** low-SNR band weighting (R9 F6) now has an explicit band range on OUR
  columns: weight excess in k≤5 at low estimated SNR, use k≥12 primarily for wind (C5).
  **Effort S.**

---

## 3. New sweep 2025–2026 (target #4)

### M10 · MEDIUM — Vessel-side log-linear source-spectrum regression (small vessels)
- **URL:** Shipton & Diamant, "Regularized log-linear models for predicting underwater
  radiated noise spectra of small vessels", Frontiers in Marine Science 2026,
  **10.3389/fmars.2026.1759355** (open access).
- **What it says:** regularized log-linear regression gives length- and speed-dependent
  source spectra 23–24,000 Hz for small motorized vessels — the missing model class for
  recreational/coastal craft, which dominate coastal noise.
- **Fit (T3/T6):** our mixture-factory vessel templates and the closed-form projection
  share `s = ⟨x−B, V−B⟩/‖V−B‖²` can use per-vessel-class band templates *regressed* from
  length/speed instead of empirically averaged — better low-SNR dictionaries, and the
  log-linear shape matches our band-level feature space directly. Factory-side only.
  **Effort M.**

### M11 · MEDIUM — AIS-gap handling: what the rebuild itself documents
- **URL:** https://zenodo.org/records/23037895 (`static_audit_README.md`,
  `static_field_fill_audit.csv`, `static_field_conflicts.csv`).
- **What it says:** AIS static fields have silent gap channels: AIS type 5 is *always*
  2-fragment and the primary parser decodes statelessly → **all Class A static fields
  lost**; a pyais `part_num` vs `partno` key mismatch silently dropped type 24 part B;
  rescue = fragment reassembly + first-non-null-wins; 15/178 hulls broadcast conflicting
  statics; raw NMEA survives for only 3 days so full re-audit is impossible. Position
  gaps are bridged by linear interpolation up to 20 min (C1) — i.e. **interpolated
  presence counts as presence** in the label predicate.
- **Fit (T4/T1):** two lessons — (i) vessel-class labels carry systematic error channels
  invisible without raw AIS; our label-free share regression + hull-disjoint validation is
  the robust side; (ii) any AIS-derived prior we might add (T4 self-training priors) must
  treat interpolated tracks as *uncertain* presence, not truth. **Effort S** (policy note).

### L12 · LOW — Pseudo-label regression under domain shift: no acoustic-specific find
- S2/arXiv sweeps return CV-centric self-training (cycle self-training, entropy-filtered
  rotation regression e.g. FisherMatch arXiv 2203.15765). Nothing beat the R9 recipe
  (confidence + diversity gates, mean-teacher). Keep R9 plan; cite FisherMatch-style
  uncertainty filtering if needed. **Effort 0.**

### L13 · LOW — Noise-floor tracking literature: canonical options unchanged
- Fitzgerald 2012 harmonic/percussive median filtering (librosa `decompose.hpss`) remains
  the standard spectral baseline-separation tool; the ML-separation paper (C5, 10.1121/10.0013887)
  is the modern distribution-based option; CATFISH full-axis median (M8) is the same
  family at zero cost. No new technique beyond what R9/C5 prescribe. **Effort 0.**

### L14 · LOW — Deposits located for later
- OSFUDA (paper 9): https://zenodo.org/records/23328407; SimCLR (paper 5):
  https://zenodo.org/records/23411528; frozen-FM (paper 8): https://zenodo.org/records/23345657
  (VTUAD embedding caches for BEATs/CLAP/AST/ HuBERT/wav2vec2/ PanNS included — if we ever
  run the T5 embedding probe, the caches save ~10 GPU·h of extraction). Cross-archive
  (paper 3): https://zenodo.org/records/23312809 (includes tuned VTUAD ResNet-18
  checkpoints + run_config.json). **Effort 0.**

### What NOT to adopt (new confirmations)
- **TENT / entropy-min TTA** — now n=5-quantified collapse (2/5 seeds to the exact
  majority point; affine-only 5/5) + tabular-FTTA literature says it doesn't transfer.
- **MMD alignment** — confirmed on-code: wins q2o (+0.236) but −0.190 INTO
  qiandaoear22 and −0.063 into VTUAD; direction-lottery. CORAL only.
- **Input-only re-normalization** (`inputnorm` ablation) — hurts (o2q F1 0.3393);
  re-standardize every block, not just inputs.
- **Absolute wind calibration** — no anemometer; wind index only (C5 safeguard i).

---

## 4. ADOPT — build-order delta (plan §7h; decisions belong to the main agent)

1. **C5 first (T2 upgrade, M):** per-window Knudsen/Wenz wind index — robust dB-vs-log10(f)
   fit on bands k≈12–24 with quiet-bed excess masking + one EM refit; per-station piecewise
   log-linear band responses; output = wind index feature + wind-detrended band excess
   block. Cross-check against existing T2 wind-shape (LGBM importance + group-split val).
2. **C3 (T5 lock, S):** tabular AdaBN = robust re-standardization of ALL feature blocks
   (raw + engineered) per test station from clean windows; never partial, never input-only.
3. **C4 (T5, S/M):** closed-form CORAL per test station on robust band subset, source-pool
   anchor, diagonal loading (shrinkage) on the whitening — their code has no closed-form
   variant, so this is our implementation guarded by their direction/stability evidence;
   identity transform stays an ensemble arm.
4. **M8 (T6, S):** LogTBN-style feature = (level, level − full-context median) dual channel;
   median over the 15-min window / per-station history, NOT rolling. PCEN arm params
   pinned s=0.04, α=0.96, δ=2, r=0.5 (eps 1e-12, clamp 1e-5).
5. **M9 (T3/T6, S):** low-SNR band weighting uses bands k≤5 for vessel excess, bands k≥12
   reserved for wind (C5) — encode as the SNR-gated weight vector.
6. **C6 (T5/T3 guard, S):** no entropy-min TTA anywhere; per-window uncertainty calibration
   (R9 F11/F12) is the sanctioned TTA surface for tabular.
7. **C2/M11 (T4 data rules, S):** if VTUAD strict WAVs are fetched for self-training, use
   strict-interval cuts (167 wraparound + 17 multi-source extensions excluded), hull-disjoint
   splits (paper2 E2 infrastructure exists as a template), and treat AIS-interpolated
   presence as uncertain (interpolation ≤20 min bridges gaps by design).
8. **M10 (T3 factory, M, opportunistic):** vessel-template dictionary via regularized
   log-linear length/speed→spectrum models for the projection-share feature.
9. **C1 (no build; validation anchor):** majority-class 0.3851 + per-class F1 table +
   background→tug confusion = the documented weakness of the classifier-first VTUAD
   family; use in the write-up and as a sanity ceiling for any rival-behavior modeling.

Everything above is band-power-level or post-hoc tabular; nothing requires raw audio at
inference. Total new effort ≈ 1.5–2 days, dominated by C5.
