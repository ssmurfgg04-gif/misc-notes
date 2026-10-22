#!/usr/bin/env python3
"""R12b — zero-risk detection probe build (r12_v2).

D46 (r12b_fold): real-quantifier share family DEAD (ceiling 0.7966 < best 0.798997).
=> share col LOCKED = r7_v4_kstar values (measured 0.798997019 twice, deterministic).
=> score col = strongest NEW detector candidate (weight-0 AUC diagnostic channel,
   starter-sanctioned). Candidates: training-free physics excess detectors
   (no clip-domain gap, no learned-feature drift) + saved R12 LGBM anchors.

Physics detectors (window-local, NaN-aware, from raw 15x25 dB):
  bed(b) = min over observed minutes; exc_lin = max(lin - bed_lin, 0)
  c1_lf   LF(<=1kHz) excess energy ratio     = sum exc_lf / sum lin_lf
  c1_hf   HF excess ratio (control)
  c2_tot  total excess energy ratio
  c3_conc peak-minute LF excess share (temporal concentration)
  c4_lfsh excess spectral LF-share
  combo   rank(c1_lf) + rank(c3_conc)
Val: fresh factory-faithful batch (seed 20261022b2, 1500 mixtures, real VTUAD
passages + real SA backgrounds, organiser-exact power-domain mixing).
"""
import json, math, time, glob
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score
from scipy.stats import rankdata

t0 = time.time()
R = {"round": "R12b", "date": "2026-10-22", "task": "r12_v2 locked-share + physics-detector probe"}
rng = np.random.default_rng(20261022)

BANDS = [f"TOL_{x}" for x in ["31.6","39.8","50.1","63.1","79.4","100","125.9","158.5","199.5",
        "251.2","316.2","398.1","501.2","631","794.3","1000","1258.9","1584.9","1995.3","2511.9",
        "3162.3","3981.1","5011.9","6309.6","7943.3"]]
NB, WIN = 25, 15
LF = list(range(16))          # 31.6 .. 1000 Hz
HF = list(range(16, 25))

# ---------- real backgrounds (factory-faithful) ----------
print("loading SA parquets ...")
frames = []
for p in sorted(glob.glob("data/South_African_Real_Acoustics/acoustics/*.parquet")):
    frames.append(pd.read_parquet(p, columns=["site", "recorder", "file_date", "t"] + BANDS))
sa = pd.concat(frames, ignore_index=True)
sa["grp"] = sa["site"].astype(str) + "|" + sa["recorder"].astype(str) + "|" + sa["file_date"].astype(str)
sa = sa.sort_values(["grp", "t"]).reset_index(drop=True)
valid = sa[BANDS].notna().sum(axis=1) >= 20
sa_ok = sa[valid].reset_index(drop=True)
sa_ok["dt"] = sa_ok.groupby("grp")["t"].diff().dt.total_seconds()
sa_ok["run"] = sa_ok.groupby("grp")["dt"].apply(lambda s: (s != 60.0).fillna(True).cumsum()).reset_index(level=0, drop=True)
grp_run_pos = sa_ok.groupby(["grp", "run"]).indices
run_idx, run_site = [], []
for key, pos in grp_run_pos.items():
    if len(pos) >= WIN:
        run_idx.append(pos)
        run_site.append(sa_ok["site"].iloc[pos[0]])
print("bg runs:", len(run_idx))

def bg_window(run_arr, start):
    rows = sa_ok.iloc[run_arr[start:start + WIN]]
    assert len(rows) == WIN
    return rows[BANDS].to_numpy(np.float64), rows["site"].iloc[0]

# ---------- real VTUAD passages (linear band power) ----------
refs = pd.read_parquet("data/refs/refs.parquet")
clips = {}
for uid, g in refs.groupby("clip_uid"):
    m = int(g["minute_idx"].max())
    arr = np.full((m, NB), np.nan)
    arr[g["minute_idx"].values - 1, g["band"].values] = g["power"].values
    if np.isfinite(arr).all():
        clips[int(uid)] = arr
clips = {k: v for k, v in clips.items() if v.shape[0] >= 3}
print("usable clips:", len(clips))

# ---------- splits (fresh seed) ----------
perm = rng.permutation(len(run_idx))
n_val = int(len(run_idx) * 0.15)
val_runs = perm[:n_val]
clip_ids = np.array(sorted(clips)); rng.shuffle(clip_ids)
val_clips = set(clip_ids[:max(20, int(0.12 * len(clip_ids)))].tolist())

