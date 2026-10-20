#!/usr/bin/env python3
"""VTUAD -> TOL reference library ingest.

Downloads (or reads local) VTUAD v1.3.2 strict-interval archives, converts every
clip to minute-level 25-band linear power via the documented organiser conversion
(tol_convert.minute_band_power), and writes a long-format parquet:

  refs.parquet: clip_uid, kind(vessel|background), label, hull_id, length_m, beam_m,
                minute_idx(1..N), band(0..24), power (linear mean-square)
  refs_meta.parquet: one row per clip (duration, n_minutes, class...)

Usage:
  python vtuad_ingest.py --meta /path/vtuad_metadata.csv --out out_dir \
      [--vessel_zip parts_dir/vtuad_strict_wav_vessel.zip] \
      [--background_zip parts_dir/vtuad_strict_wav_background.zip] \
      [--max_clips N] [--local_only]
If --local_only, fails when zips absent (used on runners where files are staged first).
"""
import argparse, io, json, os, sys, zipfile
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tol_convert import minute_band_power

ZENODO = "https://zenodo.org/records/23037895/files/{}?download=1"
PARTS = ["vtuad_strict_wav_vessel.zip.part01", "vtuad_strict_wav_vessel.zip.part02",
         "vtuad_strict_wav_vessel.zip.part03"]
BG = "vtuad_strict_wav_background.zip"


def ensure_zip(parts_dir: str, which: str, do_download: bool) -> str:
    """Return path to a ready zip. Vessel zip is concatenated from 3 parts."""
    vessel_out = os.path.join(parts_dir, "vtuad_strict_wav_vessel.zip")
    if which == "vessel":
        if os.path.exists(vessel_out):
            return vessel_out
        if do_download:
            for p in PARTS:
                dest = os.path.join(parts_dir, p)
                if not os.path.exists(dest) or os.path.getsize(dest) < 1_000_000_000:
                    print("downloading", p, flush=True)
                    os.system(f'curl -sL --retry 5 --retry-delay 10 -C - "{ZENODO.format(p)}" -o "{dest}"')
            print("concatenating parts", flush=True)
            with open(vessel_out, "wb") as out:
                for p in PARTS:
                    with open(os.path.join(parts_dir, p), "rb") as fh:
                        while True:
                            chunk = fh.read(1 << 24)
                            if not chunk:
                                break
                            out.write(chunk)
        return vessel_out
    else:
        dest = os.path.join(parts_dir, BG)
        if os.path.exists(dest):
            return dest
        if do_download:
            print("downloading", BG, flush=True)
            os.system(f'curl -sL --retry 5 --retry-delay 10 -C - "{ZENODO.format(BG)}" -o "{dest}"')
        return dest


def convert_zip(zip_path: str, kind: str, meta: pd.DataFrame, max_clips: int | None):
    """Stream a zip of WAVs -> (rows list, meta rows list). WAVs read from memory per member."""
    rows, mrows = [], []
    registry = meta.set_index("clip_uid") if meta is not None else None
    with zipfile.ZipFile(zip_path) as z:
        members = [m for m in z.namelist() if m.lower().endswith(".wav")]
        if max_clips:
            members = members[:max_clips]
        print(f"{kind}: {len(members)} wav members", flush=True)
        for mi, m in enumerate(members):
            try:
                clip_uid = os.path.splitext(os.path.basename(m))[0]
                with z.open(m) as fh:
                    data = fh.read()
                import scipy.io.wavfile as wav
                sr, x = wav.read(io.BytesIO(data))
                if x.ndim > 1:
                    x = x.mean(axis=1)
                if x.dtype != np.float64:
                    x = x.astype(np.float64) / max(1.0, float(np.iinfo(x.dtype).max if x.dtype.kind in "iu" else 1.0))
                pw = minute_band_power(x, float(sr))          # (minutes,25)
                d = pw.shape[0]
                rec = {"clip_uid": clip_uid, "kind": kind, "minutes": int(d), "sample_rate": int(sr)}
                if registry is not None and clip_uid in registry.index:
                    r = registry.loc[clip_uid]
                    rec.update({"label": str(r.get("label", "")),
                                "hull_id": str(r.get("hull_id", "")) if "hull_id" in registry.columns else "",
                                "length_m": float(r["length"]) if pd.notna(r.get("length")) else np.nan,
                                "beam_m": float(r["beam"]) if pd.notna(r.get("beam")) else np.nan})
                mrows.append(rec)
                mm, bb = np.meshgrid(np.arange(1, d + 1), np.arange(25), indexing="ij")
                rows.append(pd.DataFrame({
                    "clip_uid": clip_uid, "kind": kind,
                    "minute_idx": mm.ravel().astype(np.int16),
                    "band": bb.ravel().astype(np.int8),
                    "power": pw.ravel().astype(np.float32)}))
                if mi % 50 == 0:
                    print(f"  {mi}/{len(members)}", flush=True)
            except Exception as e:  # skip bad members, keep going
                print("  skip", m, "->", repr(e)[:120], flush=True)
    return pd.concat(rows, ignore_index=True), pd.DataFrame(mrows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--meta", default="")
    ap.add_argument("--parts_dir", default="parts")
    ap.add_argument("--out", default="output")
    ap.add_argument("--which", choices=["vessel", "background", "both"], default="both")
    ap.add_argument("--max_clips", type=int, default=0)
    ap.add_argument("--download", action="store_true", help="download from Zenodo if zips missing")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(a.parts_dir, exist_ok=True)
    meta = pd.read_csv(a.meta) if a.meta and os.path.exists(a.meta) else None
    if a.download and meta is None:
        # metadata is small; fetch it too
        p = os.path.join(a.parts_dir, "vtuad_metadata.csv")
        if not os.path.exists(p):
            os.system(f'curl -sL --retry 3 "{ZENODO.format("metadata.csv")}" -o "{p}"')
        meta = pd.read_csv(p)
    max_clips = a.max_clips or None
    all_rows, all_meta = [], []
    targets = []
    if a.which in ("vessel", "both"):
        targets.append(("vessel", ensure_zip(a.parts_dir, "vessel", a.download)))
    if a.which in ("background", "both"):
        targets.append(("background", ensure_zip(a.parts_dir, "background", a.download)))
    for kind, zp in targets:
        if not os.path.exists(zp) or os.path.getsize(zp) < 10_000_000:
            print(f"missing zip for {kind}: {zp}", flush=True)
            sys.exit(2)
        rows, mrows = convert_zip(zp, kind, meta, max_clips)
        all_rows.append(rows); all_meta.append(mrows)
    refs = pd.concat(all_rows, ignore_index=True)
    refs_meta = pd.concat(all_meta, ignore_index=True)
    refs.to_parquet(os.path.join(a.out, "refs.parquet"), index=False)
    refs_meta.to_parquet(os.path.join(a.out, "refs_meta.parquet"), index=False)
    print("DONE", refs.shape, refs_meta.shape, flush=True)


if __name__ == "__main__":
    main()
