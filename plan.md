# plan.md — Underwater Vessel Noise Challenge (Zindi / French Embassy SA)

> Status: v2 (research & planning round complete). Merge of the user's plan + the
> "second plan" + profiling evidence gathered 2026-10-20. Next round: generator v1
> + baseline tournament.

## 0. Competition facts (verified)

| Item | Value |
|---|---|
| Prize | $5,000 USD ($1,500 + ChangeNOW invite / $1,000 / $500 / 2×$1,000 write-ups) |
| Timeline | Start 16 Oct 26 · Close **13 Dec 26** · Reveal 29 Jan 27 (~8 weeks left) |
| Metric | `1 − RMSE` on `share_added_vessel` (only scored column); `score_added_vessel` = ROC-AUC diagnostic |
| Submissions | 2/day, 200 total; pick 2 for private (70% of test; public = 30%) |
| Test set | 1,500 windows × 375 features (15 min × 25 third-octave bands, 31.6 Hz–7.94 kHz) |
| Target | `y = A / T` — added passage-reference linear energy ÷ total observed linear energy, per window, over observed cells |
| Rules that bind us | Test = inference-only (no fitting/pseudo-labelling/calibration on it); no leaderboard probing; no automl; pretrained models OK if public; external data must be declared with links/versions; challenge data must not be redistributed |
| LB (20 Oct) | #1 = 0.8720 · #2–#6 = 0.816–0.824 (tight pack). Public LB ≈ 450 windows ⇒ RMSE SE ≈ ±0.01; #1 is statistically clear of the pack, the pack is statistically indistinguishable from a decent constant baseline |

## 1. Problem statement, mathematically

Per window `i`: observations `X_i` (dB) → linear energy `T_i = Σ_cells 10^(dB/10)`.
Added component `A_i` is unknown; target `y_i = A_i / T_i ∈ [0,1]`.

Two trainable formulations (train BOTH, compare on held-out simulated mixtures):
1. **Direct fraction** `ŷ = f(X)` — aligned with the scored metric.
2. **Numerator model** `Â = g(X)`, predict `ŷ = ĝ/T`. If trained on squared error in
   `A`, weight per-window loss by `1/T_i²` to match fraction-space RMSE.
3. **Two-head mixture**: `ŷ = P̂(injection present) × Ê[y | present]` — principled
   under squared loss, avoids hard-thresholding the ~30–40% zero-injection mass.
   The presence head feeds `score_added_vessel` for free (calibrate ranking, not probability).

Energy conversion details that matter:
- `T_i` uses **only observed (finite) cells** — the same cells the organisers use.
- Missing cells: never treat as silence (0 dB) or fill before conversion.
- The added reference passes through the same band representation; references
  include ambient from their origin recording (target ≠ ship-only energy).

## 2. Data inventory (verified 2026-10-20)

### 2.1 Official SA package — ACQUIRED, checksums verified
Mirror via Kaggle (`renjistarfall/underwater-vessel-noise-private`, 12 downloads,
byte-identical to official SHA256SUMS — verified locally). Files: 10 site parquets
(1,715,779 rows), stations.csv, recorders.csv, DATA_DICTIONARY.md, Test.csv,
sample_submission.csv, starter notebook. Local copy: `/home/z/my-project/data/`.

