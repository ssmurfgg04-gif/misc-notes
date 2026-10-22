# R10-A intel report — OSS tools survey for the UVNC pipeline

**Agent:** general-purpose (R10-A). **Date:** 2026-10-22.
**Scope:** open-source, Python, pip-installable, CPU-only, license-permissive tools that can concretely improve the Zindi UVNC pipeline (band-power features → LGBM two-head + E5 bump → power-map calibration → shrinkage hedge). Deliberately **no re-treading of R9 findings** (CORAL/AdaBN/PCEN/LogTBN *techniques* are assumed; this report covers *which packages deliver them*).

**Method + probe count:** ~**154** web probes (PyPI JSON API ×~65 for version/license/deps; GitHub repo pages via HTML ×~22 for licenses (core API rate-limited 403, as in R9); readthedocs/project docs ×~35; raw.githubusercontent source checks ×~12; Crossref ×3; Semantic Scholar ×3 (1 OK, then HTTP 429); misc HEAD checks ×~14). ~22 probes returned 404/429/403 and are logged as negatives below. **No heavy installs were performed** (no torch/TF); verification = PyPI metadata + docs + source reads. Local venv probed too (Python 3.12.15, x86_64): already installed — lightgbm 4.5.0, catboost 1.2.8, xgboost 2.1.3, librosa 0.10.2.post1, statsmodels 0.14.5, scipy 1.14.1, pandas 2.2.3, numpy 2.1.3, numba 0.61.0, joblib 1.5.3, sklearn 1.5.2.

**Every version below = PyPI latest verified 2026-10-22 via `pypi.org/pypi/<name>/json`. Licenses verified via PyPI classifiers + repo pages.**

---

## 0. TL;DR — five findings that change tonight's build plan

