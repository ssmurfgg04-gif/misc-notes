# worklog.md — misc-notes project log

> Format: newest first. One entry per work round. Keep entries scannable —
> tables and bullets, no prose walls. Target < 40 KB total (the old project's
> 223 KB log is the anti-pattern). Deep detail lives in `docs/`, not here.

---

## 2026-10-20 · R1 · research & planning · agent: Z.ai (GLM)

**Goal:** data hunt, vessel profiling, prior-art sweep, compute setup, plan v2, handoff.

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | GitHub recon | token OK (acct `ssmurfgg04-gif`); `context-m` cloned; prior Zindi repos inspected for patterns |
| 2 | Data acquisition | full official package via Kaggle mirror `renjistarfall/underwater-vessel-noise-private` — **all 15 files pass official SHA256SUMS** — stored `/home/z/my-project/data/` |
| 3 | SA data profile | 10 sites / 1,715,779 rows profiled → `docs/station-intel.md` |
| 4 | Vessel profile | VTUAD v1.3.2 metadata (525 clips, 178 hulls, 5–452 m) → `docs/vessels.md` |
| 5 | Prior-art sweep | GitHub code search: **0 public hits** for 4 competition-specific queries — no one has published |
| 6 | Corpus inventory | UniqueShip (CC-BY-4.0, subsets from 17.8 GB), VTUAD (CC-BY-4.0, ~25 GB), HearMyShip (license unverified), DeepShip (request), Wittekind physics gist → `docs/data-links.md` |
| 7 | Compute | GH runners verified (public repo: free, 4c/16 GB, 6 h/job); Kaggle token live (Bearer API works; CLI 2.2.4 quirks noted); `misc-notes` repo created + workflows templated |
| 8 | Memory | cortexm (`context-m`) evaluated → adopted for facts db; HANDOFF.md written |

**Key evidence (the numbers that matter)**
- Test missingness: m01 = **41.6%**, m15 = 6.7%, m02–m13 ≈ 0 ⇒ availability masks are first-class features; aggregate on observed cells only.
- Richards Bay = 58% of training rows; Bird Island loudest (p50 94.4 dB, seal colony); Sea Point only 3 days.
- LB: #1 = 0.8720 clear of pack 0.816–0.824 (pack ≈ good constant baseline).
- Recorder hardware varies (SM2M/ST300/ST500/ST600/URN, 12–96 kHz) ⇒ site-blind features mandatory.

**Decisions**
- D1: repo = public `misc-notes` (code/docs only — no challenge data in public).
- D2: data backup via private `misc-notes-data` release asset — **pending user OK** (also considering private Kaggle dataset for GPU notebooks).
- D3: adopt cortexm for structured facts; markdown stays source of truth.
- D4: primary reference library = VTUAD strict-interval (license clean, per-class zips, hull registry); UniqueShip 5h/class subset as R4 scale-up.
- D5: HearMyShip blocked until license confirmed on the download portal.

**Next round (R2) entry point:** see `HANDOFF.md` § first-tasks.

---

**R1 addendum (same day, after push)**
- Smoke run `39451412858` SUCCESS: 8 shards + aggregate, private data pull via
  `GH_PAT` works. Compute loop is live: edit `src/task.py` → dispatch → merge artifacts.
- Data backup live: private `misc-notes-data` release v1 (`sa_acoustics.zip`,
  `Test.csv`), account-only.
- cortexm verdict: adopt — chunk-recall (`search()` → `context_block`) retrieves
  the 8 project docs correctly; triple extraction is noisy for dense technical
  facts, so markdown stays source of truth (D3 confirmed). db: `memory.db`,
  `user_id=uvn`.


---

## 2026-10-20 · R2 · recipe verification + forensics + E2E v1 · agent: Z.ai (GLM)