def sample_share_present():
    a, b = 0.6698, 1.9066
    return float(rng.beta(a, b))

def make_batch_val(n):
    """factory-faithful val batch; returns db matrices + features + labels."""
    Xf, DB, yp, ys = [], [], [], []
    picks = rng.choice(val_runs, size=n, replace=True)
    starts = rng.integers(0, 4, size=n)
    for i in range(n):
        try:
            db, site = bg_window(run_idx[picks[i]], int(starts[i]))
        except AssertionError:
            continue
        lin = np.power(10.0, db / 10.0)
        present = bool(rng.random() < 0.5)
        share = 0.0
        if present:
            cid = int(rng.choice(sorted(val_clips)))
            M = clips[cid].shape[0]
            m = int(min(M, rng.integers(3, 15)))
            c0 = int(rng.integers(0, M - m + 1))
            off = int(rng.integers(0, WIN - m + 1))
            s = sample_share_present()
            mask = np.zeros((WIN, NB)); mask[off:off + m] = clips[cid][c0:c0 + m]
            E_bg = np.nansum(lin)
            g2 = s * E_bg / ((1.0 - s) * np.nansum(mask))
            lin = lin + g2 * mask
            share = s
        db_mix = np.where(lin > 0, 10.0 * np.log10(np.maximum(lin, 1e-300)), np.nan)
        DB.append(db_mix); Xf.append(featurize(db_mix)); yp.append(present); ys.append(share)
    return np.array(DB), np.array(Xf, dtype=np.float64), np.array(yp), np.array(ys)

def featurize(db):
    with np.errstate(invalid="ignore"):
        bed = np.nanmin(db, axis=0)
        exc = db - bed
        lin = np.power(10.0, db / 10.0)
        exc_lin = np.maximum(lin - np.power(10.0, bed / 10.0)[None, :], 0.0)
        minute_tot = 10.0 * np.log10(np.nansum(lin, axis=1) + 1e-300)
        minute_exc = 10.0 * np.log10(np.nansum(exc_lin, axis=1) + 1e-300)
        exc_sum = np.nansum(exc_lin, axis=0) + 1e-300
        exc_share = exc_sum / exc_sum.sum()
        band_std = np.nanstd(db, axis=0)
        band_rng = np.nanmax(db, axis=0) - bed
    return np.concatenate([db.reshape(-1), bed, exc.reshape(-1), band_std, band_rng,
                           minute_tot, minute_exc, exc_share,
                           [np.nanmax(band_rng), np.nansum(exc_lin)]])

print("building fresh val batch (1500) ...")
DBv, Xva, yva_p, yva_s = make_batch_val(1500)
R["val_batch"] = {"n": int(len(yva_p)), "pos_rate": float(yva_p.mean())}

# ---------- physics detectors ----------
def phys_scores(db):
    with np.errstate(invalid="ignore"):
        bed = np.nanmin(db, axis=0)
        lin = np.power(10.0, db / 10.0)
        exc_lin = np.maximum(lin - np.power(10.0, bed / 10.0)[None, :], 0.0)
        eps = 1e-300
        c1_lf = np.nansum(exc_lin[:, LF]) / (np.nansum(lin[:, LF]) + eps)
        c1_hf = np.nansum(exc_lin[:, HF]) / (np.nansum(lin[:, HF]) + eps)
        c2 = np.nansum(exc_lin) / (np.nansum(lin) + eps)
        m_exc = np.nansum(exc_lin[:, LF], axis=1)
        m_tot = np.nansum(lin[:, LF], axis=1)
        c3 = np.nanmax(m_exc / (m_tot + eps))
        c4 = np.nansum(exc_lin[:, LF]) / (np.nansum(exc_lin) + eps)
    return c1_lf, c1_hf, c2, c3, c4

P = np.array([phys_scores(db) for db in DBv])
c1_lf, c1_hf, c2, c3, c4 = P[:, 0], P[:, 1], P[:, 2], P[:, 3], P[:, 4]
combo = rankdata(c1_lf) + rankdata(c3)

cands = {"c1_lf": c1_lf, "c1_hf": c1_hf, "c2_tot": c2, "c3_conc": c3, "c4_lfsh": c4, "combo_c1c3": combo}

