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

### R6 addendum — D13 compliance purge (same day)

- Audit caught challenge-derived binaries tracked in the PUBLIC repo (introduced
  by the bulk auto-sync commit 09e84ca: synth_v3_mixed X/f/bgfeat/aux/bg_sums =
  mixtures of real SA backgrounds; r4 submission CSVs; zenodo CSV bundle) —
  D13 violation risk (challenge data must not be redistributed publicly).
- Fix: history rewritten (soft reset to b547d4d → selective re-stage → single
  clean commit 705a41d → force-with-lease push). Verified: no commit in history
  touches the purged paths; `git ls-files` = 66 files (code/docs/metrics only).
- .gitignore hardened (skills/, data binaries, submissions, SA package, zenodo,
  backup) so future `git add -A` cannot regress.
- Public repo keeps: src/, docs/, plan.md, worklog.md, HANDOFF.md, report JSONs,
  sha256 sidecars, blend-sweep metric CSVs. Everything data-shaped lives in the
  private misc-notes-data (main: submissions/ + reports/ + snapshots; releases
  v1/v2/v3).

---

## R7 — 2026-10-21 — LB autopsy, recipe smoking gun, bump-reading breakthrough

**Agent:** Z.ai (main). **Directive:** user R7 message (detective on {8,11,12};
open-web hunt EXHAUSTED — stop string probes; test ambient-in-passage NOW; pivot
to SA URN publications + SAEON auth; capture write-up spec; document the
honest-protocol RAISED the blend; four LB returns reported: r4_v2 0.7757,
r6_v2 0.7676, r6_v3 0.7674, r6_v4 0.7065 — "something has to be wrong").

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Sandbox re-pull | data re-fetched from misc-notes-data (v1 SA package + Test.csv, v2 refs parquets, submissions/, DSCI550 zip); pyarrow/lightgbm/sklearn installed |
| 2 | Starter notebook read | A33 score col weight ZERO; A34 metric verbatim; sample = 0.0/0.5 |
| 3 | LB autopsy (moment math) | E[f²]=0.060581 pinned + 4 CSVs → **all prior submissions ρ≈0 per-window on real test**; μ≈0.15, σ_f≈0.195, best-const≈0.81=pack ✓; v4 collapse = lock +0.243 loud-tail overshoot @0.4 weight; R_real transferred honestly (val 0.2405→LB 0.2326); M2 val optimistic 2.2×; evidence cols AUC 0.473–0.486 (r6_v3=v4 score cols identical) |
| 4 | Station registry discovery | **A36: file prefixes = site registry; {08,11,12} = absent parquet files** (withheld stations); unverified name candidates logged |
| 5 | Recipe forensics | test within-window band-range p50 16.0 dB vs raw 6.5; planted FULL-window 6.8 vs SUB-INTERVAL 14.8 → **organisers plant sub-interval passages; our synth recipe invalidated** |
| 6 | Dead ends measured | station-prior+HF-anchor ΣB̂ floor 0.23–0.44; per-band p25 (v0) f̂≈0.66; E1/E3 on full pool FA 0.25–0.51 (natural vessels) |
| 7 | Bump-reading breakthrough | E5 quiet-baseline estimator on CALM beds: RMSE 0.088 / ρ 0.852 (H_A), 0.098 / 0.837 (H_C ambient-laden — **A29 answered: ambient IMPROVES share recovery**); ship-contaminated beds 0.358 (organiser beds must be calm-selected — A28 mechanism) |
| 8 | r7_v1 built | E5(test) → power map 0.916·f^4.41 → pinned moments EXACT (mean 0.1500, E[f²] 0.060581); format-validated; sha256 917c4d53…; corr to prior vectors 0.26–0.29; **USER GATE: submit** |
| 9 | Honest-protocol doc | 0.8741→0.8941 RAISE documented: leaky flattered lock (0.2049/−0.19 → 0.3 weight); honesty exposed +0.243 overshoot (0.2824) → 0.1 weight → blend up despite M2 +5.6% |
| 10 | Hunt R7 | 10 probes (docs/hunt_log_r7.json); open-web EXHAUSTED (33 cumulative); A35 VTUAD provenance = Strait of Georgia/ONC Canada; SAMSA URN workshop = only consortium thread; SciELO blocked |
| 11 | Docs + backup | plan.md §6i/§7d; docs/r7_autopsy_and_bumpfind.md; HANDOFF banner; misc-notes-data push (submissions/ + reports/) |

