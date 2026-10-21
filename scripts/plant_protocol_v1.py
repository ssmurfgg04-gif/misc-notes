#!/usr/bin/env python3
"""R7 plant protocol v1 — the decisive recipe + estimator experiment.

Questions:
  Q1 (recipe): does the organisers' addition span the full window or a sub-interval?
      KPI: within-window per-band (max-min) dB — test p50 = 16.0 vs raw 6.5.
  Q2 (estimator): can a bump-reading estimator recover f on planted windows
      (RMSE << 0.224 = our best LB)?
  Q3 (A29/H_C): how much does an ambient-laden addition degrade detection?
  Q4 (contamination): false-alarm floor on f=0 raw windows (natural vessels).

All at feature level (minute x 25 band linear power), A32 convention:
f = sum(V over observed cells) / sum(M over observed cells).
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
RAW = BASE / "data/South_African_Real_Acoustics/South_African_Real_Acoustics/acoustics"
OUT = BASE / "data/train_v3/plant_v1_report.json"
WIN, NB = 15, 25
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
rng = np.random.default_rng(2026)

# ---------------- background windows from raw parquets ----------------
def comp_band_idx(tol_cols):
    freqs = np.array([float(c.replace("TOL_", "").replace("k", "e3")) for c in tol_cols])
    idx = []
    for cc in CENTRES:
        j = int(np.argmin(np.abs(np.log10(freqs) - np.log10(cc))))
        idx.append(j if abs(np.log10(freqs[j]) - np.log10(cc)) < 0.06 else -1)
    return idx

def load_site(path, cap=4000):
    df = pd.read_parquet(path)
    df = df[df["file_kind"] == "MinRes"]
    tol_cols = [c for c in df.columns if c.startswith("TOL_")]
    keep = [k for k in comp_band_idx(tol_cols) if k >= 0]
    V = df[tol_cols].to_numpy(float)[:, keep]
    tm = pd.to_datetime(df["t"]).to_numpy().astype("datetime64[m]").astype(np.int64)
    rec = df["recorder"].astype(str).to_numpy()
    dtmp = pd.DataFrame({"m": tm, "r": rec})
    kr = ~dtmp.duplicated(subset=["r", "m"], keep="first").to_numpy()
    V, tm, rec = V[kr], tm[kr], rec[kr]
    o = np.argsort(tm, kind="stable")
    V, tm, rec = V[o], tm[o], rec[o]
    wins, sites = [], []
    i = 0
    while i + WIN <= len(V):
        if tm[i + WIN - 1] - tm[i] == WIN - 1 and len(set(rec[i:i + WIN])) == 1:
            w = V[i:i + WIN].astype(float)
            w = np.where(np.isfinite(w) & (w > -300) & (w < 300), w, np.nan)
            if np.isfinite(w).mean() > 0.9:
                wins.append(10.0 ** (w / 10.0))
                sites.append(path.stem)
                if len(wins) >= cap:
                    break
            i += WIN
        else:
            i += 1
    return wins, sites

bg_list, site_list = [], []
for f in sorted(RAW.glob("*.parquet")):
    w, s = load_site(f)
    bg_list += w; site_list += s
    print(f"{f.stem:22} +{len(w)} windows (total {len(bg_list)})")
BG = np.stack(bg_list)                       # (N,15,25) linear, NaN->nan kept where possible
BG = np.where(np.isfinite(BG), BG, np.nan)
print("BG pool:", BG.shape)

# test windows
test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)

# VTUAD refs
refs = pd.read_parquet(BASE / "data/refs.parquet")
Vclips = {}
for uid, g in refs.groupby("clip_uid"):
    m = int(g["minute_idx"].max())
    if m >= 2:
        Vclips[int(uid)] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, NB).astype(float)
bgrefs = pd.read_parquet(BASE / "data/bg_refs.parquet")
BGclips = {}
for uid, g in bgrefs.groupby("clip_uid"):
    m = int(g["minute_idx"].max())
    if m >= 2:
        BGclips[int(uid)] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, NB).astype(float)
print(f"VTUAD vessel clips: {len(Vclips)}, bg clips: {len(BGclips)}")

# ---------------- helpers ----------------
def band_range_p50(X):
    X = np.where(np.isfinite(X) & (X > 0) & (X < 1e30), X, np.nan)
    Xdb = 10 * np.log10(X)                       # works for both dB (test) and linear (planted)
    r = np.nanmax(Xdb, axis=1) - np.nanmin(Xdb, axis=1)
    r = r[np.isfinite(r)]
    return float(np.percentile(r, 50))

def make_reference(clip, minutes, placement, amb_clip=None, amb_ratio=0.0):
    """Return (V_seg, L, start): the placed segment, its length and start minute.
    placement='full': stretch/tile clip to full 15-min length (L=15, start=0).
    placement='sub':  natural clip length 3..12 min at a random start."""
    m = clip.shape[0]
    if placement == "full":
        if m >= minutes:
            s0 = int(rng.integers(0, m - minutes + 1))
            W = clip[s0:s0 + minutes].copy()
        else:
            reps = int(np.ceil(minutes / m))
            W = np.concatenate([clip * rng.uniform(0.8, 1.2) for _ in range(reps)], axis=0)[:minutes]
        L, start = minutes, 0
    else:
        L = min(m, int(rng.integers(3, 13)))
        s0 = int(rng.integers(0, m - L + 1))
        W = clip[s0:s0 + L].copy()
        start = int(rng.integers(0, minutes - L + 1))
    if amb_clip is not None and amb_ratio > 0:
        am = amb_clip.shape[0]
        take = min(L, am)
        a0 = int(rng.integers(0, am - take + 1))
        amb = amb_clip[a0:a0 + take].copy()
        if take < L:
            reps = int(np.ceil(L / take))
            amb = np.concatenate([amb] * reps, axis=0)[:L]
        a_pow = amb.sum(); s_pow = max(W.sum(), 1e-30)
        W = W + amb * (amb_ratio * s_pow / max(a_pow, 1e-30))
    return W, L, start

def plant(B, f_true, clip, placement, amb_clip=None, amb_ratio=0.0):
    """Mix reference into background window at exact share f over observed cells."""
    M = WIN
    obs = np.isfinite(B)
    sumB = np.nansum(np.where(obs, B, 0.0))
    V, L, start = make_reference(clip, M, placement, amb_clip, amb_ratio)
    if f_true <= 0:
        return B.copy(), 0.0
    Vfull = np.zeros((M, NB))
    Vfull[start:start + L] = V[:L]               # embed segment in the window
    Vfull = np.where(obs, Vfull, 0.0)
    sumV_nat = Vfull.sum()
    alpha = f_true / (1 - f_true) * sumB / max(sumV_nat, 1e-30)
    Xv = Vfull * alpha
    X = np.where(obs, np.nan_to_num(B, nan=0.0) + Xv, np.nan)
    f_real = np.nansum(Xv) / np.nansum(np.where(obs, X, 0.0))
    return X, float(f_real)

# ---------------- estimators ----------------
def est_running_median(X, c=3.5, k_bands=5):
    """E1: per-band running-median baseline; coherent positive residuals = addition."""
    N = X.shape[0]
    f = np.zeros(N)
    for i in range(N):
        W = X[i]
        obs = np.isfinite(W)
        exc_sum = 0.0
        base = np.full_like(W, np.nan)
        for b in range(NB):
            col = W[:, b]
            if np.isfinite(col).sum() < 4:
                continue
            s = pd.Series(col).fillna(np.nanmedian(col))
            rm = s.rolling(7, center=True, min_periods=3).median()
            rm = rm.fillna(s.expanding().median())
            base[:, b] = rm.to_numpy()
        resid = W - base
        mad = np.nanmedian(np.abs(resid - np.nanmedian(resid, axis=0)), axis=0) + 1e-12
        thr = c * mad[None, :]
        bump_minute = ((resid > thr) & obs).sum(axis=1) >= k_bands
        exc = np.where(obs & bump_minute[:, None], np.maximum(resid, 0.0), 0.0)
        exc_sum = exc.sum()
        tot = np.nansum(np.where(obs, W, 0.0))
        f[i] = exc_sum / tot if tot > 0 else 0.0
    return np.clip(f, 0, 1)

def est_p25(X):
    """E2: v0 per-band p25 baseline."""
    N = X.shape[0]
    f = np.zeros(N)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        Bh = np.nanpercentile(W, 25, axis=0)
        exc = np.where(obs, np.maximum(W - Bh[None, :], 0.0), 0.0)
        tot = np.nansum(np.where(obs, W, 0.0))
        f[i] = exc.sum() / tot if tot > 0 else 0.0
    return np.clip(f, 0, 1)

def rmse(a, b):
    return float(np.sqrt(np.mean((np.asarray(a) - np.asarray(b)) ** 2)))

def rho(a, b):
    return float(np.corrcoef(a, b)[0, 1])

# ---------------- Q1: recipe KPI ----------------
print("\n=== Q1 recipe KPI (within-window per-band range p50, dB) ===")
kpi = dict(test=band_range_p50(TX))
print(f"test windows            : {kpi['test']:.1f}")
sub = 400
bg_s = BG[rng.choice(len(BG), sub, replace=False)]
kpi["raw"] = band_range_p50(bg_s)
print(f"raw background          : {kpi['raw']:.1f}")
clips = sorted(Vclips)
plants = {}
for placement in ["full", "sub"]:
    for amb_r, tag in [(0.0, "HA"), (1.0, "HC")]:
        Xs, fs = [], []
        for i in range(sub):
            B = bg_s[i]
            cl = Vclips[clips[rng.integers(0, len(clips))]]
            f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
            amb = list(BGclips.values())[rng.integers(0, len(BGclips))] if amb_r > 0 else None
            X, fr = plant(B, f, cl, placement, amb, amb_r)
            Xs.append(X); fs.append(fr)
        Xs = np.stack(Xs)
        key = f"{placement}_{tag}"
        plants[key] = (Xs, np.array(fs))
        kpi[key] = band_range_p50(Xs)
        print(f"planted {key:12}: {kpi[key]:.1f}")

# ---------------- Q2/Q3: estimator on planted windows ----------------
print("\n=== Q2/Q3 estimators on planted windows (known f) ===")
res = {}
for key, (Xs, fs) in plants.items():
    e1 = est_running_median(Xs)
    e2 = est_p25(Xs)
    res[key] = dict(
        f_mean=float(fs.mean()), f_std=float(fs.std()),
        E1=dict(rmse=rmse(e1, fs), rho=rho(e1, fs), mean=float(e1.mean())),
        E2=dict(rmse=rmse(e2, fs), rho=rho(e2, fs), mean=float(e2.mean())),
    )
    print(f"{key:12} n={len(fs)} fmean {fs.mean():.3f} | E1 rmse {res[key]['E1']['rmse']:.3f} rho {res[key]['E1']['rho']:.3f} "
          f"| E2 rmse {res[key]['E2']['rmse']:.3f} rho {res[key]['E2']['rho']:.3f}")

# ---------------- Q4: false-alarm floor on raw f=0 ----------------
print("\n=== Q4 false-alarm floor on raw windows (truth f=0) ===")
bg_big = BG[rng.choice(len(BG), 1500, replace=False)]
fa1 = est_running_median(bg_big)
fa2 = est_p25(bg_big)
res["false_alarm"] = dict(
    E1=dict(mean=float(fa1.mean()), p50=float(np.percentile(fa1, 50)), p90=float(np.percentile(fa1, 90)),
            rmse_vs0=rmse(fa1, np.zeros_like(fa1))),
    E2=dict(mean=float(fa2.mean()), p50=float(np.percentile(fa2, 50)), p90=float(np.percentile(fa2, 90)),
            rmse_vs0=rmse(fa2, np.zeros_like(fa2))),
)
print(f"E1: mean {res['false_alarm']['E1']['mean']:.3f} p50 {res['false_alarm']['E1']['p50']:.3f} "
      f"p90 {res['false_alarm']['E1']['p90']:.3f} rmse-vs-0 {res['false_alarm']['E1']['rmse_vs0']:.3f}")
print(f"E2: mean {res['false_alarm']['E2']['mean']:.3f} p50 {res['false_alarm']['E2']['p50']:.3f} "
      f"p90 {res['false_alarm']['E2']['p90']:.3f} rmse-vs-0 {res['false_alarm']['E2']['rmse_vs0']:.3f}")

json.dump(dict(kpi=kpi, results=res), open(OUT, "w"), indent=1)
print("\nsaved ->", OUT)
