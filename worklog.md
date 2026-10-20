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
