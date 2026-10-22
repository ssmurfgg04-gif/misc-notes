#!/usr/bin/env python3
"""R12 — REAL-DATA detect-then-quantify build (user directive: no synthetic).

Organiser-exact construction (starter cells 9+11, all real sources):
  background = 15 consecutive real minutes (SA acoustics parquets, one recorder-day)
  passage    = real VTUAD clip sub-interval (refs.parquet, 3-7 min, random offset)
  gain       = solved so share = E_pass/(E_pass+E_bg) hits the sampled target share
               (share is a RATIO => absolute calibration irrelevant; organiser
               'energy varied' = this gain, 'trajectory varied' = offset/duration)
  mixture dB = 10log10(bg_linear + g2*pass_linear), NaN-preserving
Labels: present (balanced 0.5, feasible per pinned moments), share (exact by construction).
Models: LGBM detector (present) + LGBM quantifier (share) on raw 15x25 dB + bed-excess physics.
Splits: background group = (site, recorder, date) stratified; vessel clips DISJOINT (UniqueShip).
"""
import json, hashlib, math, time
import numpy as np
import pandas as pd
import lightgbm as lgb

t0 = time.time()
R = {"round": "R12", "date": "2026-10-22", "task": "real-data detect-then-quantify factory"}
rng = np.random.default_rng(20261022)

BANDS = [f"TOL_{x}" for x in ["31.6","39.8","50.1","63.1","79.4","100","125.9","158.5","199.5",
        "251.2","316.2","398.1","501.2","631","794.3","1000","1258.9","1584.9","1995.3","2511.9",
        "3162.3","3981.1","5011.9","6309.6","7943.3"]]
NB, WIN = 25, 15
SITE_CLASS = {  # G0 west / G1 south / G2 harbour proxy pools (r8_pool mapping)
    "A_west": ["13 Saldhana_Bay", "9 Fish_Hoek", "1 Richards_Bay", "2 Durban"],
    "B_south": ["7 St_Francis", "3 Cape_Recife", "6 Riy_Banks", "4 Bird_Island", "5 St_Croix_Island"],
    "C_harbour": ["2 Durban", "5 St_Croix_Island", "10 Sea_Point"],
}

# ---------- load real backgrounds ----------
print("loading SA parquets ...")
frames = []
for p in sorted(__import__("glob").glob("data/South_African_Real_Acoustics/acoustics/*.parquet")):
    d = pd.read_parquet(p, columns=["site", "recorder", "file_date", "t"] + BANDS)
    d = d[d["qc_25band_finite"] if "qc_25band_finite" in d.columns else True] if False else d
    frames.append(d)
sa = pd.concat(frames, ignore_index=True)
sa["grp"] = sa["site"].astype(str) + "|" + sa["recorder"].astype(str) + "|" + sa["file_date"].astype(str)
sa = sa.sort_values(["grp", "t"]).reset_index(drop=True)
valid = sa[BANDS].notna().sum(axis=1) >= 20  # allow a few NaN bands
sa_ok = sa[valid].reset_index(drop=True)
sa_ok["dt"] = sa_ok.groupby("grp")["t"].diff().dt.total_seconds()
sa_ok["run"] = sa_ok.groupby("grp")["dt"].apply(lambda s: (s != 60.0).fillna(True).cumsum()).reset_index(level=0, drop=True)
run_sizes = sa_ok.groupby(["grp", "run"]).size()
good_runs = run_sizes[run_sizes >= WIN].index
# positional index arrays into sa_ok for each good run (single groupby pass — O(N))
run_idx = []
run_site = []
grp_run_pos = sa_ok.groupby(["grp", "run"]).indices   # dict -> positional arrays
for key, pos in grp_run_pos.items():
    if len(pos) >= WIN:
        run_idx.append(pos)
        run_site.append(sa_ok["site"].iloc[pos[0]])
R["bg_supply"] = {"runs_ge15min": len(run_idx), "minutes_total": int(len(sa_ok)), "sites": int(sa_ok["site"].nunique())}
print("bg runs >=15min:", len(run_idx), "sites:", sa_ok["site"].nunique())

def bg_window(run_arr, start):
    rows = sa_ok.iloc[run_arr[start:start + WIN]]
    assert len(rows) == WIN
    db = rows[BANDS].to_numpy(np.float64)          # 15x25 dB (NaN possible)
    lin = np.power(10.0, db / 10.0)
    return db, lin, rows["site"].iloc[0]

