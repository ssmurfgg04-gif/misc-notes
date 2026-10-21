#!/bin/bash
# R4 resilient fetcher: one call = up to 570s of progress, curl -C - resume.
# Queue: QA files -> strict vessel parts 1-3 -> strict background. Safe to re-invoke.
BASE="https://zenodo.org/api/records/23037895/files"
DIR="/home/z/my-project/data/zenodo"
LOG="$DIR/fetch.log"
mkdir -p "$DIR"
log(){ echo "[$(date +%H:%M:%S)] $*" >> "$LOG"; }

QA=(clip_acoustic_stats.csv metadata.csv dataset_card.md SHA256SUMS.txt \
v131_supplementary_SHA256SUMS.txt strict_interval_wav_SHA256SUMS.txt \
manifest_train.csv manifest_val.csv manifest_test.csv zenodo_vtuad_v1.2.0.zip \
vtuad_wraparound_splice_clips_v1_README.md vtuad_wraparound_splice_clips_v1.csv \
interval_audit_readme.md README_vtuad_strict_wav_vessel_parts.txt \
cut_rule_simulation_525clips.csv grouping_defect_3day_audit.csv \
wrap_feature_recompute_check.csv strict_adjacency_intervals_3day_sample.csv \
mmsi_stability_20160908.csv registry_verification_sample30.csv \
registry_anonymized.csv static_field_conflicts.csv static_field_fill_audit.csv \
static_audit_README.md license_evidence_v131.md \
registry_verification_sample30_README.md interval_uid_closure_v1deployment.csv)

BIG=(vtuad_strict_wav_vessel.zip.part01 vtuad_strict_wav_vessel.zip.part02 \
vtuad_strict_wav_vessel.zip.part03 vtuad_strict_wav_background.zip)

START=$(date +%s)
for f in "${QA[@]}" "${BIG[@]}"; do
  # expected size check via SHA256SUMS or known sizes for big parts
  case "$f" in
    vtuad_strict_wav_vessel.zip.part01|vtuad_strict_wav_vessel.zip.part02) EXP=1237445900;;
    vtuad_strict_wav_vessel.zip.part03) EXP=1237445899;;
    vtuad_strict_wav_background.zip) EXP=926037631;;
    *) EXP=0;;
  esac
  if [ -f "$DIR/$f" ] && [ "$(stat -c%s "$DIR/$f")" -gt 0 ]; then
    if [ "$EXP" -eq 0 ] || [ "$(stat -c%s "$DIR/$f")" -ge "$EXP" ]; then
      continue
    fi
  fi
  log "GET $f (have $(stat -c%s "$DIR/$f" 2>/dev/null || echo 0) bytes, free $(df -BG --output=avail "$DIR" | tail -1 | tr -d 'G'))"
  curl -sL -C - --max-time 470 "$BASE/$f/content" -o "$DIR/$f"
  rc=$?
  sz=$(stat -c%s "$DIR/$f" 2>/dev/null || echo 0)
  log "  rc=$rc size=$sz"
  if [ "$EXP" -gt 0 ] && [ "$sz" -ge "$EXP" ]; then log "  COMPLETE $f"; fi
  NOW=$(date +%s)
  if [ $((NOW-START)) -gt 480 ]; then log "TIMEBOX reached"; exit 0; fi
done
log "ALL FETCHED"