**Goal:** verify user's hypotheses (reuse exploit, AIS, open-source leverage), replicate
organiser recipe, first E2E generator→model→submission run.

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | DSCI550_UVNC repo | student repo carrying the OFFICIAL starter notebook (md5 identical to challenge package). Cell 9 = recipe: passages from **VTUAD v1.3.2**, converted to minute-level band summaries, **absolute digital gain discarded**, time trajectories + relative channel/energy varied, mixed with measured SA backgrounds. Cell 11 = EXACT conversion code (Hann periodogram, 2 s segments, mean-removed, band integration on 10^(1.5+0.1k) centres, 30-segment linear minute mean) |
| 2 | Forensics: reuse exploit | **DEAD — no shared backgrounds.** Max pairwise corr 0.9831; zero pairs > 0.99. Every window has a unique background ⇒ algebraic M1−M2 solve impossible. Negative result documented, branch closed |
| 3 | Forensics: clusters | 10 site-like clusters (PC1 = 82% level variance); per-cluster recorder duty-cycle fingerprints (m01 observed: 0.03 → 0.88). Cluster = recorder ≈ site. Legal input-derived features; powers site-conditional background modeling |
| 4 | Forensics: excess proxy | crude cluster-median excess swamped by background heterogeneity (median 0.75) — needs proper conditional background model; only ~1% of windows show <5% excess (weak lower bound on low-f mass) |
| 5 | Tool review (Pareto) | VND = GPLv3 (ideas only: SPL/SNLD/tonal features); onc_dataset MIT (AIS sync reference, R3); DEEP-OC MIT (detector baseline signal); SyntheticNoisySignals **does not exist** (hallucinated); synthetic-waveform datasets inferior to VTUAD (organiser source); sbi-package framing adopted conceptually (priors/posteriors), NPE deferred to R4+ |
| 6 | TOL converter | implemented the documented conversion exactly; self-test passes (tone band +28 dB vs neighbours) |
| 7 | Generator v1 | mixture factory replicating documented transforms (unit-energy refs, stretch/tile trajectory variation, lognormal+tilt channel variation); 3 scenarios (zero-rate 25/35/45%, log-unif mass); SA backgrounds from all 10 sites with native missingness |
| 8 | Tournament v1 | **two-head LGBM 0.0460 / direct 0.0467 / constant 0.0918 / heuristic 0.6565 (dead)** on grouped holdout (clips+sites). Top features: band_share (spectral shape) + band_excess_max. CAVEAT: synthetic val shares generator signatures ⇒ 0.046 is an optimistic ceiling, not an LB forecast |
| 9 | VTUAD ingest | dispatched to GH runners (2 parallel jobs, Zenodo download + convert → refs parquet artifacts, 90-day retention) |

**Decisions**
- D6: two-head (presence × conditional fraction) is the primary architecture — best RMSE and produces `score_added_vessel` natively.
- D7: heuristic (cluster-median excess) abandoned — background heterogeneity kills it at both window and cluster level; conditional background model is the R3 replacement.
- D8: cluster-derived features (membership prob, m01-fingerprint) added to the legal feature set — derived from provided inputs only.
- D9: keep all forensic scripts local-only for now (public repo gets summaries) — prudent disclosure posture until user decides on write-up framing.

**Open questions**
- Q1: does the write-up disclose cluster/recorder fingerprinting? (legal per letter; flag to user)
- Q2: AIS verification — AIS-catcher SA stations / Open Waters API claims from user's consult not yet independently verified (R3, low priority: AIS is write-up asset, not label source)

**R2 completion addendum (same day)**
- VTUAD ingest verified end-to-end on GH runners: 509 vessel + 16 background clips →
  62,775 minute-band rows (all powers real; an earlier "all-zero" scare was our own
  `describe().round(3)` display rounding, values are ~1e-9 — noted to avoid repeat).
- Registry join fixed via strict-interval paths (`vessel/<n>.wav` ↔ registry `path`);
  metadata restored (label, hull_id, length, beam; 179 hulls, 525 clips).
- Fixed 2 real bugs found by E2E: reference-stretch broadcast `(1,15,25)`;
  bool `@` matmul in forensics (N=1). Both now covered by self-tests.
- Tournament on REAL VTUAD refs (12k mixtures, grouped holdout clips+sites):
  **two-head 0.0633 ≈ direct 0.0632 << constant 0.092 << heuristic 0.714 (dead)**.
  Physics-ref run (0.046) confirmed as optimistic ceiling — real refs harder,
  as designed. Dominant features: band_share 20–24 (cavitation HF), flatness.
- E2E artifact: `data/submission_r2_v1.csv` — 1,500 rows, format-validated
  (IDs match, finite, [0,1]). Mean share 0.115, mean score 0.736. NOT submitted
  (2/day budget; user gate).

---

## R4 — 2026-10-21 — sandbox wipe recovery + corrected synth v2 + two-head retrain

