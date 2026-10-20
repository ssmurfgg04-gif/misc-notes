# data-links.md — verified data sources (R1 hunt, 2026-10-20)

All links verified live on 2026-10-20. License status is part of the table —
do not use unverified sources in any submitted artifact.

## Official challenge (Zindi)
| File | Size | Notes |
|---|---|---|
| South_African_Real_Acoustics.zip | 90.5 MB | 10 site parquets + stations + recorders + dictionary + SHA256SUMS |
| Test.csv | 2.7 MB | 1,500 × (ID + 375) |
| sample_submission.csv | 48 KB | ID, share_added_vessel, score_added_vessel |
| maritime_starter_notebook.ipynb | 10.5 KB | loading + constant baseline |
| Page | zindi.world/competitions/french-embassy-underwater-vessel-noise-challenge | needs login for file downloads |

**Acquired copy:** local `/home/z/my-project/data/` via Kaggle mirror
`renjistarfall/underwater-vessel-noise-private` (uploaded 2026-10-19, 12 downloads,
`isPrivate: false`) — **all official SHA256SUMS verify OK** ⇒ byte-identical.
TODO(user): still cross-check one checksum against your own Zindi download for
full provenance.

## External corpora — status board
| Corpus | Link | What | Size | License | Status |
|---|---|---|---|---|---|
| VTUAD (rebuilt) v1.3.2 | zenodo.org/records/23037895 | 525 clips / 56 h / 32 kHz mono / 11 vessel classes + bg; strict-interval re-cut; hull registry | ~25 GB WAV; metadata.csv + registry (166 KB) | CC-BY-4.0 | ✅ metadata downloaded; WAV download next round (per-class zips; tug 8.7 GB is largest) |
| UniqueShip / MARINA | uniqueshipdata.org | 4,218 vessels / 3,437 h / 12 classes; vessel-ID-split benchmark | subsets: 12class-5h **17.8 GB zipped**, 5class-balanced 64.8 GB, full 646 GB | CC-BY-4.0 (ONC) | ✅ inventoried; download R4 (Google Drive 10 GB chunks, rclone) |
| HearMyShip | hearmyship.fer.hr | 1,148 small vessels <55 m; SPL at CPA; speed/size metadata | ~? GB (portal) | paper CC-BY; **dataset "all rights reserved"** | ⚠️ registration + license confirm required |
| DeepShip | github.com/irfankamboh/DeepShip | 265 ships / 47 h / 4 classes (tug, passenger, cargo, tanker) | 47 h | research-only | ⚠️ request form |
| ShipsEar | (UPV, Spain) | 90 ships / 11 classes | ~2 GB | research-only; NOT on organiser allowlist | ❌ skip (use ONC-derived instead) |
| ONC archive | data.oceannetworks.ca | raw hydrophone archives (BC, Canada) | huge | ONC data policy | ⏸ optional; VTUAD/UniqueShip already ONC-derived — API needs free token |
| Wittekind source model | gist.github.com/dbetchkal/093c08f9bde266e78ee158c5bf3f2d2f | physics vessel source-level model (L1 cavitation LF, L2 cavitation HF, L3 machinery) from speed/displacement/block coeff | code gist | public | ✅ captured in docs/vessels.md |

## Overlap warning
VTUAD and UniqueShip are both ONC-derived (Strait of Georgia / BC). Before
mixing: dedupe on hull identity + UTC overlap. UniqueShip's headline result is
that random splits inflate accuracy — we adopt their split discipline, not their task.

## AIS (weak labels) — candidates to evaluate in R3
| Source | Access | Note |
|---|---|---|
| EMSA (EU) | registration, research | no SA coverage guaranteed |
| Global Fishing Watch API | free token, CC-BY-NC | fishing fleet only but global incl. SA; good clock discipline |
| MarineTraffic / VesselFinder | commercial/free tiers | snapshot exports need license check |
| NOAA/BOEM style archives | US waters only | not useful for SA |
**Clock rule from DATA_DICTIONARY:** acoustic `t` = export clock, tz-unverified;
validate alignment on training data before any AIS join.

## Local paths (this machine)
- SA package: `/home/z/my-project/data/South_African_Real_Acoustics/`
- Test.csv: `/home/z/my-project/data/Test.csv`
- VTUAD metadata: `/home/z/my-project/data/vtuad_{metadata,registry}.csv`
- Profiles: `/home/z/my-project/data/profile/`