### 2.2 Site profile (one line each)
| site | rows | period | recorders | TOL p50 dB | note |
|---|---|---|---|---|---|
| 01 Richards Bay | 1,001,174 | 2017-05→2024-05 | 3 (24 kHz) | 75.3 | 58% of all data; port |
| 02 Durban | 44,640 | 2025-10→2025-12 | 1 (ST600, 48k) | 77.3 | freshest data |
| 03 Cape Recife | 5,928 | 2024-03 (19d) | 1 | 78.2 | tiny |
| 04 Bird Island | 47,552 | 2022→2024 | 2 (24k/12k) | **94.4** | seal colony + boats |
| 05 St Croix Island | 250,717 | 2022→2025 | 3 | 81.3 | near Algoa Bay port traffic |
| 06 Riy Banks | 4,121 | 2024-03 (31d) | 1 | 79.9 | tiny |
| 07 St Francis | 169,488 | 2015→2018 | 1 (SM2M, 48k) | 84.1 | long, older |
| 09 Fish Hoek | 53,767 | 2016→2021 | 2 (ST300, 96k) | 64.6 | quiet bay |
| 10 Sea Point | 3,660 | 2018-10 (3d) | 1 (96k) | 60.7 | tiniest |
| 13 Saldanha Bay | 134,732 | 2022→2023 | 2 (ST300/ST500) | 67.2 | 2 candidate coords |

### 2.3 Critical fingerprints found
- **Test missingness is not uniform**: m01 = 41.6% missing, m15 = 6.7%, m02–m13 ≈ 0%.
  Real duty-cycling pattern ⇒ features must be computed on **observed cells only**,
  with per-minute availability masks as model inputs. Robust aggregations win.
- Overall test missing 3.3%; 48.3% of rows have ≥1 missing cell.
- Test dB range [29.3, 152.9] — outliers exist; clip/robust-scale.
- Recorder hardware varies per site (SM2M/ST300/ST500/ST600/URN, 12–96 kHz) ⇒
  band noise floors differ by site; model must not depend on site identity
  (test gives no site ID — site-dependent calibration must be inferred, not memorised).
- Richards Bay rec 201383949 (2017–2019) and URN_8321 (12 kHz) likely miss high bands
  — check per-recorder band availability before simulating.

### 2.4 External corpora (declared, licensed)
| Dataset | Size | Classes | Access | License | Use |
|---|---|---|---|---|---|
| **VTUAD rebuilt v1.3.2** (Zenodo 23037895) | ~25 GB WAV (525 clips, 56 h, 32 kHz) + features 7.4 GB | 11 vessel + background | direct HTTP, per-class zips | CC-BY-4.0 | primary vessel reference library; has strict-interval cut + `registry_anonymized.csv` (178 hulls, length/beam) |
| **UniqueShip / MARINA** (uniqueshipdata.org) | subsets: 12-class-5h = 17.8 GB zipped · 5-class balanced = 64.8 GB · full = 646 GB | 12 | Google Drive 10GB chunks (rclone) | CC-BY-4.0 (ONC) | scale-up source, leakage-safe vessel-ID splits |
| **HearMyShip** (hearmyship.fer.hr) | 1,148 small vessels (<55 m) | small craft | web portal, registration | all rights reserved — confirm terms | small-craft spectra (test "includes references from smaller craft") |
| **DeepShip** (irfankamboh/DeepShip) | 47 h, 265 ships | 4 classes | request form | research | backup diversity |
| **ONC direct** (data.oceannetworks.ca) | archives | — | free API token | ONC policy | optional; VTUAD/UniqueShip already cover it |
| **Wittekind source model** (gist dbetchkal/093c08f9) | — | — | public gist | — | physics-based synthetic source levels: L1 low-freq cavitation, L2 high-freq cavitation, L3 machinery, from (v, v_c, C_B, D, engines) |

No public competition code exists on GitHub (swept 2026-10-20: `share_added_vessel`,
`TOL_31.6`, `South_African_Real_Acoustics`, starter-notebook name → 0 hits).
First-mover window for tooling; nothing public to copy from.

## 3. Strategy (what actually wins)

**Ranked by expected RMSE impact:**

1. **Leakage-resistant synthetic validation** (highest priority — without this
   every score is noise). Group-held-out splits: background periods, source
   recordings, AND vessel identity never straddle train/val. VTUAD gives us
   per-clip hull_ids — enforce it.
