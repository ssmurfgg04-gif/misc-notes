# HANDOFF.md — read this first (next-AI pickup, updated every round)

> Last updated: R1, 2026-10-20. Repo: `ssmurfgg04-gif/misc-notes` (public, bland name).
> Companion: `plan.md` (strategy), `worklog.md` (round logs), `docs/` (evidence).

## Mission (1 line)
Zindi "Underwater Vessel Noise Challenge" (close **13 Dec 26**): predict
`share_added_vessel` ∈ [0,1] for 1,500 test windows; scored metric 1−RMSE;
we win with a leakage-clean synthetic-mixture pipeline + real vessel references
+ honest validation, plus a write-up prize attempt.

## State after R1 (research & planning) — DONE
- [x] Official SA package acquired + **checksums verified** (local
      `/home/z/my-project/data/`, mirror via Kaggle, all SHA256SUMS OK)
- [x] 10 sites / 1.7M rows profiled → `docs/station-intel.md`
- [x] Vessel references inventoried → `docs/vessels.md` (VTUAD metadata local)
- [x] Corpus status board + licenses → `docs/data-links.md`
- [x] Compute: GH Actions sharded template live (`shard-compute.yml`), Kaggle
      token verified (Bearer REST works; CLI quirks in `docs/runner-playbook.md`)
- [x] cortexm facts db seeded (see §facts-db)
- [ ] **blocked-on-user**: Zindi credentials (for submissions + direct downloads
      + discussion posts), OK to create private `misc-notes-data` repo for the
      ~90 MB data backup asset

## Environment map (this machine)
| Path | What |
|---|---|
| `/home/z/my-project/repo/` | git root → `misc-notes` (code + docs; NO data) |
| `/home/z/my-project/data/South_African_Real_Acoustics/` | official package (verified) |
| `/home/z/my-project/data/Test.csv` | the 1,500 test windows |
| `/home/z/my-project/data/vtuad_{metadata,registry}.csv` | VTUAD clip/hull registry |
| `/home/z/my-project/data/profile/` | profile.json + summary md (R1) |
| `/home/z/my-project/scripts/` | working scripts (profile_sa_data.py, profile_vtuad.py) |
| `/home/z/my-project/workspace/context-m/` | cloned cortexm repo (memory solution) |
| python | `/home/z/.venv` (3.12) — pandas/numpy/pyarrow installed |

## Hard-won facts (do not rediscover)
1. Test missingness: m01 41.6% / m15 6.7% / m02–13 ≈ 0 — availability masks are features.
2. Richards Bay = 58% of rows; Bird Island p50 = 94.4 dB (seals); Sea Point = 3 days only.
3. Recorder sample rates vary 12–96 kHz ⇒ 12 kHz units cannot support top bands.
4. LB 20 Oct: #1 = 0.8720; pack = 0.816–0.824 ≈ constant-baseline quality.
5. Zero public competition code on GitHub (swept R1) — we are first movers.
6. Kaggle CLI 2.2.4 env-token quirk → use Bearer REST; token also at
   `~/.kaggle/access_token`.
7. GH runners: public repo = free unlimited; 6 h/job cap; 4c/16 GB; shard + aggregate.

## Rules rails (violating these = disqualification)
Test = inference-only. No LB probing. No challenge-data redistribution (public
repo carries code/docs only). External data must be declared. Raw [0,1] outputs,
no rounding. AIS weak labels are confidence-weighted, never ground truth.

## First tasks for R2 (generator v1 + tournament)
1. `src/tol_convert.py` — VTUAD 32 kHz WAV → 25-band one-minute TOL
   representation (Welch → 1/3-octave base-10 aggregation onto exact centres
   31.6–7943.3 Hz). Match the starter notebook's column layout exactly.
2. `src/generator.py` v1 — inject real VTUAD passages into real SA background
   periods: linear-energy add, `y = A/T` on observed cells, ~35% zeros,
   positive mass log-uniform [1e-4, 0.6], passage placement uniform over window,
   3 scenario variants. Splits: group by (background period, hull_id).
3. `src/features.py` — tabular set per plan §3.3c (observed-cells-only aggregations,
   band ratios, excess energy, masks, spectral shape stats).
4. `src/tournament.py` — constant / energy-heuristic / LightGBM; RMSE by
   scenario × split. Output `output/tournament_v1.json` + table in worklog R2.
5. Commit + push; run one 8-shard `shard-compute` dispatch as smoke test.

## cortexm facts db (structured memory; markdown stays source of truth)
- Repo cloned at `/home/z/my-project/workspace/context-m`; pip install `cortexm`.
- Seeded facts: site stats, missingness fingerprints, LB snapshot, decisions
  D1–D5, license statuses. Query pattern:
  `python -c "from cortexm import Memory; m=Memory('/home/z/my-project/memory.db'); print(m.search('site missingness', user_id='uvn'))"`
- Keep `user_id="uvn"` (underwater-vessel-noise) namespace.

## Open questions for the user
1. Zindi account access — needed for submission upload + discussion-board
   declarations (external-data rule).
2. Approve private `misc-notes-data` (data backup release asset)?
3. Approve private Kaggle dataset for GPU notebooks, or fetch data in-notebook
   from the private GitHub release?
4. Written confirmation from Zindi re: 200-vs-300 submissions discrepancy (plan §0).