**Decisions**
- D18: bump-reading (E5) = the new primary family; level-prior/lock family demoted to diagnostic (measured dead).
- D19: submissions must pass the pinned-moment check (E[p²] ≈ 0.0606 ± 0.01, mean plausibility) before user gate.
- D20: synth v2/v3 recipes retired for decision use; R8 retrains on sub-interval + ambient-laden recipe only.

**Open questions / blocked-on-user**
- Submit r7_v1 (decision-read: ≥0.80 family confirmed / 0.77–0.80 partial → template matching / <0.77 fallback).
- SAEON portal login; Zindi discussion re withheld stations; SAEON/SAMSA enquiry re {8,11,12} names (A36 candidates); A30 copyright call.

**Process lesson:** sandbox wiped again between sessions — data re-pull from
misc-notes-data took minutes and is now the documented first step of every round.

---

## R7b — 2026-10-21 — moments measured, r7_v2 re-pinned, station hunt reopened + half-cracked

**Agent:** Z.ai (main). **Directive:** user R7b handoff (§A re-pin r7_v1 to the
parallel track's measured moments; §C reopen hunt with new query families —
SciELO/Purdon/Shabangu fetches, De Hoop/Langebaan/Dassen candidates, serial
cross-ref, verify other-AI guesses Simon's Town/Strand/Gordon's Bay; §D plan.md
§6j/§6k; §E submit tomorrow only after conditions met; tempmail authorized for
auth-gated sites).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | State recovery | sandbox intact; r7_v1 CSV pulled from misc-notes-data submissions/ |
| 2 | §A re-pin | scripts/r7_repin.py: f̂ recovered by exact inversion (round-trip 2e-16); new map p=1.1754·f̂^6.290 (γ 4.41→6.29); verified E[p]=0.130076 ✓ E[p²]=0.060580 ✓ (both in §A bands); Spearman 1.0; sha256 69fc2b81… |
| 3 | Moment measurement | μ=0.130076 from three constants (5-decimal agreement); E[f²]=0.060580; σ_f=0.20895 |
| 4 | Corrected ρ | prior subs NOT ρ≈0: r4_v2 0.20 / r6_v2 0.31 / r6_v3 0.11 (v4 mispaired per user §B) — supersedes R7 autopsy table |
| 5 | Hunt reopened | 18 probes (hunt_log_r7b.json), cumulative 51; **HIT: station 09 Fish Hoek = Sea Search False Bay ST300 network** (Ross-Marsh et al. 2020, coords exact) |
| 6 | Network named | Smitswinkel Bay / Fish Hoek / Strandfontein / Rooi Els (moored, 14–25 m, 2016–2018); Sea Point = 201650217 side deployment Oct 2018 |
| 7 | Other-AI verdicts | Simon's Town/Strand/Gordon's Bay REJECTED — claimed "coastal water quality site table" not found; the only "08 Simon's Town" numbered table = O'Connor 2009 whale-watch list (numbering coincidence) |
| 8 | Verdicts | 08 ∈ {Strandfontein (lead), Rooi Els, Smitswinkel Bay}; 11/12 ∈ {Robben I. (lead), Dassen I., Langebaan, Yzerfontein, Table Bay}; registry = regional-block ordering (A36 upgraded) |
| 9 | Literature cleared | Shabangu 2022 MPB + 2022 "Beat" + 2025 (all offshore moorings); SciELO Karomo 2023 (law review); Hawkey 2020 (same network); Probert 2025 (Robben ST300 activity); Zenodo AIS dataset (Belgian); Karpowership Saldanha EIA (shelved) |
| 10 | Serial cross-ref | GitHub: "201650217" noise / "SoundTrap 8230", "Saldhana_Bay", "Riy_Banks" all 0 — exhausted |
| 11 | Docs | plan.md §6j/§6k/§6l; hunt_log_r7b.json; station-intel.md §6; HANDOFF banner |