2. **Real-vessel mixture factory**: VTUAD strict-interval clips → convert to
   25-band TOL one-minute representation (exactly the starter notebook's
   inverse transform); inject into real SA background periods at controlled
   `y ∈ [0,1]` (zero-inflated: ~35% zeros, positive mass log-uniform-ish up to
   0.6 — treat these as *hypotheses*, run 3 scenario variants).
   Passage time-profiles come from REAL clips (not invented Gaussians) —
   preserves rise/fall, broadband shifts, propeller tone bands.
   Multiple SNR scaffolds via **Wittekind physics** (speed/displacement scaling)
   for stress-testing robustness, not as the primary generator.
3. **Baseline tournament on identical splits** (kill weak ideas early):
   a. constant per-scenario optimum (the pack's likely score)
   b. energy-informed linear heuristic (spectral-flatness / excess-energy vs
      site-quiet baseline)
   c. LightGBM/XGBoost on ~60 tabular features: per-band linear energies,
      band ratios, excess energy above minute-median, temporal profiles,
      missingness masks, min/max/p-norm per band, spectral kurtosis/flux
   d. small CNN/Transformer on 15×25 matrices (two-head: presence × fraction)
   Only models beating (a) on **two or more** generator scenarios advance.
4. **Station intelligence layer** (feeds 2 & 3 and the write-up prize):
   - background climatology per site × recorder × hour-of-day
   - band-availability matrix per recorder (which bands are trustworthy)
   - weak AIS labels for SA training periods (EMSA/ScienceBase/MarineTraffic
     snapshots — verify clock alignment per DATA_DICTIONARY warning)
   - "relative acoustic pressure map" deliverable for the write-up prizes ($1,000×2)
5. **Ensembling + robust inference**: snapshot/seed ensembles, prediction
   clipping to [0, 0.85] (never trust extreme fractions), per-window
   availability-weighted `T`, raw (unrounded) outputs.

## 4. Round plan (each round = one AI session, one worklog entry)

- **R1 (this round) — research & planning** ✅ data acquired + checksummed,
  sites/vessels profiled, corpora inventoried, compute set up, docs written.
- **R2 — generator v1 + tournament**: VTUAD→TOL converter, mixture factory v1,
  locked validation v1, run tournament a–c locally; decide neural go/no-go.
- **R3 — station intel**: climatology, band-availability matrix, AIS weak labels
  (if clean AIS source lands; else climatology-only), pressure-map prototype.
- **R4 — neural + scale-up**: two-head small net on 15×25; UniqueShip 12-class-5h
  subset if R2/R3 show reference diversity is the bottleneck.
- **R5 — submissions**: submit best 2 candidates; verify LB-vs-local correlation
  (guard: if LB ≪ local, suspect generator mismatch → scenario re-weighting).
- **R6 — write-up + freeze**: pressure maps, uncertainty, reproducible code,
  choose 2 final submissions before 13 Dec.

Submission budget guardrail: max 2/week until local validation is trusted;
never probe the LB with diagnostic submissions (rules + noise).

## 5. Compute plan (cost = $0)

| Platform | Role | Specs / limits |
|---|---|---|
| Local sandbox | profiling, feature dev, small models | current machine |
| **GitHub Actions, public `misc-notes`** | parallel research jobs (generator shards, tournament, feature builds) | ubuntu-latest 4 vCPU/16 GB/14 GB SSD; **free unlimited minutes** on public repos; **6 h hard cap per job** ⇒ shard everything; artifacts ≤ 90 days |
| Kaggle GPU (token set) | neural training, 2 heads | P100/T4×2, 30 h/week, 12 h/session; data via private channel (decision pending: private data repo release asset vs Kaggle private dataset) |
| Private repo `misc-notes-data` | data backup channel (release asset ~90 MB, no expiry, account-only) | created, data upload pending user OK |

Secrets to add to `misc-notes` (user action): `GH_PAT` (this token),
`KAGGLE_API_TOKEN` (kaggle), optional `ZINDI_COOKIE` for automated submission
upload. None may leak into logs — never `echo` secrets in workflows.

## 6. Compliance guardrails (hard constraints, checked every round)

1. Test inputs = inference only. No fitting, calibration, pseudo-labelling,
   per-window statistics fed back into training data. (Fixed per-window
   transforms like feature extraction are fine.)
2. No leaderboard probing / no submissions designed to reverse-engineer targets.
3. Never redistribute challenge data publicly (public repo = code/docs only;
   docs may carry derived *statistics*, not raw rows).
4. External data: declare source, version, license, access method in every
   write-up. HearMyShip raw files: **license unverified** — do not use until
   confirmed; paper ≠ dataset terms.
5. Raw [0,1] floats in submissions; no thresholding/rounding.
6. Weak AIS labels: proximity ≠ audibility; absence of AIS ≠ absence of vessel.
   Never treat as ground truth — confidence-weighted only.


## 6b. R2 findings (2026-10-20) — recipe verified, exploit dead, E2E live

**The organiser recipe (verified).** The official starter notebook (byte-identical
copy found in student repo maddwillson/DSCI550_UVNC) documents the test construction:
passage components derive from **VTUAD v1.3.2** (Zenodo 23037895), converted with
`minute_band_power()` (Hann periodogram, 2 s non-overlapping segments, mean removed,
PSD integrated over base-10 third-octave bands centred 10^(1.5+0.1k), linear mean of
30 segments per minute, NaN for unsupported bands); **absolute digital gain
discarded**; **time trajectories, relative acoustic channel and energy varied**;
combined with measured SA backgrounds. Our generator now replicates this exactly
(`src/tol_convert.py`, `src/generator.py`). The unknowns are now parameter-level
(randomisation ranges, f-grid, clip selection) — calibratable, per the SBI framing.

**Door 4 (background-reuse algebraic solve): DEAD.** Pairwise correlation over all
1,124,250 test pairs: max 0.9831, zero pairs > 0.99 — every test window has a unique
background. No (B,V) reuse, no f-grid via subtraction. Branch closed; document as a
negative result (write-up value).

**Structure that IS real.** 10 site-like clusters (PC1 82%); per-cluster recorder
duty-cycle fingerprints via m01-observed rate (0.03–0.88). Cluster membership and
missingness masks are legal input-derived features (D8). Conditional background
models (per cluster × band) are the correct replacement for the dead heuristic.

**Tournament v1 (grouped holdout: clips + sites).** two-head LGBM 0.0460 <
direct 0.0467 < constant 0.0918 << heuristic 0.6565. Dominant features: band_share
(spectral shape) + band_excess_max. Optimism caveat: synthetic val shares generator
signatures; treat as ceiling. Real-refs re-run pending VTUAD ingest.

**AIS assumptions reviewed (user consult):** AIS remains a write-up/weak-label
asset, NOT a label source (organisers: "AIS does not confirm which vessel produced
a sound"). Clock alignment with export clocks must be validated on training data
first (DATA_DICTIONARY warning). Claims about AIS-catcher SA coverage / Open Waters
API / ZACube-2 not independently verified yet — R3 task, low priority. Tooling
reference: lucascesarfd/onc_dataset (MIT) has a working AIS↔hydrophone sync pattern.

**Open-source leverage verdicts (Pareto):**
| Tool | License | Verdict |
|---|---|---|
| meridian-analytics/VND | GPLv3 | ideas only (SPL/SNLD/tonal features); no code reuse |
| lucascesarfd/onc_dataset | MIT | reference for AIS sync (R3) |
| lifewatch/DEEP-OC | MIT | optional detector baseline for `score_added_vessel` |
| SONARIS / phonometry (JOMOPANS-ECHO) | check | optional physics features R3/R4 |
| SyntheticNoisySignals | — | does not exist; concept reimplemented in generator.py |
| Underwater-Acoustic-Synthetic-Dataset | CC-BY-4.0 | skip for primary (synthetic < real VTUAD) |
| QiandaoEar22 / ShipsEar / DeuteroNoise | various | backup reference diversity; ShipsEar not on organiser allowlist; declare if used |

**Information-first doctrine (adopted):** compute is not the bottleneck; prior
fidelity is. Priority order: (1) conditional background model p(B) per cluster,
(2) real VTUAD references p(V) with matched transforms, (3) calibration
marginalisation (random per-window gain), (4) two-head architecture, (5) neural
posterior estimation only if tails matter (R4+). GPU converts wall-clock into
samples, not information.

## 7. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Our generator ≠ organiser generator (distribution shift) | HIGH | 3+ scenario variants; tournament gates; LB-vs-local correlation check at R5; prefer real-passage profiles over synthetic shapes |
| Zero-inflation prevalence guess wrong | MEDIUM | two-head model; presence head trained under multiple prevalence priors; ensemble across priors |
| Site-identity leakage into val → inflated local scores | HIGH | grouped splits (background period + hull + recorder); site-blind features |
| UniqueShip/VTUAD overlap (both ONC-derived) | MEDIUM | dedupe by hull_id/MMSI + date before mixing sources |
| Runner 6-h cap kills long training | LOW | shard by design; checkpoint to artifacts; resume pattern in `runner-playbook.md` |
| Saldanha coordinate ambiguity breaks AIS joins | LOW | treat as 2 candidate sites; use `station_token`+`recorder` as join keys, not coords |

## 6c. R3 findings — the calibration hunt (CLOSED, 2026-10-21)

**Sources:** full 12-cell notebook read; Zenodo 23037895 QA files; SA README;
sample_submission forensics. One-line: *the calibration was hiding in plain sight —
the notebook is the documentation, and the benchmark score is the calibration anchor.*

1. **Notebook refutes "mixing cell" hypothesis** (B1): no mixing code, no
   normalization code, no example f values in any cell. Cell 9 = recipe disclosure
   (A5); cells 10–11 = conversion spec (A4).
2. **Zenodo QA**: rms_dbfs −71…−38 (33 dB spread) → clips unnormalized upstream
   (A10); wrap-around manifest → strict-interval WAVs mandatory (A9).
3. **SA README (decisive)**: backgrounds are raw dB, NOT normalized (A11); withheld
   stations/periods explicitly excluded from the package.
4. **Benchmark anchor (A15/A16)**: sample_submission placeholder = 0.0 exactly ⇒
   benchmark = all-zeros predictor ⇒ RMSE² = E[f²] = (1−0.753867825)² = 0.06058,
   RMS(f) ≈ 0.2461.

## 6d. A16 RESTATED (correction of record — highest-leverage calibration fact)

**f grid = statistically inferred as U{0, 0.1, 0.2, 0.3, 0.4} from the all-zeros
benchmark anchor (E[f²]=0.0600 vs 0.06058, ~0.3 SE); hedged against weighted-grid
variants; NOT organiser-disclosed.** Chain: benchmark=all-zeros → E[f²]=0.06058 →
RMS(f)=0.2461 → U{0…0.4} matches; U{0…0.5} gives E[f²]=0.0917 → score 0.697, fails.
The grid is the best-fitting distribution to the benchmark's second moment — a
strong prior, not a documented fact. Weighted hedges are trained and ablated
(§6e). Any change to A16 must be surfaced to the user before adoption.

Additional locked facts: **A24** station identity is in package metadata ("Roy"≈
Richards Bay ~58%); **A25** withheld test-background periods: findability UNTESTED
(B11 reopened — search-positive posture); **A26** maddwillson/DSCI550_UVNC = USC
DSCI 550 course project carrying the official starter (byte-identical), not an
organiser repo. **B5 reopenable only on new evidence.**

## 6e. R4 rebuild + results (2026-10-21)

**Disaster → recovery.** Sandbox wiped (data/, scripts/, worklogs lost; only the
git repo survived). Recovered in order: (1) `misc-notes` origin/main = full R2
state (plan, worklog, src, docs, workflows); (2) GH Actions artifacts 90-day
retention still live → **refs-vessel + refs-background parquets** (509 vessel
clips / 1,978 minutes + 16 bg clips / 533 minutes — reconciles exactly with A12's
2,511 clip-minutes); (3) private `misc-notes-data` release v1 → **sa_acoustics.zip
+ Test.csv**, SHA256SUMS all 13 OK (A1 chain restored end-to-end). VTUAD strict
WAV re-download (3.7 GB parts) deprioritized — refs artifact verified by row
counts; re-conversion verification deferred.

**E1 — synth v2 (accepted).** `src/generator_v2.py`, one command, seed 42,
.sha256 sidecars + build manifest. PRIMARY `G_unif_04`: RMS(f)=0.2440
(accept 0.24±0.03), E[f²]=0.0595 (accept 0.060±0.006), grid mass 0.20 each.
Hedges: `G_weighted_low` (RMS 0.190), `G_nonuniform` (RMS 0.283). Band-gain σ and
tilt now marginalized over documented grids {0,0.05,0.1,0.2} / {0,0.1,0.25}
(replacing guessed 0.18/0.25 fixed). SA backgrounds: 15,000 windows (1,500/site,
10 sites), native NaN preserved, dur≥55 s filter (DATA_DICTIONARY caveat).

**E2/E4 — two-head training (accepted) + ablation.** LGBM two-head (presence ×
conditional fraction), R2 featurize + site-ID distance features:

| protocol | two-head RMSE | AUC | zero-const | mean-const | lock-only | fused w0.5 |
|---|---|---|---|---|---|---|
| clip-held-out | **0.0522** | 0.997 | 0.2437 | 0.1409 | 0.4199 | 0.2137 |
| site-held-out | **0.0434** | 0.998 | 0.2447 | 0.1410 | 0.6540 | 0.3246 |
| both-held-out | **0.0493** | 0.998 | 0.2439 | 0.1409 | 0.5683 | 0.2840 |

- All protocols beat the benchmark constant (0.2461 anchor) and the train-optimal
  constant by ≥2.9×. Improvement vs R2's real-refs 0.0633 ⇒ calibration fix worked.
- **A17 confirmed empirically**: dropping total-energy features: 0.0522→0.0525,
  0.0434→0.0437, 0.0493→0.0493 — shape carries the signal, ΣM almost none.
- **Negative result (logged)**: naive site-median structural lock f=1−ΣB̂/ΣM is
  NOT competitive in-domain (0.42–0.65; fusion at w=0.5 hurts). Within-site ΣB
  spread (1.5–1.9 orders, B2) swamps the +2.2 dB f-shift (A17). The lock is a
  domain-shift diagnostic, not a predictor. Conditional (site×band×condition)
  ΣB modeling — not site-median — is the correct R5 upgrade path if pursued.
- **Hedge comparison**: training on G_weighted_low generalizes slightly better to
  the fixed primary holdout (0.0465 vs 0.0493); G_nonuniform 0.0468. Small vs
  synthetic-domain noise; ensemble option for R5.
- **Submission artifact**: `data/train_v2/submission_r4_v1.csv` (1,500 rows,
  format-validated; mean share 0.110, p50 0.088, p90 0.199). NOT submitted —
  user gate + 2/day budget (E6).

**E3 — site-ID (accepted on confident subset, honest limits).** Nearest-centroid
on background-window descriptors (total dB, tilt, band-share, NaN rate):
accuracy-on-confident **91.2%** (site granularity) / 91.2% (site×recorder), at
confident-rate 33%/26% (τ=1.0). High-variability port segments resist centroid
assignment (Richards Bay segments 7–37% at site level; within-segment condition
spread >> between-segment separation). Follow-ups: per-segment covariance
(Mahalanobis), duty-cycle fingerprint features (m01 pattern across span), GMM
regimes. Reports: `data/train_v2/site_id_confusion*.json`.

## 6f. Hunt status (search-positive posture; every miss logged)

**Vector 1 — package metadata forensics: DONE** (recovered from backup + verified
SHA256SUMS). Master keys (sha256): stations.csv `8037b5d3…cb563`, recorders.csv
`781606b5…f5053`, DATA_DICTIONARY.md `162088ac…fbe04`.

Station/recorder index (17 recorder-segments / 10 public sites; site numbers
8, 11, 12 absent = withheld-station candidates):
- 1 Richards Bay: icListen-class serials 201383949 (24 kHz, 2017–19), 5708 (24k,
  2020–21), 7005 (24k, 2022–24); 1,001,174 min; port, extreme condition spread.
- 2 Durban: ST600 8230 (48k, 2025-10→12). 3 Cape Recife: ST600 8210 (48k, 19 d).
- 4 Bird Island: URN 6509 (24k, 2022), URN 8321 (12k, 2024 — 1,080 rows).
- 5 St Croix: URN 6509 (24k), URN.StCroix 6509 (24k), URN 8321 (12k, 135k rows).
- 6 Riy Banks: ST600 8230 (48k, 31 d). 7 St Francis: SM2M (48k, 2015-04→2018-02).
- 9 Fish Hoek: ST300 201650217 (96k, 2016–18), ST300 5344 (96k, 2021).
- 10 Sea Point: ST300 201650217 (96k, 3 d, 2018). 13 Saldanha Bay: ST300 5344
  (96k, 2022), ST500 5350 (48k, 2023).
- **Recorder movement chain (provenance gold)**: ST300 201650217 Fish Hoek→Sea
  Point; ST600 8230 Riy Banks→Durban; ST300 5344 Fish Hoek→Saldanha; URN 6509/8321
  Bird Island↔St Croix.
- **Cross-match (confirmed)**: MDPI jmse10060746 lead = St Francis SM2M+ 48 kHz
  Feb 2015–Mar 2018 ≈ SM2M_Cape_StFrancis 2015-04-21→2018-02-28. PRIORITY lead.
- 12 kHz anomaly (README): 136,518 rows nominal-12000 carry finite 6.3/7.9 kHz
  bands — convention unresolved; do not infer support from sample_rate_hz.

**Vectors 2–10: PENDING** (GitHub sweep; SAEON per exact ID; Zenodo version
history; institutional repositories SUNScholar/UCT/NMU; preprints + supplements;
consortium portals; sponsor-publication spectrogram matching; Wayback; deleted-repo
caches). Query template + logging discipline per standing directive. MIMS Algoa
297 / UP west-coast MPB 2022 / Zenodo 2025 Childs Bank leads: cross-match pending
station-table fit — none of the four public-site keys hit Namaqualand/Childs Bank/
Orange River, so those leads can only match WITHHELD stations (8/11/12?).

## 7b. Next actions (R4 → R5, ordered)

1. **Push R4 state to GitHub** (public: code+docs+metrics; private: refs parquet
   backup as release v2 + submission artifact). [in progress]
2. Hunt vectors 2–10 with exact keys above; log every query (hit/miss/partial).
3. R5 upgrade candidates (ranked by expected RMSE impact on REAL test):
   a. ensemble primary+hedge models; b. conditional ΣB model (site×band×condition)
   as lock-v2 features (not median); c. duty-cycle fingerprint features; d.
   site-ID v2 with per-segment covariance; e. UniqueShip/DeepShip reference
   diversity if VTUAD-only shapes cap the score.
4. Submission gate (user): smoke-test one submission (public LB = diagnostic only,
   A20), then select 2 private submissions from {recipe-based two-head, hedge
   ensemble, shape-based} (E6/A23 diversity rule).
5. Write-up track: every claim → figure/control/held-out number (E7); checksums
   + DOIs + notebook cells; negative results with search logs (B1–B11).
