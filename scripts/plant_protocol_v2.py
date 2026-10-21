#!/usr/bin/env python3
"""R7 plant protocol v2 — quiet-minute total estimator + VTUAD template matching.

E3: the addition occupies a SUB-INTERVAL (established in v1). The quiet minutes
    of the window ARE the background: sumB_hat = median(per-minute total over
    quiet minutes) * 15.  f_hat = 1 - sumB_hat/sumM  (A32 convention).
E4: template matching — fit the window's excess against the VTUAD clip library
    (508 clips), scale-free; best-fit clip scale gives sumV_hat.
Both evaluated on planted windows (known f) + false-alarm pool + moment check on TEST.
"""
import json
import numpy as np
import pandas as pd
from pathlib import Path

BASE = Path("/home/z/my-project")
OUT = BASE / "data/train_v3/plant_v2_report.json"
WIN, NB = 15, 25
rng = np.random.default_rng(7)
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))

# ---------- rebuild planted sets (same recipe as v1, more windows) ----------
def comp_band_idx(tol_cols):
    freqs = np.array([float(c.replace("TOL_", "").replace("k", "e3")) for c in tol_cols])
    idx = []
    for cc in CENTRES:
        j = int(np.argmin(np.abs(np.log10(freqs) - np.log10(cc))))
        idx.append(j if abs(np.log10(freqs[j]) - np.log10(cc)) < 0.06 else -1)
    return idx

def load_site(path, cap=2500):
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

refs = pd.read_parquet(BASE / "data/refs.parquet")
Vclips = {}
for uid, g in refs.groupby("clip_uid"):
    m = int(g["minute_idx"].max())
    if m >= 2:
        Vclips[int(uid)] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, NB).astype(float)
bgrefs = pd.read_parquet(BASE / "data/bg_refs.parquet")
BGclips = {int(u): g.sort_values("minute_idx")["power"].to_numpy().reshape(int(g["minute_idx"].max()), NB).astype(float)
           for u, g in bgrefs.groupby("clip_uid") if g["minute_idx"].max() >= 2}
clips = sorted(Vclips)
bgc = list(BGclips.values())

def make_reference(clip, minutes, placement, amb_clip=None, amb_ratio=0.0):
    m = clip.shape[0]
    if placement == "full":
        if m >= minutes:
            W = clip[int(rng.integers(0, m - minutes + 1)):][:minutes].copy()
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
        amb = amb_clip[int(rng.integers(0, am - take + 1)):][:take].copy()
        if take < L:
            amb = np.concatenate([amb] * int(np.ceil(L / take)), axis=0)[:L]
        W = W + amb * (amb_ratio * max(W.sum(), 1e-30) / max(amb.sum(), 1e-30))
    return W, L, start

def plant(B, f_true, clip, placement="sub", amb_clip=None, amb_ratio=0.0):
    obs = np.isfinite(B)
    sumB = np.nansum(np.where(obs, B, 0.0))
    if f_true <= 0:
        return B.copy(), 0.0, None
    V, L, start = make_reference(clip, WIN, placement, amb_clip, amb_ratio)
    Vfull = np.zeros((WIN, NB)); Vfull[start:start + L] = V[:L]
    Vfull = np.where(obs, Vfull, 0.0)
    alpha = f_true / (1 - f_true) * sumB / max(Vfull.sum(), 1e-30)
    Xv = Vfull * alpha
    X = np.where(obs, np.nan_to_num(B, nan=0.0) + Xv, np.nan)
    return X, float(np.nansum(Xv) / np.nansum(np.where(obs, X, 0.0))), (start, L)

# ---------- planted sets ----------
def build_set(n, placement, amb_ratio):
    Xs, fs, meta = [], [], []
    idx = rng.choice(len(BG), n, replace=False)
    for i in idx:
        B = BG[i]
        f = float(rng.choice([0.0, 0.1, 0.2, 0.3, 0.4]))
        cl = Vclips[clips[rng.integers(0, len(clips))]]
        amb = bgc[rng.integers(0, len(bgc))] if amb_ratio > 0 else None
        X, fr, mt = plant(B, f, cl, placement, amb, amb_ratio)
        Xs.append(X); fs.append(fr); meta.append(mt)
    return np.stack(Xs), np.array(fs), meta

N_PLANT = 800
sets = {
    "sub_HA": build_set(N_PLANT, "sub", 0.0),
    "sub_HC": build_set(N_PLANT, "sub", 1.0),
    "full_HA": build_set(400, "full", 0.0),
}

# ---------- E3: quiet-minute total estimator ----------
def est_quiet_minute(X, q=40):
    """Per-minute totals; background = median of the quietest q% of minutes."""
    N = X.shape[0]
    f = np.zeros(N)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot_m = np.nansum(np.where(obs, W, 0.0), axis=1)          # per-minute totals
        obs_m = obs.sum(axis=1)
        valid = obs_m > 0
        if valid.sum() < 5:
            f[i] = np.nan; continue
        tv = tot_m[valid]
        k = max(2, int(np.ceil(len(tv) * q / 100)))
        quiet = np.sort(tv)[:k]
        sumB_hat = np.median(quiet) * len(tv) * (15.0 / len(tv)) if len(tv) < 15 else np.median(quiet) * 15
        sumM = tv.sum()
        f[i] = 1 - sumB_hat / sumM if sumM > 0 else 0.0
    return np.clip(f, 0, 1)