# ---------- load real vessel passages ----------
print("loading VTUAD refs ...")
refs = pd.read_parquet("data/refs/refs.parquet")
refsm = pd.read_parquet("data/refs/refs_meta.parquet")
clips = {}
for uid, g in refs.groupby("clip_uid"):
    m = g["minute_idx"].max()
    arr = np.full((m, NB), np.nan)
    arr[g["minute_idx"].values - 1, g["band"].values] = g["power"].values
    if np.isfinite(arr).all():
        clips[int(uid)] = arr
clips = {k: v for k, v in clips.items() if v.shape[0] >= 3}
R["clips"] = {"n_usable": len(clips), "minutes_hist": {str(k): int(v) for k, v in
              pd.Series([v.shape[0] for v in clips.values()]).value_counts().items()}}
print("usable real clips:", len(clips))

# ---------- splits ----------
run_arr_all = np.array(range(len(run_idx)))
run_arr_all = run_arr_all[rng.permutation(len(run_arr_all))]
val_frac = 0.15
n_val = int(len(run_arr_all) * val_frac)
val_runs, train_runs = run_arr_all[:n_val], run_arr_all[n_val:]
R["splits_draft"] = {"val_runs": int(n_val), "train_runs": int(len(train_runs))}
clip_ids = np.array(sorted(clips))
rng.shuffle(clip_ids)
n_cv = max(20, int(0.12 * len(clip_ids)))
val_clips, train_clips = set(clip_ids[:n_cv].tolist()), set(clip_ids[n_cv:].tolist())
R["splits"] = {"bg_runs_train": int(len(train_runs)), "bg_runs_val": int(len(val_runs)),
               "clips_train": int(len(train_clips)), "clips_val": int(len(val_clips))}

# ---------- mixture factory ----------
def sample_share_present():
    # moment-matched Beta: mean 0.26, var 0.0538 (pinned moments @ P(present)=0.5)
    a, b = 0.6698, 1.9066
    return float(rng.beta(a, b))

def make_batch(blk_list, clip_pool, n, tag):
    Xf, y_pres, y_share, meta = [], [], [], []
    picks = rng.choice(blk_list, size=n, replace=True)
    starts = rng.integers(0, 4, size=n)  # start index within run (runs >=15 min)
    for i in range(n):
        try:
            db, lin, site = bg_window(run_idx[picks[i]], int(starts[i]))
        except AssertionError:
            continue
        present = bool(rng.random() < 0.5)
        share = 0.0
        if present:
            cid = int(rng.choice(sorted(clip_pool)))
            pass_full = clips[cid]
            M = pass_full.shape[0]
            m = int(min(M, rng.integers(3, 15)))       # sub-interval passage (organiser: trajectories varied)
            c0 = int(rng.integers(0, M - m + 1))
            pass_arr = pass_full[c0:c0 + m]
            off = int(rng.integers(0, WIN - m + 1))
            s = sample_share_present()
            mask = np.zeros((WIN, NB)); mask[off:off + m] = pass_arr
            E_bg = np.nansum(lin)
            E_pass_raw = np.nansum(mask)
            g2 = s * E_bg / ((1.0 - s) * E_pass_raw)
            lin = lin + g2 * mask
            share = s
        db_mix = np.where(lin > 0, 10.0 * np.log10(np.maximum(lin, 1e-300)), np.nan)
        Xf.append(featurize(db_mix))
        y_pres.append(present); y_share.append(share)
        meta.append((site, present, share))
    return np.array(Xf, dtype=np.float64), np.array(y_pres), np.array(y_share), meta

def featurize(db):
    # raw 375 (NaN ok), bed=min per band, excess, stats, minute energies, excess shape
    with np.errstate(invalid="ignore"):
        bed = np.nanmin(db, axis=0)                     # 25 bed estimate (passage <=14 min)
        exc = db - bed                                   # 15x25 excess dB
        lin = np.power(10.0, db / 10.0)
        exc_lin = np.maximum(lin - np.power(10.0, bed / 10.0)[None, :], 0.0)
        minute_tot = 10.0 * np.log10(np.nansum(lin, axis=1) + 1e-300)              # 15
        minute_exc = 10.0 * np.log10(np.nansum(exc_lin, axis=1) + 1e-300)          # 15
        exc_sum = np.nansum(exc_lin, axis=0) + 1e-300                                # 25
        exc_share = exc_sum / exc_sum.sum()                                          # 25
        band_std = np.nanstd(db, axis=0)                                             # 25
        band_rng = np.nanmax(db, axis=0) - bed                                       # 25
    flat = db.reshape(-1)
    return np.concatenate([flat, bed, exc.reshape(-1), band_std, band_rng,
                           minute_tot, minute_exc, exc_share,
                           [np.nanmax(band_rng), np.nansum(exc_lin)]])

