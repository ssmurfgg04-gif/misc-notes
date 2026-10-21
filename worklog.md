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

---

## R7d — 2026-10-21 — test-window census: 3 groups = 3 stations; south-coast 08 elevated

**Agent:** Z.ai (main). **Directive:** user R7d (test the 7-rank
counterintuitive-hides theory against data; queued YouTube/X/Reddit/4chan
probes; south-coast literature never swept).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Data recovery | Test.csv (md5 = official) + sa_acoustics.zip from release v1 via GH API asset flow; pyarrow/sklearn reinstalled |
| 2 | Notebook correction | **m01..m15 = minute positions 1..15** (cell 2), NOT metric types — missingness = export window-edge cropping |
| 3 | Availability census | 2-bit fingerprint → **exactly 3 groups** (sil 0.998): G0=777 / G1=623 (m01-missing) / G2=99 (m15-missing) + 8 noise; unimodal levels ⇒ 3 stations, one slot each — **reserved-slot theory REJECTED** |
| 4 | Bed-floor matching | G0 63.0 dB/−8.3 ≈ **Saldanha ST300** (RMSE 2.23); G2 64.8/−8.0 ≈ **Durban harbour** (2.47) — short campaign; **G1 72.2/−5.7 matches NOTHING** (best 4.43, tilts ≥2.7 off) |
| 5 | Verdicts | 7 ranks: #1 south-coast 08 ELEVATED (G1 unmatched + zero public south-coast moorings — Hofmeyr-Juritz 1999/2011 = boat sessions only); #2 False-Bay 11/12 WEAKENED (tilt mismatch); #4/#7 REJECTED; #5 ~5%; #3 alive-lowered; #6 weak-possible for G1. Mapping: **G1↔08, {G0,G2}↔{11,12}** (G2 harbor-tinged → Table Bay raised) |
| 6 | Platform probes | YouTube ×3 JS-walled; Reddit 0; 4chan archives 0; X 0 — no public trail |
| 7 | Docs + backup | hunt_log_r7d.json; plan.md §6n/§7f; HANDOFF banner; both repos pushed |

**Decisions**
- D27: counterintuitive-hides theory = PARTIALLY VINDICATED by data (rank 1 only); the rest rejected/weakened. Enquiry card upgraded to acoustic-fingerprint form (answerable without naming).
- D28: station-name slate revised — 08: south-coast/unmatched-class ~40% (Hermanus/Gansbaai/Agulhas/Mossel Bay etc.), Sea Search False Bay pool ~30%; 11/12: west-coast pair ~65% with Table Bay harbour RAISED (G2 harbor bed), Robben/Dassen/Langebaan retained.

**Open / blocked-on-user**
- Submit r7_v3_k045 (rec) or r7_v2 → ρ readout → k* = ρ.
- Send the A53 fingerprint enquiry to Sea Search/SAEON/SAMSA.

## R7e — 2026-10-21 — Scholar/arXiv technique harvest + south-coast intel: Mossel Bay array, harbour ST300, fingerprint-conditioning playbook

