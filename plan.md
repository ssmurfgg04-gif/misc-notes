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

## 7. Risks & mitigations

| Risk | Likelihood | Mitigation |
|---|---|---|
| Our generator ≠ organiser generator (distribution shift) | HIGH | 3+ scenario variants; tournament gates; LB-vs-local correlation check at R5; prefer real-passage profiles over synthetic shapes |
| Zero-inflation prevalence guess wrong | MEDIUM | two-head model; presence head trained under multiple prevalence priors; ensemble across priors |
| Site-identity leakage into val → inflated local scores | HIGH | grouped splits (background period + hull + recorder); site-blind features |
| UniqueShip/VTUAD overlap (both ONC-derived) | MEDIUM | dedupe by hull_id/MMSI + date before mixing sources |
| Runner 6-h cap kills long training | LOW | shard by design; checkpoint to artifacts; resume pattern in `runner-playbook.md` |
| Saldanha coordinate ambiguity breaks AIS joins | LOW | treat as 2 candidate sites; use `station_token`+`recorder` as join keys, not coords |
