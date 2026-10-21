# VTUAD (rebuild) — Interval & audio audit pack (v1.3.1 supplementary)

This pack documents the independent code/data-level audit of the released construction
pipeline carried out on 2026-09-29, together with the per-seed benchmark evidence.
It accompanies the Usage Notes limitations (viii) and (ix) of the descriptor revision.
Nothing in this pack changes the released WAV audio, metadata registry, feature library
or frozen split; the v1 window raw AIS streams survive only for 2016-09-02/08/10, so
message-level re-audits are bounded to those days.

## Files

| File | Content | Basis |
|---|---|---|
| interval_uid_closure_v1deployment.csv | Per-spell disposition ledger for all 541 candidate single-vessel spells of the 4,000 m tier (v1 deployment): retained identical / trimmed / split / fully ceded, hours kept, spawn count, destination tier | 06a_scenario_intervals tables + metadata.csv |
| grouping_defect_3day_audit.csv | Published equal-difference grouping vs strict-adjacency regrouping, per radius per surviving raw-AIS day: interval counts, hours, bridged-gap cases | Independent single-day rebuild of the pipeline (parse → clean → distance → interpolate → minute scan) on 2016-09-02/08/10 |
| strict_adjacency_intervals_3day_sample.csv | Corrected (strict-adjacency, first minute retained) interval tables for the 3 surviving days, all ten radius tiers, vessel and background. Sample only: full-window regeneration is part of the v2 re-run because the raw AIS streams of the remaining days no longer exist | Same rebuild chain |
| mmsi_stability_20160908.csv | Target-identity audit of the 13 released clips of 2016-09-08 (the only day where raw AIS and released clips coexist): per-interval within-radius MMSI set is constant and equals the registry MMSI (13/13) | Rebuilt 20 s interpolated track table vs metadata.csv |
| cut_rule_simulation_525clips.csv | Re-simulation of split_and_save_wav for all 525 clips against the 1,020 archive WAVs: predicted duration matches metadata.csv exactly for 525/525; 167 clips are single-source wrap-around splices (duration = span + 300 s), 17 deviate by −1..+2 s | 07a_needed_wav_files + metadata.csv |
| wrap_feature_recompute_check.csv | Independent re-computation of log-mel segments from reconstructed wrap-around clips (plus non-wrap controls) against the released .npy files: segment counts match exactly, per-segment correlation ≥ 0.99996, mean |Δ| ≤ 0.07 dB; the build-environment figure max |Δ| = 0.0002 dB reflects resampler implementation differences across librosa versions | 07a WAVs + vtuad_features_test.zip |
| clip_acoustic_stats.csv | Per-clip acoustic-quality statistics for all 525 clips (RMS/peak, spectral centroid, band levels 20–200 Hz / 200 Hz–1 kHz / 1–8 kHz, 1 s frame-RMS quantiles, log-mel spectral flux) plus SOG statistics (mean/median/max, contributing report counts) for the 13 clips of 2016-09-08 | Released WAVs + rebuilt track table |
| per_seed_test_predictions_s42-46.csv | Per-segment test predictions for all five seeds (42–46): 5 × 18,202 rows with segment_uid, clip_uid, label, group, offset, y_true, y_pred, correct | results/paper7_baseline_stats/preds joined to manifest_test.csv (one-to-one) |
| vtuad_v120_s4{2..6}_test_probs.npz | Per-segment softmax probability arrays behind the above predictions (5 files) | Same |
| rev1_paired_bootstrap_s42-46.json | Clip-clustered paired bootstrap of the reference baseline: seeds 42–46, B = 2,000 shared cluster resamples over 76 test recordings, point estimates and 95% percentile CIs for segment/clip-level accuracy and macro-F1, with guard tolerances | results/paper7_baseline_stats |

## Audit conclusions (summary)

1. The 541 → 511 → 509/525 counting chain closes exactly; the net −30-spell reduction decomposes into 110 spells fully ceded to smaller-radius tiers (12.7 h), 40.4 h edge-trimming and 75 spells split into 155 sub-intervals; two 2-minute remnants vanish below the effective duration floor.
2. The released grouping implementation drops the first minute of every run (effective floors 3/31 min), can bridge constant-step gaps (one instance found, in the unreleased 3,000 m tier), and does not test MMSI continuity (no identity switch observed in the 13 auditable clips).
3. Wrap-around splicing affects exactly the 167 single-source clips; released features reproduce the released audio segment for segment.