**Agent:** Z.ai (main). **Directive:** user R7e ("use these findings to get even
more findings; research even on Google Scholar and arXiv for best technique; be
methodical").

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | South-coast sweep (Mossel Bay/Knysna/Plett/Hermanus/Gansbaai) | **HIT: Dines PhD 2025 (Stellenbosch/Sea Search) — Mossel Bay SoundTrap 300/500 from 19 Mar 2021 + six-week 3-site 5-hydrophone south-coast array + new long-term Mossel Bay deployment (Oceans Research, Aug 2025, EIA-motivated)** → A55; Mossel Bay = rank-1 named 08 candidate. Gansbaai Sea Shepherd Dec 2023 = unresolved partial |
| 2 | Harbour probe | **HIT: Probert/Elwen/Gridley 2025 Sci Rep — ST300 at V&A Waterfront (Cape Town harbour), NYE 2023, ~16 h** → A56; G2 (99 win ≈ 25 h harbour-tinged) → Table Bay/Cape Town harbour strengthened |
| 3 | Provenance chase | **HIT: Schoeman/Erbe/Plön 2022 JMSE — SM2M+, 15-min duty-cycled windows, Feb 2015–Mar 2018, SF/AB1/AB2a/AB2b; wind r>0.7 at 1–2.5 kHz** → A54; wind-detrend/shape features mandated |
| 4 | Agency probe | SAMSA = GloNoise lead pilot country (RAINDROP EIAs, workshop Mar 2026) → A57 new enquiry target; MIMS portal JS-walled |
| 5 | VTUAD/technique harvest (13 queries: arXiv 2505.23964, Hummel 2026, DCASE SED line, ICML calibration, Stowell/Jeantet) | **A58: VTUAD fixed-filter collapse 97→84% across bed levels (background confound) = our G1 problem; CATFISH metadata fusion 91.6→96.3%**; frozen embeddings dominated by recording variance → per-site normalization mandatory |
| 6 | Synthesis | Ranked 7-item technique playbook (plan.md §7g): T1 station-fingerprint conditioning (LOW cost, top lever) → T2 wind-shape → T3 hurdle+calibration → T4 self-training → T5 site-normalized embedding probe → T6 CATFISH-lite fallback → T7 ensemble/TTA. R8 build order in §7h |
| 7 | Docs + backup | hunt_log_r7e.json (10 probes, cum 86); plan.md §6o/§7g/§7h; station-intel §8; HANDOFF banner |

**Decisions**
- D29: R8 modeling priority = T1 (G0/G1/G2 fingerprints + site-bed SNR normalization
  in train_v3_v31) + T2 wind-shape features, judged on background-window-level
  group-split val; proceed to T3–T5 only if val ≥ +0.01.
- D30: Enquiry card extended (Sea Search + Dines/Oceans Research Mossel Bay +
  SAMSA GloNoise); A53 fingerprint wording retained; "Mossel Bay?" added as an
  explicit allowed name.
- D31: Submission plan UNCHANGED — r7_v3_k045 recommended; ρ readout ⇒ k* = ρ.

**Open / blocked-on-user**
- Submit r7_v3_k045 (rec) or r7_v2 → LB ρ readout.
- Send extended enquiry (A53 + Mossel Bay + SAMSA).
- Greenlight R8 build (T1+T2) if wanted.

## R8 — 2026-10-21 — Rainbolt tell-mining: G1 branch quantified (St-Francis-class, margin 8.1/25.7), state-vs-station closed, Mossel Bay dates pinned

**Agent:** Z.ai (main). **Directive:** user R8 ("Rainbolt method" station hunt
+ research remaining gaps/uncertainties).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Tell-mining (scripts/r8_tells.py, r8_tells2.py) | 25-band P20 fingerprints per group/site; within-group GMM/KMeans substructure tests; recalibrated vessel proxies (6/10/14 dB); ID-order run analysis; outputs docs/r8_tells.json + r8_tells2.json |
| 2 | G1 branch | **St-Francis-class CONFIRMED with margins: shape margin 8.1 dB L2 (8.96 vs 17.06), level margin 25.7** ⇒ 08 = exposed south-coast site ~45%, nearest name Mossel Bay (A60) |
| 3 | G0/G2 branches | G0 = Saldanha-class (margin 2.6); G2 = 3-way near-tie = generic harbour class → Table Bay/V&A best pin (A61) |
| 4 | Duplicate/extra-station check | within-group 2-component splits = FLAT level/state shifts (fraction ≥0.968, same tilt) ⇒ weather states, NOT stations ⇒ 3-station theory holds (A62) |
| 5 | Vessel-activity prior | thr10 rates G0 .593 / G1 .509 / G2 .518 = mid-train-range ⇒ no per-group μ shift; global shrink stands; overfit trap closed (A63) |
| 6 | Negative tells logged | ID order 813 runs = interleaved (no batch tell); NaN census = 3 clean fingerprints + 3 stragglers (A59) |
| 7 | Web gaps (7 probes) | Dines PDF blocked (handle 10019.1/132009, bitstream uuid logged for manual DL); Rufford start = 13 Feb 2026 (post-competition); Sea Search page = Mossel Bay THE south-coast PAM site; Oosthuizen 2026 Garden Route zone; Probert-Robben/Langebaan/Hermanus/Zindi = 0 (silence = evidence) |
| 8 | Docs + backup | hunt_log_r8.json (cum 94); plan.md §6p/§7i; station-intel §9; HANDOFF banner |

**Decisions**
- D32: Decision tree locked — G1→08 south coast (~45%, Mossel Bay lead),
  G0→11/12 west coast, G2→11/12 Table Bay/V&A; duplicates 5–8%; all other
  theories dead/weakened per A62.
- D33: No per-group μ adjustment in submissions (A63) — global r7_v3 family
  remains the hedge set.
- D34: Manual user action requested: download dines_marine_2025.pdf (names
  the 3 south-coast array sites — last open name-gap on 08).

**Open / blocked-on-user**
- Submit r7_v3_k045 (rec) or r7_v2 → ρ readout → k* = ρ.
- Download Dines PDF; send A53+Mossel Bay enquiry (Sea Search / SAMSA / SAEON).
- Greenlight R8 build (T1 fingerprints + T2 wind-shape).

---
Task ID: R9-C
Agent: general-purpose (Dines thesis rescue)
Task: find working route to Dines 2025 thesis + 3 south-coast array site names

Work Log:
- Read worklog R7e/R8 (lines 324-385); found stale /data/dines_thesis_text.txt = 162 B nginx 403 stub
- GET /handle/10019.1/132009 (browser UA) -> 200 OK, 459 KB DSpace 7 Angular page; prior "resource not found"/403/404 was transient or wrong-path, handle resolves fine
- Decoded SSR state (<script id="dspace-angular-state">, &q;/&s; entities): item uuid = ba08fdd7-4a00-4367-b6fd-f7dd10e309c6; recorded 00218139-21b4-4e5d-9d6f-98c4ed54d6af is a BITSTREAM uuid (TEXT bundle) not an item uuid -> explains earlier /server/api/core/items/00218139... 404
- Bitstream inventory: PDF b304c9c7-9499-4625-9227-b3742d7f9c81 (ORIGINAL, 6,286,780 B); TEXT 00218139... (100,242 B); thumb cc0058ea...; license c2d8de08...
- /bitstreams/<uuid>/download (UI proxy) -> nginx 429 x2 (rate-limited path; avoid for automation)
- /server/api/core/bitstreams/<uuid>/content (DSpace 7 REST) -> 200 OK: PDF + TEXT both downloaded
- OAI-PMH: /oai/request 403/wrong path; /server/oai/request?verb=GetRecord (browser UA) -> 200 full oai_dc record incl. complete English abstract
- Wayback CDX: web.archive.org unreachable from sandbox (timeout x3) — moot
- OpenAIRE title query 400 (encoding) — moot after acquisition
- PDF sha256 174b3b1c521881d7a309bb00a51e7d79dab6e0034d1a826c115004e98148dbd4 (6,286,780 B, 304 pp); official TEXT bundle + pdftotext extraction saved; docs/intel_r9_dines.md written

Stage Summary:
- PDF ACQUIRED. Dines, S. F. 2025. "Applied passive acoustic monitoring of South Africa's most
  threatened marine mammal, the Indian Ocean humpback dolphin (Sousa plumbea)" PhD, Stellenbosch
  (advisors Measey/Gridley/Elwen, Sea Search). Working route: scholar.sun.ac.za/server/api/core/
  bitstreams/b304c9c7-9499-4625-9227-b3742d7f9c81/content; item page /items/ba08fdd7-4a00-4367-b6fd-f7dd10e309c6
- THE PRIZE — 3 array site names (Ch. 5 SWORD, 120 km, 5 hydrophones, 42 days, 26 Aug-7 Oct 2022):
  Mossel Bay, Buffelsbaai, Plettenberg Bay; moorings M1 MB_Harbour, M3 MB_Diaz, M7 Buffelsbaai,
  M8 Plett_Robberg Point, M9 Plett_Beacon Isle. M1+M7 = 77% of SW detections; Buffelsbaai =
  hottest site (2,070 whistles, single hydrophone, 13 inds) -> new name candidate for station 08
  alongside Mossel Bay. Harbour-adjacent M1 (MB_Harbour) noted for harbour-tinged fingerprint risk
- Bonus: 2021 Mossel Bay 6-mooring array WITH coordinates (Table 4.1): M1 -34.1767/22.14221 (ST500,
  harbour), M2 -34.1703/22.13575 (ST500), M3 -34.1646/22.12037 (ST300), M4 -34.1446/22.1151,
  M5 -34.1546/22.1138, M6 -34.1331/22.11944 (Hartenbos/Kleinbrak end); 19 Mar-5 Apr 2021, 96 kHz
  continuous 10-min files, 8-10 m depth, 2 km spacing; 2022 M1/M3 = redeploys of 2021 M1/M3
- D34 (manual Dines download) CLOSED. Gansbaai: 0 mentions in thesis -> R7e Gansbaai lead stays
  uncorroborated. Abundance: MB 8, Buffelsbaai 19, Plett 22; POPAN 26 (CI 23-30), SECR 23-26

---
Task ID: R9-B
Agent: general-purpose (ruicodex OSINT)
Task: rival dossier — Zenodo deposit, Belgian registry, people, tactical read

Work Log:
- Zenodo: resolved DOI 10.5281/zenodo.23037895 (302→zenodo.org, API 200); record = "VTUAD: An AIS-Auto-Labeled Vessel-Type Underwater Acoustic Dataset Reconstructed from Ocean Networks Canada Archives", v1.3.2, 2026-09-29, CC-BY-4.0, concept DOI 10.5281/zenodo.22274549; creators Yuan/Wang/Li/Chen/Zeng/Liu (WUST + CSSC-LINCOM Wuhan, ORCIDs present)
- Version chain pulled (6): v1.0.0 2026-09-03 (2 files, 255 KB) → v1.1 09-03 (25.8 GB) → v1.2.0 09-15 (36.2 GB) → v1.3.0 09-23 (40.9 GB) → v1.3.1 + v1.3.2 09-29 (63 files, 40.9 GB) — 26-day release cadence, rebuild-from-ONC framing is the deposit's own
- Declared-file cross-check PASS: vtuad_strict_wav_vessel.zip parts 01-03 (3,712,337,699 B reassembled, SHA-256 96564721a917… in README), vtuad_strict_wav_background.zip (926 MB), metadata.csv (166,858 B), registry_anonymized.csv (164,251 B) all exist in v1.3.2; downloaded the 2 CSVs + 8 small docs to data/zenodo_r9/; registry_anonymized.csv SHA-256 matches SHA256SUMS.txt, metadata.csv MD5 matches API
- CSV analysis: 525 rows each; 12 labels (tug 188/cargo 97/passengership 71/bg 38/…); registry anonymization = MMSI→hull_id, 179 MMSIs ↔ 178 hulls (1:1), 509 vessel clips, 22 bg-with-hull (6 hulls), 16 dedicated bg; CTD p1 144.5–149.2 dbar ⇒ hydrophone ~14.5–14.9 m; 32 kHz mono, ICLISTENAF2523 Strait of Georgia, 2016-05-09..2017-05-28, only 33 distinct UTC days, 56.0 h, durations 119–2220 s; ResNet-18 baseline macro-F1 0.2766 (their card); audit pack: 167/525 wrap-around splices, grouping drops first minute
- ONC DOI 10.17616/R3RW43 → re3data r3d100011094 "Oceans 3.0 Data Portal"/ONC — CONFIRMED; license_evidence_v131.md quotes ONC CC-BY-4.0 data policy per stream (hydrophone redistributable; AIS = derived metadata only; CTD = derived averages)
- Registry: Belgian KBO registry hit — Rui Codex = sole proprietorship (natuurlijk persoon), founded 4 Feb 2026, Nacebel 62.100/62.200/63.100/58.290/70.200; KBO/VIES/site-footer all agree; identity details kept in the PRIVATE dossier only (docs/intel_r9_ruicodex.md, not pushed); "2 employees" = UNVERIFIABLE from KBO (probable, LinkedIn-only)
- People: founder identified and verified across site JSON-LD/About/itch.io/Devpost (name in private dossier only); GitHub RuiCodex=0 public repos, RuiCodex-dev=8 company repos, ZERO competition code — confirms GitHub does NOT disclose the project; second member: no footprint outside LinkedIn (UNCONFIRMED); Zindi profile zindi.world/users/ruicodex EXISTS (rank #7060/100k aggregate)
- VTUAD upstream: original = Domingos, Skelton & Santos 2022 IEEE DataPort 10.21227/msg0-ag12 (DOI + title + authors verified; gated access); "rebuilt" = Yuan et al. MDPI preprint 10.20944/preprints202609.0617 (v1 09-08/v2 09-20, six-stage AIS auto-label pipeline, silver-standard labels) + Oct-2026 companion deposits (cross-water benchmark, SimCLR, foundation-model eval, source-free adaptation) — all public
- Blocked: LinkedIn 999, Kaggle reCAPTCHA, companyweb 403, belgiancompanies/northdata/trendstop/efis DNS, northdata.de 429, staatsbladmonitor 404, kbopub name-search JSF wall, DDG 202-throttle after q1, Mojeek timeout, Bing query-mangled, GitHub core API rate-limited (HTML used instead), Zindi LB login-walled
- Deliverable: docs/intel_r9_ruicodex.md (VERIFIED/PROBABLE/UNCONFIRMED sections, per-claim URLs); local data in data/zenodo_r9/; plan.md and submissions untouched

Stage Summary:
- VERIFIED: deposit 23037895 v1.3.2 exists and matches ruicodex's declared file set byte-for-byte on names/sizes/checksums; 525 clips / 178 hulls / 12 classes / 56.0 h / ~14.5–14.9 m icListen SoG / 33 duty days — license CC-BY-4.0 with ONC attribution (re3data r3d100011094 confirmed)
- VERIFIED: Rui Codex = Belgian sole proprietorship, founded 4 Feb 2026 (KBO/VIES-confirmed; personal identifiers in private dossier only); "2 employees" plausible but only LinkedIn-sourced; second member invisible outside LinkedIn
- VERIFIED: original VTUAD = Domingos et al. 2022 IEEE DataPort (gated); rebuild = Yuan et al. 2026 preprint + open Zenodo; both teams now use the SAME data + SAME starter-conversion band power — zero data asymmetry
- TACTICAL: their declared pipeline = strict re-cut vessel+background WAVs → minute deci-decade band power, no calibration, no test-window matching ⇒ auxiliary prior/pretraining usage; lacks site/state features ⇒ our T1 fingerprint conditioning + T2 wind-shape remain the differentiators; only gap to close = download the 4.6 GB strict WAV set (SHA ledgers already captured)
- TACTICAL: rival profile = generalist AI-automation studio (hackathon tempo, solo+1), Zindi aggregate rank #7060, no deep-audio research footprint — expect solid pragmatic pipelines, not novel architectures; #1 position likely won on the same band-power/shrink family we already run
---
Task ID: R9-A
Agent: general-purpose (VTUAD mining)
Task: deep-mine VTUAD + vessel-noise literature/code, sorted critical→medium

Work Log:
- ~36 web probes (arXiv API, Crossref, Semantic Scholar w/ backoff, Zenodo API,
  GitHub API/raw, ar5iv; DDG/Bing/OpenAlex/IEEE-DataPort/preprints.org/grep.app
  bot-walled or out of budget — logged as misses)
- VTUAD identity pinned: original = Domingos 2022a IEEE Access 10.1109/ACCESS.2022.3220265
  (1-s clips, 3 range scenarios, benchmark 84.13% combined); 2026 re-release = Yuan et al.
  preprints 10.20944/preprints202609.0617 (Zenodo 23037895: 525 clips, 133,784 log-mel
  segments, MMSI+CTD covariates, cut-rule/wraparound audits); pipeline code =
  lucascesarfd/onc_dataset + mominali12/vtuad_personal; SOTA = Jotels/CATFISH
- CATFISH fulltext+code mined: ablation Table 2 (filters alone 91.59 → +CTDSV 96.32 →
  +attention 96.23 → both 96.63), Δ-band diagnostic (discriminative bands narrow 0–60→0–10
  with range), LogTBN median-filter dual-channel config, PCEN option (s=.04 α=.96 δ=2 r=.5)
- Yuan 2026 five-paper series found via Zenodo/Crossref: UDA four-corpus benchmark
  (CORAL>MMD, MMD negative transfer −0.190), SFUDA benchmark (AdaBN suffices, TENT
  collapses, post-hoc rejection fails), cross-archive direct-transfer (all 12 directions
  collapse; sqrt weights > inverse), SimCLR in-corpus SSL (encodes recording ID — probe
  diagnostic), frozen-FM zero-label transfer (BEATs best on VTUAD; source-validation
  selection rule)
- Citation-graph sweep (S2 on Domingos 2022a, 35 citers): MFAV JASA 2026 arctic ship
  detection (FAV statistic, +22% small boats, open tool), sea-state-7 generalization
  study, UniqueShip leakage audit (random splits +10–48 pp; vessel diversity ≫ duration),
  sonar texture metrics (code), CAM++ change-point features, Oceanship 121 h dataset
- Wind track: Ragland & Abadi 2025 (piecewise log-linear AN-wind), Cho 2021 Ocean Eng,
  Kalman wind tracking 2017, Rogers 2024 (wave params <0.3 dB gain = skip swell proxies)
- Calibration track: ZIB regression (two-head = ZOIB), weighted conformal under
  covariate shift, mixture-consistency projection → per-station closed-form
  projection-share; rejected: MMD, TENT/entropy-min TTA, MSP/Energy/OpenMax gates,
  inverse-frequency weighting, in-corpus SSL shortcut
- Deliverable: docs/intel_r9_vtuad.md (24 findings, sorted CRITICAL 6 / MEDIUM 11 / LOW 7,
  each with URL, technique, fit, grade + build-order delta to plan §7h)

Stage Summary:
- F1 CORAL station alignment (closed-form, label-free; MMD documented harmful) — CRITICAL
- F2 AdaBN-analogue: test-station robust re-standardization of frozen features — CRITICAL
- F3+F4 LogTBN median-detrend dual channels + PCEN on band-power series (CATFISH/LEAF) — CRITICAL
- F5 UniqueShip: vessel-ID-disjoint validation mandatory; diversity>duration in factory — CRITICAL
- F6 low bands survive at far range → SNR-gated band weighting (CATFISH Δ-diagnostic) — CRITICAL
- F7/F13 MFAV dispersion features + mixture-consistency projection share; F11/F12 per-window
  adaptive shrinkage (ZOIB / weighted conformal) replace single global k — MEDIUM

---

## R9 — 2026-10-22 — Dines thesis acquired (08 slate closed), ruicodex dossier, VTUAD steals, R8 T1+T2 VALIDATED (D29 gate PASS)

**Agent:** Z.ai (main) + 3 parallel research agents (R9-A VTUAD mining, R9-B ruicodex OSINT, R9-C thesis rescue). **Directive:** user R9 (place pin; greenlight R8 T1+T2; mine VTUAD papers/code critical→medium; ruicodex intel; thesis link broken).

**Done**
| # | Task | Outcome |
|---|---|---|
| 1 | Pin verified | r7_v3_k045 sha 98775aed ✓ 1,500 rows ✓ → staged download/submission_r7_v3_k045_PIN.csv |
| 2 | R9-C thesis rescue | **PDF ACQUIRED** — 404 root cause = wrong uuid (TEXT bundle); item ba08fdd7-4a00-4367-b6fd-f7dd10e309c6 + bitstream b304c9c7 (docs/intel_r9_dines.md); data/dines_marine_2025.pdf 304 pp |
| 3 | A66 | SWORD array 5 moorings named: Mossel Bay Harbour/Diaz, **Buffelsbaai**, Plett Robberg Pt/Beacon Isle (Aug–Oct 2022) + 2021 M1–M6 coords ⇒ 08 slate closed to 4 exposed candidates |
| 4 | R9-B ruicodex | Zenodo 23037895 verified (Yuan et al. AIS-auto-labeled rebuild, 525 clips/178 hulls, CC-BY-4.0); Rui Codex = BE sole prop (identity in private dossier only); **zero data asymmetry** (docs/intel_r9_ruicodex.md, 80 probes) |
| 5 | R9-A VTUAD harvest | 4 CRITICAL: CORAL alignment, AdaBN re-standardization, PCEN/LogTBN (CATFISH code), vessel-ID-disjoint validation law (docs/intel_r9_vtuad.md, ~36 probes) |
| 6 | Data recovery | refs/bg_refs parquets re-pulled from misc-notes-data v2 (49,450+13,325 rows A12-exact); symlinks fixed |
| 7 | R8 build | scripts/r8_t1t2_build.py + r8_followup.py: D20 recipe (sub-interval + H_A/H_C + bg-group split + clip holdout); 15k bg pool, 39% calm; 6k train/1.5k cal/2.2k val pools incl. 4 class-matched pools |
| 8 | R8 result | **LGBM+T1T2 beats base everywhere; G1-class 0.0661→0.0507 (+0.0154) = D29 PASS**; T1 = 31.2% importance; T2 = 8.6% |
| 9 | A69 negative result | wind gate inverted: FA bumps LF-rich (AUC 0.92) but gate moves calm-val only −0.0008 — FA is not the E5 bottleneck |
| 10 | A70 | centered-shape distances confirm decision tree: G0→A_west 1.79, G1→B_south 1.90, G2→C_harbour 1.80 |
| 11 | Docs + backup | plan.md §6q/§7j/§7k; station-intel §10; HANDOFF banner; reports merged r8_t1t2_report.json; test vectors r8_test_diag.npz |

**Decisions**
- D35: R8 track = LGBM+T1T2 (recipe-correct val 0.039–0.051 beats E5 0.10–0.42 in-domain); E5 stays the calibration anchor + fallback.
- D36: r8 candidate submission ONLY after r7_v3_k045 ρ readout; moment-pin via r7_v2 power-map machinery; Spearman-check vs r7_v2 first.
- D37: T5 = AdaBN+CORAL per test group = next build (no training loop, stackable).

**Open / blocked-on-user**
- Submit r7_v3_k045 → ρ readout → k* = ρ.
- Enquiry (A66 slate) to Sea Search/Dines + SAMSA-GloNoise + SAEON.
- Optional: 4.6 GB VTUAD strict-WAV re-download for T4 self-training (SHA ledgers already in data/zenodo_r9/).
