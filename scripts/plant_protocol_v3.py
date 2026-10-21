#!/usr/bin/env python3
"""R7 plant protocol v3 — calm-bed validation of the bump-share estimator.

Hypothesis (organizer's seat): test background periods are CLEAN (no natural
vessels) — that's why they are withheld. Validating the estimator on the FULL
raw pool (ports full of ships) overstates the floor. So:

  1. calm pool  = raw windows with stable per-minute totals (ship-free-ish)
  2. plant sub-interval additions at known f into CALM windows
  3. evaluate E5 (quiet-baseline bump estimator) on calm-planted vs full pool
  4. preview on TEST + pinned-moment check E[f^2] ~= 0.0606
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
OUT = BASE / "data/train_v3/plant_v3_report.json"
WIN, NB = 15, 25
rng = np.random.default_rng(11)
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))

def comp_band_idx(tol_cols):
    freqs = np.array([float(c.replace("TOL_", "").replace("k", "e3")) for c in tol_cols])
    idx = []
    for cc in CENTRES:
        j = int(np.argmin(np.abs(np.log10(freqs) - np.log10(cc))))
        idx.append(j if abs(np.log10(freqs[j]) - np.log10(cc)) < 0.06 else -1)
    return idx

def load_site(path, cap=3000):
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
    wins = []
    i = 0
    while i + WIN <= len(V) and len(wins) < cap:
        if tm[i + WIN - 1] - tm[i] == WIN - 1 and len(set(rec[i:i + WIN])) == 1:
            w = V[i:i + WIN].astype(float)
            w = np.where(np.isfinite(w) & (w > -300) & (w < 300), w, np.nan)
            if np.isfinite(w).mean() > 0.9:
                wins.append(10.0 ** (w / 10.0))
            i += WIN
        else:
            i += 1
    return wins

bg_list = []
for f in sorted((BASE / "data/South_African_Real_Acoustics/South_African_Real_Acoustics/acoustics").glob("*.parquet")):
    bg_list += load_site(f)
BG = np.stack(bg_list)
print("BG pool:", BG.shape)

# calm selection: stable per-minute totals
def calm_mask(X, range_thr=9.0, cv_thr=0.5):
    m = np.zeros(len(X), bool)
    for i in range(len(X)):
        W = X[i]
        obs = np.isfinite(W)
        tot = np.nansum(np.where(obs, W, 0.0), axis=1)
        ok = tot > 0
        if ok.sum() < 10:
            continue
        cv = tot[ok].std() / tot[ok].mean()
        rdb = np.nanpercentile(10 * np.log10(np.where(obs & (W > 0), W, np.nan)), 90, axis=0) - \
              np.nanpercentile(10 * np.log10(np.where(obs & (W > 0), W, np.nan)), 10, axis=0)
        m[i] = (cv < cv_thr) and (np.nanmedian(rdb) < range_thr)
    return m

calm = calm_mask(BG)
print(f"calm windows: {calm.sum()} / {len(BG)} ({calm.mean()*100:.0f}%)")

refs = pd.read_parquet(BASE / "data/refs.parquet")
Vclips = {}
for uid, g in refs.groupby("clip_uid"):
    m = int(g["minute_idx"].max())
    if m >= 2:
        Vclips[int(uid)] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, NB).astype(float)
clips = sorted(Vclips)
bgrefs = pd.read_parquet(BASE / "data/bg_refs.parquet")
BGclips = {int(u): g.sort_values("minute_idx")["power"].to_numpy().reshape(int(g["minute_idx"].max()), NB).astype(float)
           for u, g in bgrefs.groupby("clip_uid") if g["minute_idx"].max() >= 2}
bgc = list(BGclips.values())

def make_reference(clip, minutes, L=None, amb_clip=None, amb_ratio=0.0):
    m = clip.shape[0]
    if L is None:
        L = min(m, int(rng.integers(3, 13)))
    L = min(L, m)
    s0 = int(rng.integers(0, m - L + 1))
    W = clip[s0:s0 + L].copy()
    start = int(rng.integers(0, minutes - L + 1))
    if amb_clip is not None and amb_ratio > 0:
        am = amb_clip.shape[0]
        take = min(L, am)
        amb = amb_clip[int(rng.integers(0, am - take + 1)):][:take].copy()
        if take < L:
            amb = np.concatenate([amb] * int(np.ceil(L / take)), axis=0)[:L]
        W = W + amb * (amb_ratio * max(W.sum(), 1e-30) / max(amb.sum(), 1e-30))
    return W, L, start

def plant(B, f_true, clip, amb_clip=None, amb_ratio=0.0):
    obs = np.isfinite(B)
    sumB = np.nansum(np.where(obs, B, 0.0))
    if f_true <= 0:
        return B.copy(), 0.0
    V, L, start = make_reference(clip, WIN, amb_clip=amb_clip, amb_ratio=amb_ratio)
    Vfull = np.zeros((WIN, NB)); Vfull[start:start + L] = V[:L]
    Vfull = np.where(obs, Vfull, 0.0)
    alpha = f_true / (1 - f_true) * sumB / max(Vfull.sum(), 1e-30)
    Xv = Vfull * alpha
    X = np.where(obs, np.nan_to_num(B, nan=0.0) + Xv, np.nan)
    return X, float(np.nansum(Xv) / np.nansum(np.where(obs, X, 0.0)))

# ---------- E5: quiet-baseline bump estimator ----------
def est_bump(X, bump_factor=1.35, min_bump_minutes=2):
    """Per-band quiet baseline from non-bump minutes; excess over baseline."""
    N = X.shape[0]
    f = np.zeros(N)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot = np.nansum(np.where(obs, W, 0.0), axis=1)
        med = np.median(tot[tot > 0]) if (tot > 0).any() else 0.0
        bump = tot > bump_factor * med
        if bump.sum() < min_bump_minutes:
            f[i] = 0.0; continue
        quiet = ~bump & (tot > 0)
        if quiet.sum() < 2:
            f[i] = 0.0; continue
        Bq = np.nanmedian(np.where(quiet[:, None], W, np.nan), axis=0)   # (25,) quiet baseline
        exc = np.where(obs & bump[:, None], np.maximum(W - Bq[None, :], 0.0), 0.0)
        totsum = np.nansum(np.where(obs, W, 0.0))
        f[i] = exc.sum() / totsum if totsum > 0 else 0.0
    return np.clip(f, 0, 1)

def rmse(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))

def rho(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[m], b[m])[0, 1]) if m.sum() > 3 else float("nan")

res = {}
def evaluate(name, Xs, fs):
    e = est_bump(Xs)
    r = dict(n=len(fs), f_mean=float(np.mean(fs)),
             rmse=rmse(e, fs), rho=rho(e, fs), mean=float(np.nanmean(e)),
             bias=float(np.nanmean(e - fs)))
    res[name] = r
    print(f"{name:22} n={r['n']:5} fmean {r['f_mean']:.3f} | E5 rmse {r['rmse']:.3f} rho {r['rho']:.3f} "
          f"mean {r['mean']:.3f} bias {r['bias']:+.3f}")
    return e

print("\n=== planted evaluation: calm beds vs full pool ===")
idx = rng.choice(np.where(calm)[0], 800, replace=False)
Xs, fs = [], []
for i in idx:
    f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
    X, fr = plant(BG[i], f, Vclips[clips[rng.integers(0, len(clips))]])
    Xs.append(X); fs.append(fr)
evaluate("calm_sub_HA", np.stack(Xs), np.array(fs))

Xs2, fs2 = [], []
for i in idx[:400]:
    f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
    X, fr = plant(BG[i], f, Vclips[clips[rng.integers(0, len(clips))]],
                  bgc[rng.integers(0, len(bgc))], 1.0)
    Xs2.append(X); fs2.append(fr)
evaluate("calm_sub_HC", np.stack(Xs2), np.array(fs2))

idx_all = rng.choice(len(BG), 800, replace=False)
Xs3, fs3 = [], []
for i in idx_all:
    f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
    X, fr = plant(BG[i], f, Vclips[clips[rng.integers(0, len(clips))]])
    Xs3.append(X); fs3.append(fr)
evaluate("allpool_sub_HA", np.stack(Xs3), np.array(fs3))

print("\n=== false-alarm floor on calm windows (f=0 truth) ===")
fa = est_bump(BG[idx[:800]])
res["false_alarm_calm"] = dict(mean=float(np.nanmean(fa)), p50=float(np.nanpercentile(fa, 50)),
                               p90=float(np.nanpercentile(fa, 90)), rmse_vs0=rmse(fa, np.zeros_like(fa)))
print(f"calm: mean {res['false_alarm_calm']['mean']:.3f} p50 {res['false_alarm_calm']['p50']:.3f} "
      f"p90 {res['false_alarm_calm']['p90']:.3f} rmse-vs-0 {res['false_alarm_calm']['rmse_vs0']:.3f}")

print("\n=== TEST preview + pinned-moment check ===")
test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)
e_test = est_bump(10.0 ** (TX / 10.0))
m2 = (1 - 0.753867825) ** 2
res["test_E5"] = dict(mean=float(np.nanmean(e_test)), std=float(np.nanstd(e_test)),
                      e_f2=float(np.nanmean(e_test ** 2)), pinned_m2=m2,
                      q={str(q): float(np.nanpercentile(e_test, q)) for q in [0, 10, 25, 50, 75, 90, 100]})
print(f"E5 on test: mean {res['test_E5']['mean']:.3f} std {res['test_E5']['std']:.3f} "
      f"E[f2] {res['test_E5']['e_f2']:.4f} vs pinned {m2:.4f}")
print("quantiles:", {k: round(v, 3) for k, v in res["test_E5"]["q"].items()})
np.save(BASE / "data/train_v3/est_e5_test_share.npy", e_test)

json.dump(res, open(OUT, "w"), indent=1)
print("\nsaved ->", OUT)