**Agent:** Z.ai (main). **Directive:** handoff brief §E + user GitHub keys + A16 restatement.

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Sandbox wipe forensics | data/scripts/worklogs lost; git repo + upload brief survived; no creds in env |
| 2 | GitHub recovery | origin/main = R2 state; GH Actions artifacts still live (90-day retention): refs-vessel (509 clips/1,978 min) + refs-background (16 clips/533 min) recovered, row counts reconcile with A12 (2,511 clip-minutes) |
| 3 | Data package recovery | private `misc-notes-data` release v1 → sa_acoustics.zip + Test.csv; **SHA256SUMS 13/13 OK** (A1 chain restored); stations.csv + recorders.csv + DATA_DICTIONARY.md recovered = hunt vector 1 keys |
| 4 | Zenodo re-download (deprioritized) | QA files + metadata fetched; strict WAV parts 01 (85%)/02/03 partial on disk, resumable via `scripts/fetch.sh`; refs artifact made conversion-verification optional |
| 5 | E1 synth v2 | `generator_v2.py` seed 42: PRIMARY G_unif_04 RMS(f)=0.2440, E[f²]=0.0595 → **ACCEPTED** (0.24±0.03 / 0.060±0.006); hedges G_weighted_low (0.190) + G_nonuniform (0.283); σ∈{0,0.05,0.1,0.2}, tilt∈{0,0.1,0.25} marginalized; 15k SA bg windows, dur≥55s filter |
| 6 | E2 two-head retrain | clip/site/both-held-out RMSE **0.0522/0.0434/0.0493**, AUC 0.997–0.998; beats zero-const 0.244 and mean-const 0.141 by ≥2.9×; vs R2 real-refs 0.0633 → calibration fix confirmed |
| 7 | E4 ablation | no-total-features: 0.0525/0.0437/0.0493 → **A17 confirmed** (shape carries signal); **negative result:** site-median lock 0.42–0.65 + fusion hurts in-domain (within-site ΣB spread swamps +2.2 dB f-shift); lock = domain-shift diagnostic only; hedges 0.0465/0.0468 vs primary 0.0493 on fixed holdout |
| 8 | E3 site-ID | nearest-centroid: 91.2% accuracy-on-confident @ 33%/26% coverage (site / site×recorder); Richards Bay segments resist (7–37%) — follow-up: per-segment covariance, duty-cycle fingerprints |
| 9 | Submission artifact | `data/train_v2/submission_r4_v1.csv` format-validated (mean share 0.110, p50 0.088) — **NOT submitted** (user gate, 2/day) |
| 10 | Docs | plan.md §6c–§7b appended (A16 restated, results, hunt status, next actions) |

**Decisions**
- D10: A16 written as *statistically inferred*, never "organiser-disclosed" (user correction of record).
- D11: hedge variants built but submission = primary model; hedge ensemble is an R5 candidate.
- D12: structural lock demoted to diagnostic; conditional ΣB (site×band×condition) is the lock-v2 path.
- D13: public repo gets code/docs/metrics only; SA parquets/Test.csv NEVER pushed to public (rules); refs parquet (VTUAD, CC-BY-4.0) + submission artifact → private repo release.

**Open questions**
- Q3: does the write-up disclose cluster/recorder fingerprinting? (carried from R2 Q1 — user call)
- Q4: rules decision if exact test backgrounds ever surface (B11 hunt) — user decides after provenance visible.

**Blocked-on-user**
- Zindi login or 2 manual submissions (E6); approval to push refs/submission release v2 to `misc-notes-data` (defaulting to yes per "backup everything" directive).

### R4b same-day addendum — the recipe question resolved to a decision table