1. **CORAL does not need to be hand-rolled OR pulled from a torch repo**: `skada` 0.6.0 (BSD-3, base deps numpy/scipy/sklearn/POT/pandas — **no torch**) ships `CORALAdapter` with `reg="auto"` = **Ledoit–Wolf covariance shrinkage**, which directly answers R9-F1's caveat that raw CORAL amplifies noisy bands. https://github.com/scikit-adaptation/skada, source: https://github.com/scikit-adaptation/skada/blob/main/skada/_mapping.py
2. **MAPIE 1.6 does NOT implement weighted conformal prediction under covariate shift** (R9-F12 assumption wrong). Full docs sitemap has zero `covariate|weight` pages; sections = calibration / classification / conditional_cp / exchangeability_testing / regression / risk_control (https://mapie.readthedocs.io/en/latest/sitemap.xml); regression API page has 0 "weight" hits. It *does* ship `SplitConformalRegressor`, `ConformalizedQuantileRegressor` (→ per-window intervals ⇒ k(window)), Mondrian `conditional_cp` (→ per-station-group calibration), and an **exchangeability-testing martingale monitor** (online shift alarm — a free unknown-unknown we hadn't planned). Weighted CP stays hand-rolled (~15 lines).
3. **Optuna's LightGBM pruning callback moved out of core**: `optuna.integration.lightgbm` is deprecated since optuna 4.9 (removal targeted 6.0) — shim at https://github.com/optuna/optuna/blob/master/optuna/integration/lightgbm.py. Must `pip install optuna-integration` (5.0.0, base dep = optuna only) and import from there; `LightGBMPruningCallback` export verified in https://github.com/optuna/optuna-integration/blob/main/optuna_integration/__init__.py. **Yes, it works out of the box with LightGBM callbacks + RMSE.**
4. **R9-F9 license correction:** `pypam` (lifewatch) is **GPL-3.0** (https://github.com/lifewatch/pypam) → do NOT vendor its code; implement SPD percentiles by hand (they are 5 lines of numpy). Its companion `pyhydrophone` 0.4.0 is MIT but **pins `scipy==1.13.1`** (PyPI requires_dist) → would downgrade our scipy 1.14.1; skip tonight.
5. **No native snapshot ensembling in any GBDT.** LightGBM's `snapshot_freq` is CLI-only **checkpointing** (https://lightgbm.readthedocs.io/en/latest/Parameters.html); CatBoost `save_snapshot` = crash recovery. Emulate snapshot ensembles with bagging_fraction/feature_fraction × seed bags via Optuna instead.

Also: `pycoral` (PyPI) = Google **Edge TPU** hardware API (https://github.com/google-coral/pycoral), NOT Sun–Saenko CORAL; `coral` (PyPI) = unrelated Klavins-lab repo (https://github.com/klavinslab/coral); `transf` and `duqgrep` **do not exist** on PyPI (404). `adapt` 0.4.5 has CORAL but hard-requires TensorFlow → skip.

---

## 1. Prioritized table (top = install and use tonight)

### CRITICAL (use tonight)

| # | Tool (verified ver) | What it does (1 line) | License | CPU-pip | Concrete use in OUR pipeline | Sources |
|---|---|---|---|---|---|---|
| C1 | **optuna 5.0.0 + optuna-integration 5.0.0** | HPO with TPE sampler + per-iteration pruning of LightGBM trials | MIT | ✅ light (alembic/sqlalchemy only; torch only in extras) | Replaces manual grid fiddling in `train_v3_v31`: tune num_leaves/min_child_in_leaf/feature_fraction/bagging/λ_l1λ_l2 per head with `TPESampler(multivariate=True, group=True, constant_liar=True)` + `SuccessiveHalvingPruner`; `LightGBMPruningCallback(trial, "rmse")` inside `lgb.train(callbacks=…)` with the val set | https://pypi.org/project/optuna/, https://pypi.org/project/optuna-integration/, https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html (multivariate/group/constant_liar params verified), https://github.com/optuna/optuna-integration/blob/main/optuna_integration/__init__.py |
| C2 | **skada 0.6.0** | sklearn-style closed-form CORAL domain alignment (`CORALAdapter`, `reg="auto"` = Ledoit–Wolf shrinkage) | BSD-3 | ✅ light (numpy/scipy/sklearn≥1.5/POT/pandas≥2.3 — **will bump pandas 2.2.3→2.3.x**) | R9-F1 tonight: align train-pool feature covariance to each test station before LGBM; per-station transform, no labels; keep identity arm as ensemble member; validate direction on bg-group split. Hand-rolled 20-line fallback identical to Sun–Saenko 2016 if we refuse the pandas bump | https://github.com/scikit-adaptation/skada (BSD-3), https://github.com/scikit-adaptation/skada/blob/main/skada/_mapping.py (CORALAdapter + reg="auto" docstring), https://arxiv.org/abs/1511.05547, https://github.com/jindongwang/transferlearning (MIT reference impls) |
| C3 | **scikit-maad 1.5.2** | 40+ ecoacoustic "alpha indices" (ACI, ADI, AEI, BI, NDSI=`soundscape_index`, temporal/spectral entropy, roughness, AGI, tfsd…) on any spectrogram-like matrix | BSD-3 | ✅ light (numpy/scipy/skimage/pandas/matplotlib/pywavelets) | New feature block for the LGBM: run `all_temporal_alpha_indices` / `all_spectral_alpha_indices` on the station-relative (bed-normalized) 25-band × 15-position matrix; literature ties NDSI/ACI-family to boat-noise dominance (see §3). MUST be computed station-relative or they encode station identity (R9-F15 warning) | https://pypi.org/project/scikit-maad/, https://scikit-maad.github.io/features.html, function list verified in https://github.com/scikit-maad/scikit-maad/blob/production/maad/features/__init__.py |
| C4 | **MAPIE 1.6.0** | Conformal prediction for regression: `SplitConformalRegressor`, `ConformalizedQuantileRegressor` (intervals from quantile heads), Mondrian conditional CP, exchangeability martingale tests | BSD-3 | ✅ light (numpy≥1.24/scipy≥1.10/sklearn≥1.4) | R9-F11: CQR-style per-window intervals on the share head → `k(window) = width/μ` adaptive shrinkage replacing the single global k; Mondrian per-group calibration for G0/G1/G2; martingale monitor as a free shift alarm. **No covariate-shift weighting in 1.6** — density-ratio weighted quantiles stay hand-rolled | https://pypi.org/project/MAPIE/, https://mapie.readthedocs.io/en/latest/api/regression/ (classes verified), https://mapie.readthedocs.io/en/latest/sitemap.xml (no covariate/weight pages), https://github.com/scikit-learn-contrib/MAPIE (BSD-3) |
| C5 | **librosa (already installed 0.10.2.post1; PyPI latest 1.0.0)** | PCEN (`librosa.pcen`) — per-channel EMA automatic-gain-control + compression on ANY array along a time axis; audio I/O | ISC (1.0.0; MIT for 0.10.x) | ✅ **zero-install (already in venv)** | R9-F4 tonight: `librosa.pcen` on the 25-band × 15-window power matrix (axis=-1), two time-constants = two background trackers; the CPU reference implementation for band-power series (see §2) | https://librosa.org/doc/0.10.2/generated/librosa.pcen.html (params gain/bias/power/time_constant/max_size), `def pcen` verified in https://github.com/librosa/librosa/blob/main/librosa/core/spectrum.py, https://pypi.org/project/librosa/ |

### MEDIUM (use if time — all verified installable, CPU, permissive)

| Tool (ver) | What it does | License | CPU-pip | Concrete use in OUR pipeline | Sources |
|---|---|---|---|---|---|
| statsmodels 0.14.5 (**installed**) | Robust M-estimators (Huber/Tukey `RLM`) | BSD-3 | ✅ zero-install | E5 upgrade: replace per-band P20 bed with per-band RLM/Huber center over the minute series → robust quiet-bed immune to 15-window vessel contamination | https://www.statsmodels.org/stable/generated/statsmodels.robust.robust_linear_model.RLM.html |
| antropy 0.2.3 | 12+ complexity features per series: permutation/spectral/sample/SVD entropy, higuchi/katz/petrosian FD, DFA | BSD-3 | ✅ light (numpy/scipy/sklearn/numba — bumps numba 0.61.0→≥0.61.2) | Per-band excess-envelope complexity features for LGBM (vessel bands are structured, wind is noise-like) | https://pypi.org/project/antropy/, https://raphaelvallat.com/antropy/, https://github.com/raphaelvallat/antropy (BSD-3) |
| bottleneck 1.6.0 | C-speed moving window functions (`move_median`, `move_mean`) | BSD (Simplified) | ✅ tiny wheel | LogTBN dual-channel (R9-F3) at full 1.7M-row scale: `bn.move_median(band_series, window=…)` = the running-median detrend channel | https://github.com/pydata/bottleneck, https://pypi.org/project/bottleneck/ |
| stumpy 1.14.1 | Matrix-profile motif/discord discovery on any 1-D series (numba CPU) | BSD-3 | ✅ light (numpy/scipy/numba≥0.61.2) | Motif detection on per-band minute series per station: recurring vessel-pass signatures → "distance to nearest past pass motif" feature + planted-passage boundary sanity check | https://stumpy.readthedocs.io/en/latest/, https://github.com/stumpy-dev/stumpy (BSD-3), https://pypi.org/project/stumpy/ |
| ruptures 1.1.10 | Offline change-point detection (PELT/Binseg, many costs) | BSD-2 | ✅ light | Per-band change-point stats on the 15-position trajectory (R9-F20) — passage-boundary features for the bump reader | https://github.com/deepcharles/ruptures (BSD-2), https://pypi.org/project/ruptures/ |
| catboost 1.2.8 (**installed**; latest 1.2.10) | Ordered boosting GBDT | Apache-2.0 | ✅ zero-install | Hedge head: CatBoost two-head on same features as diversity member of the blend; `has_time` off; note CatBoost snapshots = checkpointing only | https://pypi.org/project/catboost/, https://catboost.ai/docs/en/concepts/algorithm-main-stages |
| xgboost 2.1.3 (**installed**; latest 3.4.1) | GBDT with hist trees | Apache-2.0 | ⚠️ stay on 2.x: 3.x adds `nvidia-nccl-cu13` as a hard Linux dep (verified in PyPI requires_dist) | Third hedge arm only if time; `tree_method="hist"` | https://pypi.org/project/xgboost/, https://xgboost.readthedocs.io/en/stable/ |
| LightGBM 4.7.0 (installed 4.5.0) | Our main GBDT | MIT | ✅ | Minor-version bump optional; no snapshot ensembling (see §2.4); `snapshot_freq` = CLI checkpointing | https://lightgbm.readthedocs.io/en/latest/Parameters.html, https://github.com/lightgbm-org/LightGBM |
| crepes 0.9.1 | Conformal regressors/classifiers w/ difficulty-normalized scores + Mondrian + `crepes.wrap` for sklearn-compatible models | BSD-3 | ✅ light (numpy/pandas/scipy) | Alternative to MAPIE for difficulty-normalized intervals wrapping LGBM; **no covariate-shift weighting** (0 "weight" hits in API docs) | https://pypi.org/project/crepes/, https://crepes.readthedocs.io/en/latest/crepes.html, https://github.com/henrikbostrom/crepes (BSD-3) |
| quantile-forest 1.4.2 | RF with exact quantile prediction | Apache-2.0 | ✅ light | Optional quantile cross-check for k(window) if CQR intervals look miscalibrated | https://zillow.github.io/quantile-forest, https://github.com/zillow/quantile-forest (Apache-2.0) |
| polars 2.0.0 / duckdb 2.0.0 / pyarrow 26.0.0 | Fast dataframe / in-SQL analytics / columnar CSV engine | MIT / MIT / Apache-2.0 | ✅ | Feature-builder I/O speed on the 10-site 1.7M-row band tables (lazy group-bys, `pyarrow` CSV engine for pandas) | https://pypi.org/project/polars/, https://pypi.org/project/duckdb/, https://pypi.org/project/pyarrow/, https://docs.pola.rs/, https://duckdb.org/docs/stable/ |
| audiomentations 0.43.1 | Waveform augmentation (pitch/time/poise/noise) for the mixture factory | MIT | ✅ light (numpy/librosa/scipy/soxr) | ONLY if we process VTUAD strict WAVs (T4): augment vessel clips before the band-power transform | https://pypi.org/project/audiomentations/, https://iver56.github.io/audiomentations/, https://github.com/iver56/audiomentations (MIT) |
| properscoring 0.1 | CRPS and related proper scoring rules | Apache-2.0 | ✅ (stale 2016 but tiny) | Score hedged submissions with CRPS on val (RMSE stays the ranking metric) | https://github.com/TheClimateCorporation/properscoring |
| joblib 1.5.3 (**installed**), psutil 7.2.2, filelock 4.2.4 | Parallelism / mem guard / lock files | BSD-3 / BSD-3 / MIT | ✅ | Parallel per-station feature builds; RAM guard on the 3–16 GB box; filelock around backup scripts | https://github.com/joblib/joblib, https://github.com/giampaolo/psutil, https://github.com/tox-dev/py-filelock |
| scipy.signal 1.14.1 (**installed**) | Welch/spectrogram/CWT | BSD-3 | ✅ zero-install | Welch smoothing of per-band minute trajectories before entropy features; cite as the band-power reference | https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html |

### SKIP (checked, with reason)

| Tool | Reason (verified) | Source |
|---|---|---|
| opensoundscape 0.13.2 (MIT) | requires torch + tensorflow + torchaudio (PyPI requires_dist) — heavy-deps rule | https://pypi.org/project/opensoundscape/ |
| ketos 2.7.1 | **GPL-3.0** license (violates permissive rule); also py≤3.11 | https://pypi.org/project/ketos/ |
| torchaudio / LEAF-family frontends | torch-bound | (per our no-torch constraint; LEAF context in R9 doc §F4) |
| tabpfn 9.2.0 | torch≥2.5 hard dep; TabPFN-3-Fast limited to **5000 samples** (older 1000) vs our 6–15k pools; **model weights non-commercial** (code Apache-2.0) | https://pypi.org/project/tabpfn/ (README License + size text verified) |
| pytabkit 1.7.3 (Apache-2.0) | torch + pytorch-lightning hard deps | https://pypi.org/project/pytabkit/, https://github.com/dholzmueller/pytabkit |
| adapt 0.4.5 (BSD-2) | CORAL inside, but hard-requires TensorFlow + cvxopt + scikeras | https://pypi.org/project/adapt/, https://github.com/adapt-python/adapt |
| ncalib 0.1.2 (MIT) | torch + jaxtyping deps; niche calibration lib | https://pypi.org/project/ncalib/ |
| noisereduce 3.0.3 (MIT) | operates on **waveforms/STFT**, not band-power matrices — E5 bed-subtraction is already the band-domain equivalent | https://github.com/timsainb/noisereduce |
| scaper 1.6.5 (BSD-3) | audio-file event mixing; needs sox/soxbindings/jams; our factory mixes in power domain | https://github.com/justinsalamon/scaper, https://pypi.org/project/scaper/ |
| tsfresh 0.21.2 (MIT) / tsfel 0.2.0 (BSD) | heavy compute, ~overlaps antropy+maad+scipy for our 750-value matrices | https://github.com/blue-yonder/tsfresh, https://github.com/fraunhoferportugal/tsfel |
| pyhht 0.1.0 | stale (last release years old); EMD not needed | https://pypi.org/project/pyhht/ |
| EMD-signal/PyEMD 1.10.0 (Apache-2.0) | works but low marginal value vs RLM detrend | https://pypi.org/project/EMD-signal/ |
| pypam | **GPL-3.0** — R9-F9 correction: re-implement SPD percentiles by hand | https://github.com/lifewatch/pypam |
| pyhydrophone 0.4.0 (MIT) | pins `scipy==1.13.1` → would downgrade our scipy; revisit with `--no-deps` if icListen calibration ever needed | https://pypi.org/project/pyhydrophone/ |
| BirdNET-Analyzer (code MIT) / birdnetlib 0.18.1 | birds ≠ underwater vessel acoustics; nuisance-mask idea moot (wind is our nuisance, not bio noise); model weights carry separate NC terms | https://github.com/kahst/BirdNET-Analyzer, https://pypi.org/project/birdnetlib/ |
| PAMGuard | Java, GPL, no pip | https://www.pamguard.org/ |
| pycoral 0.2.0 (Apache-2.0) | **name collision**: Google Edge TPU accelerator API, needs Coral hardware — not domain adaptation | https://github.com/google-coral/pycoral |
| coral 0.5.0 (klavinslab) | unrelated research code, not CORAL alignment | https://github.com/klavinslab/coral |
| transf | **does not exist on PyPI** (404) | https://pypi.org/pypi/transf/json |
| duqgrep | **does not exist on PyPI** (404) | https://pypi.org/pypi/duqgrep/json |
| dabest 2025.10.20 (Apache-2.0) | estimation-statistics plots, not domain adaptation (usable for val-delta reporting = cosmetic) | https://github.com/acclab/DABEST-python |
| ONC api-python-client / oncdw | already logged R9-F23; no inference value tonight | https://github.com/OceanNetworksCanada |

---

## 2. Answers to the specific survey questions

### 2.1 PCEN outside librosa; stateful vs stateless; on band-power series
- **librosa.pcen is the CPU-pip reference.** Verified present in 0.10.2 docs (params: `gain=0.98, bias=2, power=2, time_constant=0.400, eps, b, axis, max_size`) https://librosa.org/doc/0.10.2/generated/librosa.pcen.html and in current main source (`def pcen` in librosa/core/spectrum.py) https://github.com/librosa/librosa/blob/main/librosa/core/spectrum.py. Every other pip-installable PCEN we could find is deep-learning-framework-bound (LEAF-family, used by CATFISH in torch; see R9 doc §F4).
- **Stateful vs stateless:** `librosa.pcen` computes the per-channel EMA **within the passed array** and returns no state (stateless-per-call). The original PCEN is a per-channel IIR tracker (Wang et al. 2017); the exact stateful/streaming variant is a 3-line numpy EMA (`zi = (1-b)*zi + b*x`) or `scipy.signal.lfilter([b],[1, b-1],x,axis=-1)`.
- **Best for band-power series:** librosa.pcen on the 25-band × 15-window matrix with `axis=-1` and `b` set **in window units** (`b = 1 − exp(−Δt/tc)`), bypassing sr/hop defaults. Multi-scale = two calls with different `tc` (≈5 and ≈30 window-equivalents) → two background trackers per band. Stateless-over-the-full-station-series is correct for us because the whole test context is available at inference.

### 2.2 CORAL: reference implementations
- Hand-rolled 20 lines is mathematically complete: Sun & Saenko, "Return of Frustratingly Easy Domain Adaptation", AAAI 2016, https://arxiv.org/abs/1511.05547 (C = C_s^(−1/2)·C_t·C_s^(−1/2), align mean+re-color).
- MIT-licensed reference code: https://github.com/jindongwang/transferlearning (deep+traditional CORAL).
- **Best maintained CPU package: `skada` 0.6.0** (`CORALAdapter`, `reg="auto"` = Ledoit–Wolf shrinkage — handles ill-conditioned covariance on 25-band features), BSD-3, https://github.com/scikit-adaptation/skada/blob/main/skada/_mapping.py. `adapt` also has CORAL but requires TensorFlow.

### 2.3 Optuna RMSE pruner × LightGBM callbacks
**Yes, out of the box** — via `optuna-integration` (5.0.0; base dep = optuna only): `from optuna_integration.lightgbm import LightGBMPruningCallback`; export verified in https://github.com/optuna/optuna-integration/blob/main/optuna_integration/__init__.py (`"lightgbm": ["LightGBMPruningCallback", "LightGBMTuner", "LightGBMTunerCV"]`). Core `optuna.integration.lightgbm` is a deprecation shim (since 4.9, removal 6.0) https://github.com/optuna/optuna/blob/master/optuna/integration/lightgbm.py. Pattern: `lgb.train(params, dtrain, evals=[(dval,"valid")], callbacks=[LightGBMPruningCallback(trial, "rmse"), lgb.log_evaluation(0)])` with `SuccessiveHalvingPruner`/`MedianPruner`. `TPESampler(multivariate=True, group=True, constant_liar=True)` verified in https://optuna.readthedocs.io/en/stable/reference/samplers/generated/optuna.samplers.TPESampler.html.

### 2.4 Snapshot ensembling in GBDT
**None of LightGBM/CatBoost/XGBoost ships snapshot ensembling.** LightGBM `snapshot_freq` is CLI-only model-file checkpointing ("frequency of saving model file snapshot", usable only in CLI version) https://lightgbm.readthedocs.io/en/latest/Parameters.html. CatBoost snapshots = crash-recovery checkpoints https://catboost.ai/docs/en/concepts/algorithm-main-stages. Do it manually: Optuna seed/feature_fraction bags (cheap diversity) or cyclic-refit at different subsamples.

### 2.5 Weighted conformal under covariate shift (tooling)
- MAPIE 1.6: **no** covariate-shift weighting (sitemap + API grep, §0.2). Has Split/CQR/Mondrian + martingale tests.
- crepes 0.9.1: difficulty-normalized + Mondrian only (0 "weight" hits in https://crepes.readthedocs.io/en/latest/crepes.html).
- ⇒ Keep R9-F12 as a **hand-rolled weighted-quantile block** (density ratio from a small domain classifier or 2–4 robust dims → weighted np.quantile). MAPIE's CQR covers the per-window-interval half.

### 2.6 noisereduce on band-power series
No — it consumes waveforms and computes its own STFT (https://github.com/timsainb/noisereduce); feeding it a 25-band × 15-min matrix would re-STFT the series as if it were audio. E5 quiet-bed subtraction + PCEN are the correct band-domain equivalents.

---

## 3. Unknown unknowns

### 3.1 Acoustic indices vs vessel share (scikit-maad shortlist)
maad.features verified function list includes: `acoustic_complexity_index`, `soundscape_index` (NDSI), `bioacoustics_index`, `acoustic_diversity_index`, `acoustic_eveness_index`, `temporal_entropy`, `spectral_entropy`, `roughness`, `surface_roughness`, `tfsd`, `acoustic_gradient_index`, `frequency_raoq`, plus `all_temporal_alpha_indices`/`all_spectral_alpha_indices` wrappers — https://github.com/scikit-maad/scikit-maad/blob/production/maad/features/__init__.py.
Literature linking the index family to boat-noise dominance (Crossref-verified DOIs):
- "Boat noise in an estuarine soundscape…" Marine Pollution Bulletin 2018, 10.1016/j.marpolbul.2018.05.016
- "Fish sounds and boat noise are prominent soundscape contributors in an urban European estuary", MPB 2021, 10.1016/j.marpolbul.2021.112845
- "A Fish and Dolphin Biophony in the Boat Noise-Dominated Soundscape of the Cres-Lošinj Archipelago", JMSE 2022, 10.3390/jmse10020300
**Our 5 to test tonight (station-relative, on the 15×25 matrix):** (1) NDSI (`soundscape_index`) low-vs-high band balance; (2) ACI (`acoustic_complexity_index`) temporal variability — vessels modulate, wind is flat (same logic as R9-F7 MFAV); (3) `spectral_entropy` (flat/complex spectrum ⇒ wind); (4) ADI (`acoustic_diversity_index`) — broadband vessel noise compresses band diversity; (5) `roughness`/`surface_roughness` (band-roughness ≈ engine tonals). Validate by LGBM gain + permutation on the bg-group split; drop any that merely re-encode station identity (R9-F15).

### 3.2 MAPIE exchangeability testing (martingales) — unplanned freebie
`exchangeability_testing` section ships online martingale tests for deployed regression models (https://mapie.readthedocs.io/en/latest/sitemap.xml) → use as a per-test-station drift alarm feeding the shrinkage strength, with zero model changes.

### 3.3 Library-risk gotchas found while verifying
- optuna-integration deprecation shim (§0.3) — pin `optuna==5.0.0 optuna-integration==5.0.0`.
- xgboost 3.x pulls `nvidia-nccl-cu13` on Linux (PyPI requires_dist) — stay on 2.1.3.
- skada needs pandas≥2.3 (bump from 2.2.3); stumpy/antropy need numba≥0.61.2 (bump from 0.61.0) — accept, or hand-roll CORAL and skip stumpy.
- pyhydrophone pins scipy==1.13.1 — skip.
- Semantic Scholar API rate-limits aggressively (429 after 1 query) — prefer Crossref for quick lit checks.

---

## 4. ADOPT TONIGHT — top 5

```bash
# 1. HPO + per-iteration pruning for the two LGBM heads (MIT)
pip install optuna==5.0.0 optuna-integration==5.0.0

# 2. Closed-form CORAL station alignment, Ledoit-Wolf-shrunk (BSD-3; bumps pandas>=2.3)
pip install skada==0.6.0

# 3. 40+ acoustic indices on the 25x15 matrix (BSD-3)
pip install scikit-maad==1.5.2

# 4. Conformal intervals -> per-window shrinkage k(window); Mondrian per-group; martingale alarm (BSD-3)
pip install MAPIE==1.6.0

# 5. Entropy/FD features + C-speed running median for LogTBN dual channel (BSD-3)
pip install antropy==0.2.3 bottleneck==1.6.0
```
Zero-install bonuses already in the venv, use tonight too: `librosa.pcen` (R9-F4), `statsmodels.RLM` (robust E5 bed), `catboost` (hedge head).

**3-line usage sketches**

1. Optuna × LightGBM pruning:
```python
import optuna, lightgbm as lgb
from optuna_integration.lightgbm import LightGBMPruningCallback
study = optuna.create_study(direction="minimize", pruner=optuna.pruners.SuccessiveHalvingPruner(min_resource=200, reduction_factor=3),
                            sampler=optuna.samplers.TPESampler(multivariate=True, group=True, constant_liar=True, seed=42))
lgb.train(params, dtrain, num_boost_round=3000, valid_sets=[dval],   # dval = bg-group-split val
          callbacks=[LightGBMPruningCallback(trial, "rmse"), lgb.log_evaluation(0)])
```
2. CORAL alignment (skada arm + hand-rolled identity-check arm):
```python
from skada import CORALAdapter                      # reg="auto" -> Ledoit-Wolf covariance shrinkage
Xtr2t = CORALAdapter().fit_transform(X_train, y, X_test_station)   # align train -> test station (verify exact call vs docs)
# fallback/arm-2 (identical math, Sun-Saenko 2016): C = invsqrt(Cov_tr) @ Cov_te @ invsqrt(Cov_tr); X' = (X-mu_tr) @ sqrtm(C) + mu_te
```
3. scikit-maad alpha indices (station-relative!):
```python
import maad.features as mf
Sxx = 10**(band_power_dB/10)                        # 25 bands x 15 positions, bed-normalized per station
alpha = {**mf.all_temporal_alpha_indices(Sxx, tn, fn), **mf.all_spectral_alpha_indices(Sxx, tn, fn)}
keep = [k for k in ("NDSI","ACI","Hf","ADI","roughness") if permutation_check(alpha[k], val)]  # drop station-ID leakers
```
4. MAPIE per-window shrinkage:
```python
from mapie.regression import ConformalizedQuantileRegressor      # intervals from LGBM quantile heads
mapie = ConformalizedQuantileRegressor(estimator=lgb_quantile_model).conformalize(X_cal, y_cal)
lo, hi = mapie.predict_interval(X_test, confidence=0.9)
k_window = (hi - lo) / mu_station                    # adaptive shrinkage: p = mu + k_window*(p_hat - mu)
```
5. LogTBN dual channel + entropy features:
```python
import bottleneck as bn, antropy as ant
med = bn.move_median(band_power, window=7, axis=-1, min_count=1)   # slowly-varying bed per band
dual = np.concatenate([log1p(band_power), log1p(band_power - med)], axis=1)   # CATFISH-style raw + median-detrended
h = [ant.perm_entropy(e, normalize=True) for e in excess_bands]    # complexity per band for the LGBM
```

**Execution note:** dev sandbox shows ~3 GB RAM visible (mission runner spec: 4c/16 GB); none of tonight's picks needs more — all are wheels ≤ a few MB except pyarrow (~36 MB) if added later.