# anchors: saved R12 models on the same fresh val
det = lgb.Booster(model_file="data/train_v3/r12_detector.txt")
qnt = lgb.Booster(model_file="data/train_v3/r12_quantifier.txt")
p_det = det.predict(Xva)
q_qnt = np.clip(qnt.predict(Xva), 0, 1)
cands["anchor_r12_lgbm_det"] = p_det
cands["anchor_r12_quant_as_det"] = q_qnt

R["val_auc"] = {}
for k, s in cands.items():
    R["val_auc"][k] = float(roc_auc_score(yva_p, s))
R["val_spearman_phys_vs_lgbm"] = float(pd.Series(combo).rank().corr(pd.Series(p_det).rank()))
R["val_share_rmse_quant"] = float(np.sqrt(np.mean((q_qnt - yva_s) ** 2)))
R["val_rho_quant"] = float(np.corrcoef(q_qnt, yva_s)[0, 1])

# ---------- pick winner (physics only) ----------
phys_names = ["c1_lf", "c1_hf", "c2_tot", "c3_conc", "c4_lfsh", "combo_c1c3"]
best = max(phys_names, key=lambda k: R["val_auc"][k])
R["winner"] = best
print("val AUCs:", {k: round(v, 4) for k, v in R["val_auc"].items()})
print("winner:", best)

# ---------- test side ----------
test = pd.read_csv("data/sa_package/Test.csv", dtype={"ID": str})
ids = test["ID"].tolist()
TX = test.drop(columns=["ID"]).to_numpy(np.float64)
DBt = [TX[i].reshape(WIN, NB) for i in range(len(TX))]
Pt = np.array([phys_scores(db) for db in DBt])
test_map = {"c1_lf": Pt[:, 0], "c1_hf": Pt[:, 1], "c2_tot": Pt[:, 2],
            "c3_conc": Pt[:, 3], "c4_lfsh": Pt[:, 4],
            "combo_c1c3": rankdata(Pt[:, 0]) + rankdata(Pt[:, 3])}
sc_test = test_map[best]
R["test_score_stats"] = {"min": float(np.nanmin(sc_test)), "max": float(np.nanmax(sc_test)),
                         "n_nan": int(np.isnan(sc_test).sum())}
assert np.isfinite(sc_test).all(), "NaN in test physics score"

# drift audit lite: per-band test mean vs fresh-val mean (dB)
tb = np.nanmean(np.stack(DBt), axis=(0, 1))
vb = np.nanmean(DBv, axis=(0, 1))
R["drift_band_db"] = {BANDS[i].replace("TOL_", ""): round(float(tb[i] - vb[i]), 2) for i in range(NB)}
R["drift_note"] = "test_minus_val per-band mean dB (large |d| => factory representation gap)"

# ---------- assemble r12_v2 ----------
r7 = pd.read_csv("download/submission_r7_v4_kstar.csv", dtype={"ID": str})
share = r7["share_added_vessel"].to_numpy(float)
assert abs(share.mean() - 0.1300757620833332) < 1e-12
assert abs((share ** 2).mean() - 0.020644126729202947) < 1e-12
assert r7["ID"].tolist() == ids, "ID order mismatch vs Test.csv"

# score col: keep natural scale if within [0,1], else rank-normalize (AUC-invariant)
if sc_test.min() >= 0 and sc_test.max() <= 1:
    score_col = sc_test
    note = f"raw {best} (natural [0,1])"
else:
    score_col = (rankdata(sc_test) - 1) / (len(sc_test) - 1)
    note = f"rank-normalized {best}"

stage = pd.DataFrame({"ID": ids, "share_added_vessel": share, "score_added_vessel": score_col})
stage_path = "data/train_v3/r12_v2_stage.csv"
stage.to_csv(stage_path, index=False)
R["r12_v2"] = {"stage": stage_path, "share_col": "locked r7_v4_kstar (expect 0.798997019)",
               "score_col": note, "spearman_score_vs_share": float(
                   pd.Series(score_col).rank().corr(pd.Series(share).rank())),
               "expected_share_score": 0.798997019,
               "expected_auc_read": f"{best} detection transfer (physics, training-free)"}

with open("data/train_v3/r12b_build_report.json", "w") as f:
    json.dump(R, f, indent=1, default=float)
print(json.dumps({k: R[k] for k in ["val_auc", "winner", "r12_v2"]}, indent=1, default=float))
print("TOTAL minutes:", round((time.time() - t0) / 60, 1))
