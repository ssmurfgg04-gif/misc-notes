#!/usr/bin/env python3
"""r7d_test_stations.py — census of the 1,500 TEST windows: how many distinct
hidden stations? Which recorder classes? Do any test groups match KNOWN sites
(duplicate-site theory) or nothing at all (reserved-slot theory)?

Method
  train: 10 SA parquets -> per-minute 25 common-band (31.6..7943.3 Hz) dB rows
         -> level-invariant descriptors: tilt + band_share(25), per SITE x RECORDER era
  test : 1500 windows x 15 metrics x 25 bands (dB)
         -> per-window: mean dB over available metrics -> tilt + band_share(25)
         + nan_rate (metric dropout) + hf_top (finite fraction at >6309 Hz)
         -> KMeans k=2..8 (silhouette pick) -> group census
  match: test groups vs train era centroids (SiteID nearest-centroid, shape-only)

Outputs: data/train_v3/r7d_test_station_census.json + console summary.
"""
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA

BASE = "/home/z/my-project/data/sa_package/South_African_Real_Acoustics"
BANDS = ["31.6", "39.8", "50.1", "63.1", "79.4", "100", "125.9", "158.5", "199.5",
         "251.2", "316.2", "398.1", "501.2", "631", "794.3", "1000", "1258.9",
         "1584.9", "1995.3", "2511.9", "3162.3", "3981.1", "5011.9", "6309.6", "7943.3"]
TOL = [f"TOL_{b}" for b in BANDS]
LF = np.log10(10.0 ** (1.5 + 0.1 * np.arange(25)))
HF_IDX = [i for i, b in enumerate(BANDS) if float(b) > 6309.6]  # 6309.6 & 7943.3


