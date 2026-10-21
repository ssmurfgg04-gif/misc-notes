#!/usr/bin/env python3
"""r7d_avail_census.py — cluster TEST windows by metric-availability fingerprint
(recorder duty signature) + cross-tab with shape-based site matches.

Questions:
  1. How many distinct availability (recorder-behaviour) groups in the test set?
  2. Per group: which shape-nearest TRAIN eras/sites? (identity candidates)
  3. Do any groups match known sites at LOW distance (duplicate-site theory)
     or sit far from everything (true hidden stations / reserved-slot)?
"""
import json
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

BASE = "/home/z/my-project/data/sa_package/South_African_Real_Acoustics"
BANDS = ["31.6", "39.8", "50.1", "63.1", "79.4", "100", "125.9", "158.5", "199.5",
         "251.2", "316.2", "398.1", "501.2", "631", "794.3", "1000", "1258.9",
         "1584.9", "1995.3", "2511.9", "3162.3", "3981.1", "5011.9", "6309.6", "7943.3"]
TOL = [f"TOL_{b}" for b in BANDS]
LF = np.log10(10.0 ** (1.5 + 0.1 * np.arange(25)))


def shape_desc_db(db):
    lin = 10.0 ** (db / 10.0)
    total = np.nansum(lin, axis=1, keepdims=True)
    share = lin / total
    A = np.stack([np.ones(25), LF], axis=1)
    tilt = np.full(len(db), np.nan)
    ok = np.isfinite(db).sum(axis=1) >= 10
    coef, *_ = np.linalg.lstsq(A, db[ok].T, rcond=None)
    tilt[ok] = coef[1]
    return np.column_stack([tilt, share]), ok


def main():
    # ---- train eras ----
    import glob, os
    descs, keys, recs = [], [], []
    for path in sorted(glob.glob(f"{BASE}/acoustics/*.parquet")):
        site = os.path.basename(path).replace(".parquet", "")
        df = pq.read_table(path, columns=["recorder"] + TOL).to_pandas()
        db = df[TOL].to_numpy(dtype=float)
        fin = np.isfinite(db).sum(axis=1) >= 10
        db = db[fin]
        d, ok = shape_desc_db(db)
        d = d[ok]
        r = df["recorder"].to_numpy()[fin][ok]
        idx = np.arange(len(d))
        if len(idx) > 20000:
            idx = np.random.default_rng(7).choice(idx, 20000, replace=False)
        descs.append(d[idx]); keys += [site] * len(idx); recs += list(r[idx])
    Dtr = np.vstack(descs)
    mu = np.nanmean(Dtr, axis=0); sd = np.nanstd(Dtr, axis=0) + 1e-9
    Ztr = (Dtr - mu) / sd
    era_key = np.array([f"{k}|{r.split('_')[0]}" for k, r in zip(keys, recs)])
    eras = sorted(set(era_key))
    cen = {e: np.nanmean(Ztr[era_key == e], axis=0) for e in eras}
    S = np.array([cen[e] for e in eras])

    # ---- test ----
    t = pd.read_csv("/home/z/my-project/data/Test.csv")
    cols = list(t.columns[1:])
    X = t[cols].to_numpy(dtype=float).reshape(1500, 15, 25)
    mnames = sorted(set(c.split("_TOL")[0] for c in cols))
    avail = np.isfinite(X).mean(axis=(1, 2))
    with np.errstate(all="ignore"):
        mdb = np.nanmean(X, axis=1)
    d, ok = shape_desc_db(mdb)
    Zte = (d - mu) / sd
    dist = np.linalg.norm(Zte[:, None, :] - S[None, :, :], axis=2)
    order = np.argsort(dist, axis=1)
    best_era = np.array(eras)[order[:, 0]]
    dmin = dist[np.arange(1500), order[:, 0]]

    # ---- availability-mask clustering ----
    A = np.isfinite(X).any(axis=2).astype(float)   # (1500, 15)
    best_k, best_s, models = None, -2, {}
    for k in range(2, 9):
        km = KMeans(n_clusters=k, n_init=10, random_state=7).fit(A)
        s = silhouette_score(A, km.labels_, sample_size=2000, random_state=7)
        models[k] = (km, s)
        if s > best_s:
            best_s, best_k = s, k
    km, sil = models[best_k]
    print(f"availability clustering k*={best_k} sil={sil:.3f} sweep=" +
          str({k: round(models[k][1], 3) for k in models}))

    groups = []
    for c in sorted(set(km.labels_)):
        m = km.labels_ == c
        prof = A[m].mean(axis=0)
        era_counts = pd.Series(best_era[m]).value_counts().head(4)
        dmq = np.percentile(dmin[m], [10, 50, 90]).tolist()
        groups.append({
            "group": int(c), "n": int(m.sum()),
            "avail_profile": {mm: round(float(v), 3) for mm, v in zip(mnames, prof) if v > 0.01},
            "dmin_p10_p50_p90": [round(x, 2) for x in dmq],
            "top_era_assignments": [[e, int(v)] for e, v in era_counts.items()],
        })
        print(f"group {c}: n={m.sum()} dmin p10/50/90={[round(x,1) for x in dmq]}")
        print("   avail:", {mm: round(float(v), 2) for mm, v in zip(mnames, prof) if v > 0.01})
        print("   top eras:", dict(era_counts))

    # ---- cross-tab group x shape-site ----
    sites = sorted(set(e.split("|")[0] for e in eras))
    site_dist = np.zeros((1500, len(sites)))
    for i, s in enumerate(sites):
        idxs = [j for j, e in enumerate(eras) if e.startswith(s + "|")]
        site_dist[:, i] = dist[:, idxs].min(axis=1)
    best_site = np.array(sites)[np.argsort(site_dist, axis=1)[:, 0]]
    tab = pd.crosstab(pd.Series(km.labels_, name="avail_group"),
                      pd.Series(best_site, name="shape_site"))
    print("\ncross-tab (avail group x shape-nearest site):")
    print(tab.to_string())

    report = {"round": "R7d", "k": int(best_k), "silhouette": float(sil),
              "sweep": {str(k): float(models[k][1]) for k in models},
              "groups": groups,
              "crosstab": {str(i): row.to_dict() for i, row in tab.iterrows()}}
    with open("/home/z/my-project/data/train_v3/r7d_avail_census.json", "w") as f:
        json.dump(report, f, indent=1)


if __name__ == "__main__":
    main()