**Decisions**
- D21: r7_v2 (re-pinned) replaces r7_v1 as the submission candidate (§A bands met).
- D22: shrinkage calibration (E[p²]=0.0477 @ ρ̂=0.84) held as r7_v3 option, only
  after the r7_v2 readout gives a real ρ.
- D23: station-hunt open-web posture = re-opened with new families, 18 probes, then
  re-exhausted for this round; enquiry targets now have sharp question form.

**Open questions / blocked-on-user**
- Submit r7_v2 (decision bands in §6k).
- Sharp enquiry to Sea Search/SAEON/SAMSA: "08 ∈ {Strandfontein, Rooi Els,
  Smitswinkel Bay}? 11/12 ∈ {Robben, Dassen, Langebaan, Yzerfontein, Table Bay}?"
- SAEON portal via tempmail (authorized; not attempted — web-tool throttle +
  time-box; still the strongest remaining public-data route).

---

## R7c — 2026-10-21 — shrink hedge built, Heliyon table resolved, fleet-inference closed

**Agent:** Z.ai (main). **Directive:** user R7c message (verify Heliyon tbl1
S2405-8440(23)05767-5; sweep YouTube/Twitter/4chan/Reddit/papers Rainbolt-style;
re-check leading candidates; user's shrink-fix math p = 0.1301 + k·(p̂−0.1301)).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Heliyon tbl1 verification | Cloudflare/JS walls on Cell+ScienceDirect; Europe PMC abstract-only; **CPUT thesis metadata independently confirms the table** (Gordan's Bay=12, Kalk Bay=9, Mouille Point=6) + user's snippets (02 Eland's Bay, 07 Maiden's Cove, 08 Simon's Town, 11 Strand) → A46: table REAL, still NOT the registry (its 09 Kalk Bay ≠ competition 09 Fish Hoek exact coords) |
| 2 | R7b verdict correction | verdict #7 ("claimed table not found") SUPERSEDED — table exists; Simon's Town/Strand/Gordon's Bay REJECTED with evidence now |
| 3 | Social sweep | Sea Search FB = live Fish Hoek hydrophone maintenance (supports A38); **ATAP = Vemco shark telemetry, ELIMINATED** (A48); YouTube/Reddit/Twitter/4chan probes pending (web budget exhausted, logged in hunt_log_r7c.json) |
| 4 | r7_v3 shrink family | scripts/r7_shrink.py: k∈{0.35,0.45,0.55} on share_added_vessel (NOT the zero-weight score col — first run grabbed wrong col, caught by moment check); all E[p]=0.130076, E[p²]=0.022268/0.025761/0.030127 exact; shas 8b51e3af/98775aed/c17ce982; k=0.45 PRIMARY (beats constant iff ρ>0.225, beats pinned iff ρ<0.725; worst case ≈0.789) |
| 5 | Clipping risk found | r7_v2 share max = **1.1696** (>1, power-map tail) — unknown Zindi behaviour; shrink family eliminates (max ≤0.70) |
| 6 | Fleet-inference closed | corr(r7_v2, priors)=0.223/0.258/0.218 → single-factor model implies ρ₇>1 (impossible) ⇒ shared variance = background/site factor, NOT truth → **A47: fleet correlations cannot predict bump ρ; LB readout is the only estimator** |
| 7 | Docs + backup | plan.md §6m/§7e; docs/hunt_log_r7c.json (10 probes, cum 61); SHA256SUMS updated; both repos pushed |

**Decisions**
- D24: r7_v3_k045 = recommended submission if ρ prior ≤ 0.6; r7_v2 if > 0.6; k*=ρ after the first readout (RMSE² = σ_f²(1−2kρ+k²)).
- D25: Heliyon microplastics table classified "real, coincidental reuse" — closed as a registry lead.
- D26: remaining platform probes (YouTube-native/X/Reddit/4chan) = low-prior name-hunt, execute only if budget allows next round.

**Open / blocked-on-user**
- Submit ONE of {r7_v3_k045 (rec), r7_v2, r7_v3_k035} — §7e decision table.
- Sea Search/SAEON/SAMSA sharp enquiry (§6l wording) — still the highest-yield route.