- Push conflict integrated: origin d9241a3 (parallel hunt session's mission update) — claims H_B background-matched recipe M≈B/(1−f); independently verified before adoption (guardrail: no verdict without own search/experiment).
- Ran experiments P (plant control: 99.5% detect in-distribution; test p50 0.987 PRESENT — contradicts their p0=0.981; both = condition artifacts), R (matched-level residuals: test is windier/flatter than level-matched pool — condition shift, recipe-non-diagnostic), M1/M2/M3 (recipe-exclusive models; mixed two-head 0.073/0.102; ΣB̂ absolute-feature poisoning found+fixed via scale-invariant subset; blend w=0.3 → 0.8741 synthetic-equivalent).
- Bayesian verdict ≈85% H_B from pack-below-constant evidence (0.816–0.824 < 0.859 with 122 competitors); #1's 0.872 reproducible by our blend on H_B val.
- 5 submission candidates prepared (r4_v1/v2_mixed/v3_HA/v4_superseded/v6_blend); smoke-test recommendation: r4_v2_mixed, then r4_v6_blend. User gates all submissions (E6).
- Known limitation logged: ΣB̂-family circularity (val windows built from pool backgrounds seen by regressor) — R5 enforces background-window-group splits.
- Files: src/recipe_discrimination.py, src/synth_v3_mixed.py (seed 43, sha256 sidecar), src/train_v3.py; reports in data/train_v2/recipe_discrimination.json + data/train_v3/{decision_table,lockv2b_report,blend_report}.json.

---

## R6 — 2026-10-21 — circularity fixed, honest blend, pursue-real, hunt {8,11,12}, full backup

**Agent:** Z.ai (main). **Directive:** user R6 message (chase 8/11/12; fix circularity
via background-window group splits; rerun blend — honest number; data repo = single
backup home incl. submissions folder; DSCI550 zip = user's local clone; less
synthetic, more real; update plan.md).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Repo state recovery | sandbox restored from git (R4b state); data re-pulled from misc-notes-data v1/v2: SA package 14/14 checksums OK, Test.csv md5 = official, VTUAD refs 49,450+13,325 rows = A12-exact; deps reinstalled |
| 2 | DSCI550 zip (user's clone) | found in data repo root as `competition files main.zip`; extracted + verified: notebook 12 cells, md5 `20e62deb…` (official), Test.csv md5 `f45428f9…` = official; preserved in data repo + README provenance |
| 3 | Circularity fix | `src/r6_bgmap.py`: seed-43 pool reproduced deterministically (24,000/24,000 synth windows mapped, loud-tail agreement 1.0); bg-window split G_train 12k / G_val 3k site-stratified seed 7 → `bg_split.csv`; protocol: no synth-val window shares bg row with ANY component's training input |
| 4 | Honest rerun | `src/train_v3_v31.py`: M2 H_B 0.1078 (leaky 0.1018 → circularity bounded +5.6%); ΣB̂ window-split 0.147/0.799 dB, site-heldout 3-fold 0.444/1.989 dB; lock f H_B 0.2824 (leaky 0.2049); **loud-tail ferr SIGN FLIP +0.243** (leaky said −0.19); honest blend (0.9 M2, 0.1 lock, 0 const) → **H_B 0.1059 → score 0.8941**; R4b 0.8741 retired (leaky-protocol number, not comparable) |
| 5 | Pursue-real | R_real two-head on 16k REAL mixtures (real bg × real VTUAD clips, H_A; clip+bg group splits): 0.0590/AUC 0.997 in-domain; v3 H_B val 0.2405; real+lock blend w_lock 0.4 → 0.1736 |
| 6 | Submissions | 4 r6 CSVs written + format-validated (r6_v1_mixed / r6_v2_blend / r6_v3_real / r6_v4_blend_real); smoke rec: r6_v2_blend; user gate |
| 7 | Hunt {8,11,12} | 23 probes (19 web + GH code API + metadata grep + Wayback attempt) → no public record names stations 8/11/12; geographic gaps: 8 between St Francis/Fish Hoek, 11+12 between Sea Point/Saldanha; **A27 suppliers = SAEON+SANBI+SA URN Consortium** (consortium has no public footprint); A28 test bg periods excluded from release; A29 passage ref may carry ambient (H_C reopened); A30 copyright assignment (top-3); A31 write-up eval spec; log: docs/hunt_log_r6.json |
| 8 | Backup | misc-notes-data: main pushed (submissions/ 9 CSVs+SUMS, reports/ 15 JSONs, snapshots, README inventory); release v3 = vtuad_metadata_qa.zip (Zenodo insurance); release v1/v2 verified after re-pull |
| 9 | Docs | plan.md §6h + §7c added; HANDOFF banner updated; hunt log written |

**Decisions**
- D14: honest protocol = bg-window-group splits mandatory for ΣB̂-family metrics; R4b leaky numbers retired from decision use.
- D15: lock weight capped at 0.1 (blend optimum) — justified by measured site-extrapolation error (0.444 dB p50) since test stations/periods are withheld (A28).
- D16: R_real = recipe hedge + write-up engine; M2/blend remains H_B primary pending smoke test.
- D17: data repo misc-notes-data = single backup home (main: submissions/reports/snapshots; releases: bulk data); sandbox NOT a delivery channel (user cannot download from it).

**Open questions / blocked-on-user**
- Zindi login: smoke-test r6_v2_blend + verify LB state (crawler showed benchmark-only render — artifact?).
- User-routable hunt: SAEON portal login; Zindi discussion re withheld-station policy; SAEON/consortium enquiry.
- A30 flag: top-3 winners assign worldwide copyright of solution code to Zindi — acceptable?

**Process lesson:** R4b blend ran inline (never persisted) → unrecoverable; R6 rebuilt from spec. Rule 9 (script persistence) now enforced with zero exceptions.
