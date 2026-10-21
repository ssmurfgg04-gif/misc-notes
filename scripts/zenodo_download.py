#!/usr/bin/env python3
"""R4 data re-acquisition: sequential Zenodo download queue (VTUAD v1.3.2, DOI 10.5281/zenodo.23037895).
Disk budget: 9.3 GB. One zip at a time; curl -C - resume; stops before passengership if disk tight.
QA/metadata files fetched first (tiny). Log to data/zenodo/download.log
"""
import os, subprocess, sys, time

BASE = "https://zenodo.org/api/records/23037895/files"
DIR = "/home/z/my-project/data/zenodo"
LOG = os.path.join(DIR, "download.log")

# Tiny QA/metadata files first (provenance-critical, per brief A8-A10)
QA_FILES = [
    "clip_acoustic_stats.csv",
    "metadata.csv",
    "dataset_card.md",
    "SHA256SUMS.txt",
    "v131_supplementary_SHA256SUMS.txt",
    "strict_interval_wav_SHA256SUMS.txt",
    "manifest_train.csv",
    "manifest_val.csv",
    "manifest_test.csv",
    "zenodo_vtuad_v1.2.0.zip",
    "vtuad_wraparound_splice_clips_v1_README.md",
    "interval_audit_readme.md",
    "README_vtuad_strict_wav_vessel_parts.txt",
    "cut_rule_simulation_525clips.csv",
    "grouping_defect_3day_audit.csv",
    "wrap_feature_recompute_check.csv",
    "strict_adjacency_intervals_3day_sample.csv",
    "mmsi_stability_20160908.csv",
    "registry_verification_sample30.csv",
]

# Big zips in priority order (small vessel types first, then background, then mid-size)
ZIP_QUEUE = [
    ("vtuad_wav_pilotvessel.zip", 69_120_288),
    ("vtuad_wav_rescue.zip", 220_000_000),
    ("vtuad_wav_tanker.zip", 250_000_000),
    ("vtuad_wav_sailing.zip", 260_000_000),
    ("vtuad_wav_dredger.zip", 330_241_094),
    ("vtuad_strict_wav_background.zip", 926_037_631),
    ("vtuad_wav_pleasurecraft.zip", 1_300_000_000),
    ("vtuad_wav_fishing.zip", 1_630_000_000),
    ("vtuad_wav_other.zip", 1_630_000_000),
    ("vtuad_wav_passengership.zip", 2_520_000_000),  # only if disk allows
]

def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as fh:
        fh.write(line + "\n")

def disk_free_gb():
    st = os.statvfs(DIR)
    return st.f_bavail * st.f_bsize / 1e9

def fetch(fname, expected=None):
    url = f"{BASE}/{fname}/content"
    out = os.path.join(DIR, fname)
    if expected and os.path.exists(out) and os.path.getsize(out) >= expected * 0.999:
        log(f"SKIP {fname} (already complete)")
        return True
    log(f"GET  {fname} free={disk_free_gb():.1f}GB")
    # curl with resume, retry loop
    for attempt in range(8):
        r = subprocess.run(["curl", "-sL", "-C", "-", "--max-time", "14400",
                            "--retry", "3", url, "-o", out])
        if r.returncode == 0:
            sz = os.path.getsize(out)
            if expected and sz < expected * 0.999:
                log(f"  short read {sz}/{expected}, retrying")
                time.sleep(10)
                continue
            log(f"DONE {fname} {sz/1e6:.0f}MB")
            return True
        log(f"  curl rc={r.returncode}, retry in 15s")
        time.sleep(15)
    log(f"FAIL {fname}")
    return False

def main():
    os.makedirs(DIR, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("qa", "all"):
        for f in QA_FILES:
            fetch(f)
    if which in ("zips", "all"):
        for fname, sz in ZIP_QUEUE:
            if fname == "vtuad_wav_passengership.zip" and disk_free_gb() < sz/1e9 + 4.0:
                log(f"SKIP {fname} (insufficient disk: {disk_free_gb():.1f}GB)")
                continue
            ok = fetch(fname, sz)
            if not ok and fname != "vtuad_wav_passengership.zip":
                log("Aborting queue on hard failure")
                sys.exit(1)
    log("QUEUE COMPLETE")

if __name__ == "__main__":
    main()