def shape_desc(db):
    """db: (n,25) dB values (NaN allowed) -> [tilt, share*25]; level-invariant."""
    lin = 10.0 ** (db / 10.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        pass
    band_db = db.copy()
    total = np.nansum(lin, axis=1, keepdims=True)
    with np.errstate(divide="ignore", invalid="ignore"):
        share = lin / total
    A = np.stack([np.ones(25), LF], axis=1)
    tilt = np.full(len(db), np.nan)
    ok = np.isfinite(band_db).sum(axis=1) >= 10
    coef, *_ = np.linalg.lstsq(A, band_db[ok].T, rcond=None)
    tilt[ok] = coef[1]
    return np.column_stack([tilt, share]), ok


def load_train():
    import glob, os
    descs, keys, rec_keys, floors = [], [], [], {}
    for path in sorted(glob.glob(f"{BASE}/acoustics/*.parquet")):
        site = os.path.basename(path).replace(".parquet", "")
        df = pq.read_table(path, columns=["recorder", "sample_rate_hz"] + TOL).to_pandas()
        db = df[TOL].to_numpy(dtype=float)
        # drop sentinel/negative absurdities, keep finite rows
        fin = np.isfinite(db).sum(axis=1) >= 10
        db = db[fin]
        d, ok = shape_desc(db)
        d = d[ok]
        # per recorder-era subsample for centroids
        recs = df["recorder"].to_numpy()[fin][ok] if "recorder" in df else np.array(["?"] * len(db))
        uniq = pd.unique(recs)
        for r in uniq:
            m = recs == r
            idx = np.where(m)[0]
            if len(idx) > 20000:
                idx = np.random.default_rng(7).choice(idx, 20000, replace=False)
            descs.append(d[idx])
            keys += [site] * len(idx)
            rec_keys += [r] * len(idx)
        # site noise floor (10th pct per band) for reference
        floors[site] = np.nanpercentile(db, 10, axis=0).tolist()
        print(f"  {site}: rows={len(db)} eras={len(uniq)}")
    return np.vstack(descs), keys, rec_keys, floors


def load_test():
    t = pd.read_csv("/home/z/my-project/data/Test.csv")
    ids = t["ID"].to_numpy()
    cols = list(t.columns[1:])
    assert len(cols) == 375
    # column order: m01..m15 x 25 bands (verify a band stride)
    X = t[cols].to_numpy(dtype=float).reshape(1500, 15, 25)
    # metric availability
    avail = np.isfinite(X).mean(axis=(1, 2))          # overall data presence
    avail_mask = np.isfinite(X).any(axis=2)           # (n,15) metric present?
    # mean dB over available metrics
    with np.errstate(all="ignore"):
        mdb = np.nanmean(X, axis=1)
    d, ok = shape_desc(mdb)
    nan_rate = np.isnan(X).mean(axis=(1, 2))
    hf_top = np.isfinite(X[:, :, HF_IDX]).mean(axis=(1, 2))
    return ids, d, ok, nan_rate, hf_top, avail_mask


def main():
    print("loading train…")
    Dtr, keys, rec_keys, floors = load_train()
    print("train descriptor matrix:", Dtr.shape)
    print("loading test…")
    ids, Dte, ok_te, nan_rate, hf_top, avail_mask = load_test()
    print("test descriptors:", Dte.shape, " usable rows:", ok_te.sum())

    # ---- train centroids per site and per site-era ----
    mu = np.nanmean(Dtr, axis=0); sd = np.nanstd(Dtr, axis=0) + 1e-9
    Ztr = (Dtr - mu) / sd
    sites = sorted(set(keys))
    cen_site = {s: np.nanmean(Ztr[np.array(keys) == s], axis=0) for s in sites}
    era_key = np.array([f"{k}|{r.split('_')[0]}" for k, r in zip(keys, rec_keys)])
    eras = sorted(set(era_key))
    cen_era = {e: np.nanmean(Ztr[era_key == e], axis=0) for e in eras}

    # ---- assign test windows ----
    Zte = (Dte - mu) / sd
    S_site = np.array([cen_site[s] for s in sites])
    dist = np.linalg.norm(Zte[:, None, :] - S_site[None, :, :], axis=2)
    order = np.argsort(dist, axis=1)
    best = order[:, 0]; second = order[:, 1]
    margin = dist[np.arange(1500), second] - dist[np.arange(1500), best]
    dmin = dist[np.arange(1500), best]
    assigned = np.array(sites)[best]

    # reference distribution of min-distances WITHIN train (resubstitution)
    dtr_min = np.linalg.norm(Ztr[:, None, :] - S_site[None, :, :], axis=2).min(axis=1)
    q = np.percentile(dtr_min, [50, 90, 95, 99]).tolist()

    # ---- cluster test windows (on usable shape + dropout + hf) ----
    feat = np.column_stack([
        Zte,
        nan_rate,
        hf_top,
        avail_mask.astype(float),
    ])
    F = feat[ok_te]
    F = np.nan_to_num(F, nan=0.0)
    best_k, best_s, models = None, -2, {}
    for k in range(2, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=7).fit(F)
        s = silhouette_score(F, km.labels_, sample_size=2000, random_state=7)
        models[k] = (km, s)
        if s > best_s:
            best_s, best_k = s, k
    km, sil = models[best_k]
    print(f"KMeans k*={best_k} (silhouette {sil:.3f})")

    labels = np.full(1500, -1)
    labels[ok_te] = km.labels_

    # ---- per-cluster census ----
    census = []
    for c in sorted(set(labels) - {-1}):
        m = labels == c
        dm = dmin[m]
        top2 = [sites[i] for i in np.argsort(dist[m].mean(axis=0))[:3]]
        era_d = {e: float(np.linalg.norm(Zte[m].mean(axis=0) - cen_era[e])) for e in eras}
        top_era = sorted(era_d.items(), key=lambda kv: kv[1])[:3]
        census.append({
            "cluster": int(c), "n_windows": int(m.sum()),
            "dmin_p50": float(np.median(dm)), "dmin_p10": float(np.percentile(dm, 10)),
            "nan_rate_mean": float(nan_rate[m].mean()),
            "hf_top_mean": float(hf_top[m].mean()),
            "top3_site_matches": top2,
            "mean_dist_to_site": {s: float(dist[m][:, i].mean()) for i, s in enumerate(sites)},
            "nearest_eras": [[e, round(v, 3)] for e, v in top_era],
        })

    # ---- distance ratio: cluster-to-nearest-site vs train-internal spread ----
    report = {
        "round": "R7d", "date": "2026-10-21",
        "train_min_dist_pctiles_p50_p90_p95_p99": q,
        "test_dmin_p50": float(np.median(dmin)),
        "test_dmin_p90": float(np.percentile(dmin, 90)),
        "kmeans": {"k": int(best_k), "silhouette": float(sil),
                   "sweep": {str(k): float(models[k][1]) for k in models}},
        "site_assign_counts": {s: int((assigned == s).sum()) for s in sites},
        "clusters": census,
        "floors_db": floors,
    }
    with open("/home/z/my-project/data/train_v3/r7d_test_station_census.json", "w") as f:
        json.dump(report, f, indent=1)

    print("\ntrain-internal dmin pctiles [p50,p90,p95,p99]:", [round(x, 2) for x in q])
    print("test dmin p50/p90:", round(float(np.median(dmin)), 2), round(float(np.percentile(dmin, 90)), 2))
    print("site assignment counts:", {s: int((assigned == s).sum()) for s in sites})
    for c in census:
        print(f"cluster {c['cluster']}: n={c['n_windows']} dmin_p50={c['dmin_p50']:.2f} "
              f"nan={c['nan_rate_mean']:.3f} hf_top={c['hf_top_mean']:.2f} "
              f"top={c['top3_site_matches'][0]} eras={c['nearest_eras'][0]}")


if __name__ == "__main__":
    main()