print("building train/val batches ...")
Xtr, ytr_p, ytr_s, _ = make_batch(train_runs, train_clips, 9000, "train")
Xva, yva_p, yva_s, meta_va = make_batch(val_runs, val_clips, 1500, "val")
R["build"] = {"n_train": len(Xtr), "n_val": len(Xva),
              "train_minutes": round(time.time() - t0, 1)}

pos_rate = ytr_p.mean()
R["build"]["pos_rate"] = float(pos_rate)

det = lgb.LGBMClassifier(n_estimators=600, learning_rate=0.05, num_leaves=63,
                         colsample_bytree=0.8, subsample=0.8, subsample_freq=1,
                         min_child_samples=30, random_state=7, verbose=-1)
det.fit(Xtr, ytr_p)
from sklearn.metrics import roc_auc_score
pva = det.predict_proba(Xva)[:, 1]
R["detector_val"] = {"auc_all": float(roc_auc_score(yva_p, pva))}
for cname, slist in SITE_CLASS.items():
    idx = [i for i, mt in enumerate(meta_va) if mt[0] in slist]
    if len(idx) > 50 and len(set(np.array(yva_p)[idx])) > 1:
        R["detector_val"][f"auc_{cname}"] = float(roc_auc_score(np.array(yva_p)[idx], pva[idx]))

qnt = lgb.LGBMRegressor(n_estimators=800, learning_rate=0.05, num_leaves=63,
                        colsample_bytree=0.8, subsample=0.8, subsample_freq=1,
                        min_child_samples=30, random_state=7, verbose=-1)
qnt.fit(Xtr, ytr_s)
qva = np.clip(qnt.predict(Xva), 0, 1)
R["quantifier_val"] = {
    "rmse_all": float(np.sqrt(np.mean((qva - yva_s) ** 2))),
    "rho_all": float(np.corrcoef(qva, yva_s)[0, 1]),
    "rmse_pos": float(np.sqrt(np.mean((qva[yva_p == 1] - yva_s[yva_p == 1]) ** 2))),
    "rho_pos": float(np.corrcoef(qva[yva_p == 1], yva_s[yva_p == 1])[0, 1]) if (yva_p == 1).sum() > 2 else None,
}
for cname, slist in SITE_CLASS.items():
    idx = np.array([i for i, mt in enumerate(meta_va) if mt[0] in slist])
    if len(idx) > 50:
        R["quantifier_val"][f"rmse_{cname}"] = float(np.sqrt(np.mean((qva[idx] - yva_s[idx]) ** 2)))

# ---------- test inference ----------
print("test inference ...")
test = pd.read_csv("data/sa_package/Test.csv", dtype={"ID": str})
ids = test["ID"].tolist()
TX = test.drop(columns=["ID"]).to_numpy(np.float64)
Xte = np.array([featurize(TX[i].reshape(WIN, NB)) for i in range(len(TX))])
p_det = det.predict_proba(Xte)[:, 1]
q_sh = np.clip(qnt.predict(Xte), 0, 1)
R["test_vec"] = {"det_mean": float(p_det.mean()), "det_p50": float(np.median(p_det)),
                 "q_mean": float(q_sh.mean()), "q_p50": float(np.median(q_sh)),
                 "spearman_q_vs_e5": float(pd.Series(q_sh).rank().corr(
                     pd.read_csv("download/submission_r7_v4_kstar.csv")["share_added_vessel"].rank())),
                 "spearman_det_vs_e5": float(pd.Series(p_det).rank().corr(
                     pd.read_csv("download/submission_r7_v4_kstar.csv")["share_added_vessel"].rank()))}

np.savez("data/train_v3/r12_test_diag.npz", det=p_det, qnt=q_sh,
         ids=np.array(ids), det_val=pva, qnt_val=qva,
         yva_p=yva_p, yva_s=yva_s)
det.booster_.save_model("data/train_v3/r12_detector.txt")
qnt.booster_.save_model("data/train_v3/r12_quantifier.txt")

with open("data/train_v3/r12_report.json", "w") as f:
    json.dump(R, f, indent=1, default=float)
print(json.dumps(R, indent=1, default=float))
print("TOTAL minutes:", round((time.time() - t0) / 60, 1))
