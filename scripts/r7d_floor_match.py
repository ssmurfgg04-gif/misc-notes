#!/usr/bin/env python3
"""r7d_floor_match.py — identify each test availability-group's station via its
QUIET-BED noise floor (shape + absolute level) vs the 10 train sites.

Logic:
  - planted vessel passages distort spectra -> use only the quietest windows
  - per group: bed = lowest-total-level 20% of windows
  - bed descriptors: absolute band levels (25) + tilt + share; compare to
    train per-site P10 floor levels (same band grid) + shape space
  - ALSO absolute-level comparison (train/test dB conventions sanity-checked)
"""
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq

BASE = "/home/z/my-project/data/sa_package/South_African_Real_Acoustics"
BANDS = ["31.6", "39.8", "50.1", "63.1", "79.4", "100", "125.9", "158.5", "199.5",
         "251.2", "316.2", "398.1", "501.2", "631", "794.3", "1000", "1258.9",
         "1584.9", "1995.3", "2511.9", "3162.3", "3981.1", "5011.9", "6309.6", "7943.3"]
TOL = [f"TOL_{b}" for b in BANDS]
LF = np.log10(10.0 ** (1.5 + 0.1 * np.arange(25)))


def site_floors():
    floors, levels = {}, {}
    import glob, os
    for path in sorted(glob.glob(f"{BASE}/acoustics/*.parquet")):
        site = os.path.basename(path).replace(".parquet", "")
        df = pq.read_table(path, columns=TOL).to_pandas()
        db = df[TOL].to_numpy(dtype=float)
        db[db <= 0] = np.nan
        fin = np.isfinite(db).sum(axis=1) >= 10
        db = db[fin]
        floors[site] = np.nanpercentile(db, 10, axis=0)          # (25,)
        # also quiet-window descriptor distribution: quietest 20% rows
        tot = np.nanmean(10.0 ** (db / 10.0), axis=1)
        q = db[tot <= np.nanpercentile(tot, 20)]
        levels[site] = {"floor": np.nanpercentile(db, 10, axis=0).tolist(),
                        "bed_mean": np.nanmean(q, axis=0).tolist(),
                        "bed_tilt": None, "n_rows": len(db), "n_bed": len(q)}
        A = np.stack([np.ones(25), LF], axis=1)
        ok = np.isfinite(q).sum(axis=1) >= 10
        coef, *_ = np.linalg.lstsq(A, q[ok].T, rcond=None)
        levels[site]["bed_tilt"] = float(np.mean(coef[1]))
    return floors, levels


def main():
    floors, levels = site_floors()
    sites = sorted(floors)
    t = pd.read_csv("/home/z/my-project/data/Test.csv")
    cols = list(t.columns[1:])
    X = t[cols].to_numpy(dtype=float).reshape(1500, 15, 25)
    X[X <= 0] = np.nan
    mnames = sorted(set(c.split("_TOL")[0] for c in cols))
    A = np.isfinite(X).any(axis=2)
    g1 = ~A[:, 0] & A[:, 14]          # m01 missing, m15 present
    g2 = A[:, 0] & ~A[:, 14]          # m15 missing
    g0 = A[:, 0] & A[:, 14]           # nothing missing
    groups = {"G0_full": g0, "G1_m01miss": g1, "G2_m15miss": g2}

    out = {}
    for gname, mask in groups.items():
        with np.errstate(all="ignore"):
            mdb = np.nanmean(X[mask], axis=1)              # (n,25) dB
            lin = 10.0 ** (mdb / 10.0)
            tot = np.nanmean(lin, axis=1)
        ok = np.isfinite(mdb).sum(axis=1) >= 10
        q = mdb[ok][tot[ok] <= np.nanpercentile(tot[ok], 20)]   # quietest 20%
        bed_mean = np.nanmean(q, axis=0)
        A2 = np.stack([np.ones(25), LF], axis=1)
        coef, *_ = np.linalg.lstsq(A2, q[np.isfinite(q).sum(axis=1) >= 10].T, rcond=None)
        bed_tilt = float(np.mean(coef[1]))
        # site matches: absolute band-level distance on floors + tilt distance
        rank = []
        for s in sites:
            fl = np.array(levels[s]["bed_mean"])
            d_abs = float(np.sqrt(np.nanmean((fl - bed_mean) ** 2)))
            d_tilt = abs(levels[s]["bed_tilt"] - bed_tilt)
            rank.append((s, round(d_abs, 2), round(d_tilt, 3)))
        rank_abs = sorted(rank, key=lambda r: r[1])
        rank_tilt = sorted(rank, key=lambda r: r[2])
        out[gname] = {
            "n": int(mask.sum()), "n_bed": int(len(q)),
            "bed_level_broadband_db": round(float(10 * np.log10(np.nanmean(10 ** (bed_mean / 10)))), 2),
            "bed_tilt_db_per_decade": round(bed_tilt, 2),
            "bed_band_levels": {b: round(float(v), 1) for b, v in zip(BANDS, bed_mean)},
            "site_rank_abs_rmse": rank_abs[:5],
            "site_rank_tilt": rank_tilt[:5],
        }
        print(f"\n{gname}: n={mask.sum()} bed_broadband={out[gname]['bed_level_broadband_db']} dB "
              f"tilt={bed_tilt:.1f} dB/dec")
        print("  abs-level rank:", rank_abs[:5])
        print("  tilt rank     :", rank_tilt[:5])

    # train-side reference: site bed broadband levels
    print("\ntrain site beds:")
    for s in sites:
        bb = 10 * np.log10(np.nanmean(10 ** (np.array(levels[s]["bed_mean"]) / 10)))
        print(f"  {s}: bed={bb:.1f} dB tilt={levels[s]['bed_tilt']:.1f}")

    with open("/home/z/my-project/data/train_v3/r7d_floor_match.json", "w") as f:
        json.dump({"round": "R7d", "groups": out,
                   "train_beds": {s: {"bed_broadband_db": round(float(10 * np.log10(np.nanmean(10 ** (np.array(levels[s]['bed_mean'])) / 10))), 2),
                                      "bed_tilt": levels[s]["bed_tilt"]} for s in sites}}, f, indent=1)


if __name__ == "__main__":
    main()