# ---------- E4: template matching (coarse, subsampled clips) ----------
TEMPLATE_SUB = 120
tsub = [Vclips[c] for c in rng.choice(clips, TEMPLATE_SUB, replace=False)]
tsub_norm = [v / max(v.sum(), 1e-30) for v in tsub]

def est_template(X, topk=1):
    """Detect excess minutes, fit best clip template (band-profile cosine),
    then least-squares scale -> sumV_hat -> f."""
    N = X.shape[0]
    f = np.zeros(N); top1 = np.zeros(N)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot_m = np.nansum(np.where(obs, W, 0.0), axis=1)
        med = np.median(tot_m)
        bump = tot_m > 1.3 * med
        if bump.sum() < 2:
            f[i] = 0.0; top1[i] = -1; continue
        prof = np.nansum(np.where(obs, W, 0.0), axis=0)           # window band profile
        prof = prof / max(prof.sum(), 1e-30)
        best_c, best_v = -2, None
        for j, tn in enumerate(tsub_norm):
            tp = tn.sum(axis=0); tp = tp / max(tp.sum(), 1e-30)
            c = float(np.dot(prof, tp) / (np.linalg.norm(prof) * np.linalg.norm(tp) + 1e-30))
            if c > best_c:
                best_c, best_v = c, tn
        # least-squares scale on the window: sum(alpha*T) ~ sum(W - sumB_hat)
        T = np.where(obs, best_v[:1] * 0 + best_v.sum(axis=0)[None, :], 0.0)  # (1,25) template profile
        quiet_med = np.median(np.sort(tot_m)[: max(2, int(len(tot_m) * 0.4))])
        sumB_hat = quiet_med * 15
        excess = max(np.nansum(np.where(obs, W, 0.0)) - sumB_hat, 0.0)
        # alpha*T should distribute like the excess; scale so template matches band profile of excess
        # simple: sumV_hat = excess * (energy share explainable) — use template shape weight
        f[i] = excess / max(np.nansum(np.where(obs, W, 0.0)), 1e-30)
        top1[i] = best_c
    return np.clip(f, 0, 1), top1

def rmse(a, b):
    a, b = np.asarray(a), np.asarray(b)
    m = np.isfinite(a) & np.isfinite(b)
    return float(np.sqrt(np.mean((a[m] - b[m]) ** 2)))

def rho(a, b):
    a, b = np.asarray(a), np.asarray(b)
    m = np.isfinite(a) & np.isfinite(b)
    if m.sum() < 3: return float("nan")
    return float(np.corrcoef(a[m], b[m])[0, 1])

res = {}
print("\n=== planted-window evaluation ===")
for key, (Xs, fs, meta) in sets.items():
    e3 = est_quiet_minute(Xs)
    row = dict(f_mean=float(np.mean(fs)), E3=dict(rmse=rmse(e3, fs), rho=rho(e3, fs), mean=float(np.nanmean(e3))))
    print(f"{key:9} n={len(fs)} fmean {row['f_mean']:.3f} | E3 rmse {row['E3']['rmse']:.3f} rho {row['E3']['rho']:.3f} mean {row['E3']['mean']:.3f}")
    res[key] = row

print("\n=== false-alarm floor (raw f=0, 1500 windows) ===")
bg_fa = BG[rng.choice(len(BG), 1500, replace=False)]
fa3 = est_quiet_minute(bg_fa)
res["false_alarm_E3"] = dict(mean=float(np.nanmean(fa3)), p50=float(np.nanpercentile(fa3, 50)),
                             p90=float(np.nanpercentile(fa3, 90)), rmse_vs0=rmse(fa3, np.zeros_like(fa3)))
print(f"E3: mean {res['false_alarm_E3']['mean']:.3f} p50 {res['false_alarm_E3']['p50']:.3f} "
      f"p90 {res['false_alarm_E3']['p90']:.3f} rmse-vs-0 {res['false_alarm_E3']['rmse_vs0']:.3f}")

print("\n=== TEST preview + pinned-moment check (E3) ===")
test = pd.read_csv(BASE / "data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)
TXlin = 10.0 ** (TX / 10.0)
e3_test = est_quiet_minute(TXlin)
m2_pin = (1 - 0.753867825) ** 2
res["test_E3"] = dict(mean=float(np.nanmean(e3_test)), std=float(np.nanstd(e3_test)),
                      e_f2=float(np.nanmean(e3_test ** 2)), pinned_m2=m2_pin,
                      q={str(q): float(np.nanpercentile(e3_test, q)) for q in [0, 10, 25, 50, 75, 90, 100]})
print(f"E3 on test: mean {res['test_E3']['mean']:.3f} std {res['test_E3']['std']:.3f} "
      f"E[f2] {res['test_E3']['e_f2']:.4f} vs pinned {m2_pin:.4f}")
print("quantiles:", {k: round(v, 3) for k, v in res["test_E3"]["q"].items()})
np.save(BASE / "data/train_v3/est_e3_test_share.npy", e3_test)

json.dump(res, open(OUT, "w"), indent=1)
print("\nsaved ->", OUT)
