#!/usr/bin/env python3
"""R8 build — T1 fingerprint conditioning + T2 wind-shape features.

Directive: user R9 greenlight (plan.md 7h/7i). Protocol per D20/R7-autopsy:
  - sub-interval planting (L in [3,12], random start)  = the smoking-gun recipe
  - H_A (ship ref) 50% / H_C (ambient-laden, amb_ratio in {0.5,1.0}) 50%
  - background-window-level group splits (seed 7, site-stratified)
  - clip-level holdout for val-side planting
  - calm emphasis 60/40 (A28: organiser beds calm-selected; test E5 mean 0.536
    says not too calm -> keep 40% non-calm hedge)

T1 (station-fingerprint conditioning, plan.md 7g #1):
  - bed P10 per band (dB) + SNR-normalized bands (band_mean_dB - bed_dB)
  - bed summaries: low level, HF level, spectral tilt
  - class-centroid distances in bed space (CLASS_A west/moored <-> G0,
    CLASS_B south-coast exposed <-> G1, CLASS_C harbour/industrial <-> G2,
    CLASS_D residual), per A60/A61 matching; test side uses the real
    G0/G1/G2 fingerprints in the same 25-dim space.

T2 (wind-shape features, plan.md 7g #2, A54 wind r>0.7 @ 1-2.5 kHz):
  - wind-band level (k15..19 = 1-2.5 kHz), LF/ship band (k0..6), ratios
  - excess-shape stats on bump minutes (vessel vs wind discrimination):
    lf_frac, wind_frac, excess tilt, ramp smoothness, onset sharpness
  - PCEN/LogTBN-flavoured trailing running-median baseline (R9-A steal,
    github.com/Jotels/CATFISH) -> share_pcen estimator variant
  - calibrated wind gate on E5 excess (r_lf_wind stat; calibrated on CAL pool
    only, evaluated on VAL pools; negative result reported honestly if no
    separation).

Outputs:
  data/train_v3/r8_pool/{X_train,X_cal,...}.npy + aux CSVs
  data/train_v3/r8_t1t2_report.json
  data/train_v3/r8_test_diag.npy (per-model test vectors for next round)
"""
import json, os, sys
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import roc_auc_score

BASE = "/home/z/my-project"
sys.path.insert(0, f"{BASE}/src")
from tournament import featurize
from generator_v2 import load_backgrounds, load_refs

WIN, NB = 15, 25
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
LOGC = np.log10(CENTRES)
LF, MID, WND, HF = slice(0, 7), slice(7, 15), slice(15, 20), slice(20, 25)
OUT = f"{BASE}/data/train_v3"
POOL = f"{OUT}/r8_pool"
os.makedirs(POOL, exist_ok=True)
R = {"protocol": "sub-interval L[3,12] + H_A/H_C mix + bg-window group split "
                 "(seed 7 site-stratified) + clip holdout (seed 101) + calm 60/40"}

CLASS_SITES = {  # A60/A61: test-group <-> train-site class mapping
    "A_west_moored_G0": ["13_Saldhana_Bay", "09_Fish_Hoek"],
    "B_southcoast_exposed_G1": ["07_St_Francis", "03_Cape_Recife"],
    "C_harbour_industrial_G2": ["01_Richards_Bay", "02_Durban", "05_St_Croix_Island"],
    "D_residual": ["04_Bird_Island", "06_Riy_Banks", "10_Sea_Point"],
}

# ---------------- data ----------------
print("loading backgrounds...", flush=True)
BGPath = f"{POOL}/BG_pool.npy"
if os.path.exists(BGPath):
    BG = np.load(BGPath)
    BGmeta = pd.read_csv(f"{POOL}/BG_meta.csv")
    print("BG pool restored from cache", flush=True)
else:
    BG, BGmeta = load_backgrounds(f"{BASE}/data/South_African_Real_Acoustics",
                                  per_site_cap=1500, seed=43)
    np.save(BGPath, BG.astype(np.float32))
    BGmeta.to_csv(f"{POOL}/BG_meta.csv", index=False)
sites = BGmeta["site"].to_numpy()
print("BG pool:", BG.shape, "| per-site:", pd.Series(sites).value_counts().to_dict(), flush=True)

rng = np.random.default_rng(7)
bg_split = np.zeros(len(BG), dtype="<U5")
for s in sorted(set(sites)):
    idx = np.where(sites == s)[0]
    rng.shuffle(idx)
    bg_split[idx[: int(0.8 * len(idx))]] = "train"
    bg_split[idx[int(0.8 * len(idx)):]] = "val"
pd.DataFrame({"bg_uid": np.arange(len(BG)), "site": sites, "split": bg_split}
             ).to_csv(f"{POOL}/bg_split_r8.csv", index=False)
gtr, gva = bg_split == "train", bg_split == "val"

refs = load_refs(f"{BASE}/data/refs_vtuad_real")           # vessel clips
bgrefs = pd.read_parquet(f"{BASE}/data/bg_refs.parquet")
BGclips = {int(u): g.sort_values("minute_idx")["power"].to_numpy()
           .reshape(int(g["minute_idx"].max()), NB).astype(float)
           for u, g in bgrefs.groupby("clip_uid") if g["minute_idx"].max() >= 2}
bgc = list(BGclips.values())
clip_uids = sorted(refs)
rng_c = np.random.default_rng(101)
val_clips = set(rng_c.choice(len(clip_uids), size=int(0.2 * len(clip_uids)), replace=False).tolist())
clips_tr = [refs[clip_uids[i]] for i in range(len(clip_uids)) if i not in val_clips]
clips_va = [refs[clip_uids[i]] for i in range(len(clip_uids)) if i in val_clips]
print(f"clips: train-side {len(clips_tr)} / val-side {len(clips_va)} (holdout)", flush=True)

# ---------------- calm mask (plant_protocol_v3, verbatim logic) ----------------
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
        Wdb = 10 * np.log10(np.where(obs & (W > 0), W, np.nan))
        rdb = np.nanpercentile(Wdb, 90, axis=0) - np.nanpercentile(Wdb, 10, axis=0)
        m[i] = (cv < cv_thr) and (np.nanmedian(rdb) < range_thr)
    return m

print("calm mask...", flush=True)
calmPath = f"{POOL}/calm_mask.npy"
if os.path.exists(calmPath):
    calm = np.load(calmPath)
else:
    calm = calm_mask(BG)
    np.save(calmPath, calm)
print(f"calm windows: {calm.sum()} / {len(BG)} ({calm.mean()*100:.0f}%)", flush=True)

# ---------------- planting (plant_protocol_v3, verbatim math) ----------------
def make_reference(clip, rng2, amb_clip=None, amb_ratio=0.0):
    m = clip.shape[0]
    L = min(m, int(rng2.integers(3, 13)))
    s0 = int(rng2.integers(0, m - L + 1))
    W = clip[s0:s0 + L].copy()
    start = int(rng2.integers(0, WIN - L + 1))
    if amb_clip is not None and amb_ratio > 0:
        am = amb_clip.shape[0]
        take = min(L, am)
        amb = amb_clip[int(rng2.integers(0, am - take + 1)):][:take].copy()
        if take < L:
            amb = np.concatenate([amb] * int(np.ceil(L / take)), axis=0)[:L]
        W = W + amb * (amb_ratio * max(W.sum(), 1e-30) / max(amb.sum(), 1e-30))
    return W, L, start

def plant(B, f_true, clip, rng2, amb_clip=None, amb_ratio=0.0):
    obs = np.isfinite(B)
    sumB = np.nansum(np.where(obs, B, 0.0))
    if f_true <= 0:
        return B.copy(), 0.0
    V, L, start = make_reference(clip, rng2, amb_clip, amb_ratio)
    Vfull = np.zeros((WIN, NB)); Vfull[start:start + L] = V[:L]
    Vfull = np.where(obs, Vfull, 0.0)
    alpha = f_true / (1 - f_true) * sumB / max(Vfull.sum(), 1e-30)
    Xv = Vfull * alpha
    X = np.where(obs, np.nan_to_num(B, nan=0.0) + Xv, np.nan)
    return X, float(np.nansum(Xv) / np.nansum(np.where(obs, X, 0.0)))

F_GRID = np.array([0.0, 0.1, 0.2, 0.3, 0.4])

def build_pool(name, bg_idx, n_max, clip_pool, seed, calm_frac=0.6, hc_frac=0.5):
    r2 = np.random.default_rng(seed)
    calm_idx = bg_idx[calm[bg_idx]]
    wild_idx = bg_idx[~calm[bg_idx]]
    n = min(n_max, max(len(calm_idx), len(wild_idx)))
    rows_X, rows_f, rows_aux = [], [], []
    for j in range(n):
        use_calm = (j % 10) < int(10 * calm_frac)
        src = calm_idx if (len(calm_idx) > 0 and use_calm) else wild_idx
        if len(src) == 0:
            src = calm_idx if len(calm_idx) > 0 else wild_idx
        bi = int(r2.choice(src))
        B = BG[bi]
        clip = clip_pool[int(r2.integers(0, len(clip_pool)))]
        f = float(r2.choice(F_GRID))
        if r2.random() < hc_frac:
            ar = float(r2.choice([0.5, 1.0]))
            X, fr = plant(B, f, clip, r2, bgc[int(r2.integers(0, len(bgc)))], ar)
            rec = "H_C"
        else:
            X, fr = plant(B, f, clip, r2)
            rec = "H_A"
        rows_X.append(X.astype(np.float32)); rows_f.append(fr)
        rows_aux.append({"pool": name, "bg_uid": bi, "site": sites[bi],
                         "calm": bool(calm[bi]), "recipe": rec, "f_true": fr})
        if (j + 1) % 2000 == 0:
            print(f"  {name}: {j+1}/{n}", flush=True)
    X = np.stack(rows_X); f = np.array(rows_f); aux = pd.DataFrame(rows_aux)
    np.save(f"{POOL}/X_{name}.npy", X); np.save(f"{POOL}/f_{name}.npy", f)
    aux.to_csv(f"{POOL}/aux_{name}.csv", index=False)
    print(f"pool {name}: {X.shape} E[f^2]={np.mean(f**2):.4f} mean(f)={f.mean():.3f}", flush=True)
    return X, f, aux

tr_idx = np.where(gtr)[0]
va_idx = np.where(gva)[0]
def have(name):
    return os.path.exists(f"{POOL}/X_{name}.npy")

X_tr, f_tr, aux_tr = (np.load(f"{POOL}/X_train.npy"), np.load(f"{POOL}/f_train.npy"),
                      pd.read_csv(f"{POOL}/aux_train.csv")) if have("train") else build_pool("train", tr_idx, 6000, clips_tr, seed=202)
X_cal, f_cal, aux_cal = (np.load(f"{POOL}/X_cal.npy"), np.load(f"{POOL}/f_cal.npy"),
                         pd.read_csv(f"{POOL}/aux_cal.csv")) if have("cal") else build_pool("cal", tr_idx, 1500, clips_tr, seed=303)

# class-matched val pools (calm only — A28 organiser-bed logic)
val_class = {}
for cls, slist in CLASS_SITES.items():
    idx = va_idx[np.isin(sites[va_idx], slist)]
    if len(idx) < 80:
        print(f"  !! {cls}: only {len(idx)} val bg windows", flush=True)
    val_class[cls] = idx
X_va, f_va, aux_va = (np.load(f"{POOL}/X_val_main.npy"), np.load(f"{POOL}/f_val_main.npy"),
                      pd.read_csv(f"{POOL}/aux_val_main.csv")) if have("val_main") else build_pool("val_main", va_idx, 800, clips_va, seed=404)
X_vc, f_vc, aux_vc = (np.load(f"{POOL}/X_val_calm.npy"), np.load(f"{POOL}/f_val_calm.npy"),
                      pd.read_csv(f"{POOL}/aux_val_calm.csv")) if have("val_calm") else build_pool("val_calm", va_idx[calm[va_idx]], 800, clips_va, seed=505)
X_cls, f_cls, aux_cls = {}, {}, {}
for cls, idx in val_class.items():
    nmv = f"val_{cls.split('_G')[0]}"
    if have(nmv):
        X_cls[cls], f_cls[cls], aux_cls[cls] = (np.load(f"{POOL}/X_{nmv}.npy"),
                                                np.load(f"{POOL}/f_{nmv}.npy"),
                                                pd.read_csv(f"{POOL}/aux_{nmv}.csv"))
    else:
        X_cls[cls], f_cls[cls], aux_cls[cls] = build_pool(nmv, idx, 300,
                                                          clips_va, seed=505 + sum(map(ord, cls)) % 97)

# ---------------- feature builders ----------------
def bed_profile(w):
    """per-band P10 dB across minutes (bump-robust bed estimate)."""
    W = np.where(np.isfinite(w) & (w > 0), w, np.nan)
    return 10 * np.log10(np.nanpercentile(W, 10, axis=0) + 1e-30)

def bed_tilt(p):
    ok = np.isfinite(p)
    if ok.sum() < 5:
        return 0.0
    A = np.polyfit(LOGC[ok], p[ok], 1)[0]
    return float(A)

# site/class fingerprints from TRAIN-side bg windows only (legal)
print("fingerprints...", flush=True)
site_fp = {}
for s in sorted(set(sites)):
    idx = np.where((sites == s) & gtr)[0]
    if len(idx) == 0:
        idx = np.where(sites == s)[0]
    site_fp[s] = np.nanmedian(np.stack([bed_profile(BG[i]) for i in idx[:500]]), axis=0)
class_fp = {c: np.nanmean(np.stack([site_fp[s] for s in sl]), axis=0)
            for c, sl in CLASS_SITES.items()}
np.save(f"{POOL}/site_fingerprints.npy", np.stack(list(site_fp.values())))

def t1_features(X):
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])            # (N,25) dB
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10 * np.log10(np.maximum(bmean, 1e-30))
    snr = bmean_dB - beds                                             # SNR-normalized bands
    feats = {"bed": beds, "snr": snr,
             "bed_low": beds[:, LF].mean(1)[:, None],
             "bed_hf": beds[:, HF].mean(1)[:, None],
             "bed_tilt": np.stack([bed_tilt(b) for b in beds])[:, None]}
    for c, fp in class_fp.items():
        feats[f"dist_{c.split('_G')[0]}"] = np.sqrt(
            np.nanmean((beds - fp[None, :]) ** 2, axis=1))[:, None]
    tops = np.stack([feats[f"dist_{c.split('_G')[0]}"][:, 0] for c in CLASS_SITES])
    srt = np.sort(tops, axis=0)
    feats["cls_margin"] = (srt[1] - srt[0])[:, None]
    return feats

def excess_stats(X):
    """E5 machinery + excess-shape stats. Returns f_e5, stats dict of arrays."""
    N = X.shape[0]
    f5 = np.zeros(N); f_pc = np.zeros(N)
    lf_frac = np.full(N, np.nan); wnd_frac = np.full(N, np.nan)
    exc_tilt = np.full(N, np.nan); smooth = np.full(N, np.nan)
    onset = np.full(N, np.nan); r_lf_wnd = np.full(N, np.nan)
    bump_any = np.zeros(N, bool)
    for i in range(N):
        W = X[i]; obs = np.isfinite(W)
        tot = np.nansum(np.where(obs, W, 0.0), axis=1)
        med = np.median(tot[tot > 0]) if (tot > 0).any() else 0.0
        bump = tot > 1.35 * med
        # --- E5 base ---
        if bump.sum() >= 2:
            quiet = ~bump & (tot > 0)
            if quiet.sum() >= 2:
                Bq = np.nanmedian(np.where(quiet[:, None], W, np.nan), axis=0)
                exc = np.where(obs & bump[:, None], np.maximum(W - Bq[None, :], 0.0), 0.0)
                totsum = np.nansum(np.where(obs, W, 0.0))
                f5[i] = np.clip(exc.sum() / totsum if totsum > 0 else 0.0, 0, 1)
                bump_any[i] = True
                E = exc.sum(0)                                    # (25,) excess spectrum
                Es = E.sum()
                if Es > 0:
                    lf_frac[i] = E[LF].sum() / Es
                    wnd_frac[i] = E[WND].sum() / Es
                    okb = E > 0
                    if okb.sum() >= 5:
                        exc_tilt[i] = np.polyfit(LOGC[okb], np.log10(E[okb]), 1)[0]
                    r_lf_wnd[i] = E[LF].sum() / max(E[WND].sum(), Es * 1e-6)
                    bm = bump & (tot > 0)
                    seg = tot[bm]
                    if len(seg) >= 3:
                        smooth[i] = np.std(np.diff(seg)) / max(np.std(seg), 1e-30)
                    onset[i] = (seg[0] - med) / max(med, 1e-30)
        # --- PCEN/LogTBN-flavoured trailing running-median baseline ---
        if (tot > 0).any():
            k = 5
            runmed = np.array([np.median(tot[max(0, j - k + 1):j + 1]) for j in range(WIN)])
            excm = np.maximum(tot - 1.15 * runmed, 0.0)
            f_pc[i] = np.clip(excm.sum() / max(tot.sum(), 1e-30), 0, 1)
    stats = {"lf_frac": lf_frac, "wnd_frac": wnd_frac, "exc_tilt": exc_tilt,
             "smooth": smooth, "onset": onset, "r_lf_wnd": r_lf_wnd,
             "bump_any": bump_any}
    return f5, f_pc, stats

def t2_features(X, stats):
    N = X.shape[0]
    beds = np.stack([bed_profile(X[i]) for i in range(N)])
    with np.errstate(invalid="ignore", divide="ignore"):
        bmean = np.nanmean(np.where(np.isfinite(X), X, np.nan), axis=1)
    bmean_dB = 10 * np.log10(np.maximum(bmean, 1e-30))
    feats = {"wind_bed": beds[:, WND].mean(1)[:, None],
             "wind_mean": bmean_dB[:, WND].mean(1)[:, None],
             "lf_wind_bed": beds[:, LF].mean(1)[:, None] - beds[:, WND].mean(1)[:, None],
             "lf_wind_mean": bmean_dB[:, LF].mean(1)[:, None] - bmean_dB[:, WND].mean(1)[:, None],
             "lf_frac": stats["lf_frac"][:, None], "wnd_frac": stats["wnd_frac"][:, None],
             "exc_tilt": stats["exc_tilt"][:, None], "smooth": stats["smooth"][:, None],
             "onset": stats["onset"][:, None],
             "log_r_lf_wnd": np.log10(np.maximum(stats["r_lf_wnd"], 1e-6))[:, None]}
    return feats

def assemble(X, base=True, t1=True, t2=True, stats=None):
    parts, names = [], []
    if base:
        Fb, nb = featurize(X)
        parts.append(Fb); names += nb
    if stats is None:
        _, _, stats = excess_stats(X)
    if t1:
        f1 = t1_features(X)
        for k, v in f1.items():
            parts.append(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0))
            names += [f"t1_{k}_{j}" for j in range(v.shape[1])]
    if t2:
        f2 = t2_features(X, stats)
        for k, v in f2.items():
            parts.append(np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0))
            names += [f"t2_{k}_{j}" for j in range(v.shape[1])]
    return np.hstack(parts), names, stats

# ---------------- estimators ----------------
def rmse(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return float(np.sqrt(np.mean((a - b) ** 2)))

def rho(a, b):
    return float(np.corrcoef(a, b)[0, 1])

def eval_block(tag, fs, preds):
    row = {"n": len(fs), "f_mean": float(np.mean(fs))}
    for k, p in preds.items():
        row[f"{k}_rmse"] = rmse(fs, p); row[f"{k}_rho"] = rho(p, fs)
        row[f"{k}_bias"] = float(np.mean(p - fs))
    R[tag] = row
    s = " | ".join(f"{k} rmse {row[f'{k}_rmse']:.4f} rho {row[f'{k}_rho']:.3f}" for k in preds)
    print(f"{tag:34} n={row['n']:4} {s}", flush=True)

# ---------------- CAL: gate calibration ----------------
print("\nCAL pool: gate separation stats...", flush=True)
f5_cal, fpc_cal, st_cal = excess_stats(X_cal)
stat = np.log10(np.maximum(st_cal["r_lf_wnd"], 1e-6))
pos = f_cal > 1e-9; neg = ~pos
bp = st_cal["bump_any"]
# separation of r_lf_wnd between planted-vessel windows and f=0 bump windows
auc_gate = float("nan")
if (pos & bp).sum() > 20 and (neg & bp).sum() > 20:
    y = np.concatenate([np.ones((pos & bp).sum()), np.zeros((neg & bp).sum())])
    s = np.concatenate([stat[pos & bp], stat[neg & bp]])
    auc_gate = roc_auc_score(y, s)
R["gate_cal"] = {"auc_vessel_vs_FA": auc_gate,
                 "n_vessel_bump": int((pos & bp).sum()), "n_FA_bump": int((neg & bp).sum()),
                 "stat_p50_vessel": float(np.nanmedian(stat[pos & bp])) if (pos & bp).any() else None,
                 "stat_p50_FA": float(np.nanmedian(stat[neg & bp])) if (neg & bp).any() else None}
print(json.dumps(R["gate_cal"]), flush=True)
# threshold: max-Youden on CAL bump windows
thr = None
if np.isfinite(auc_gate):
    grid = np.nanquantile(stat[bp][np.isfinite(stat[bp])], np.linspace(0.05, 0.95, 37))
    best = (-1, None)
    for t in grid:
        sens = np.nanmean(stat[pos & bp] >= t); fpr = np.nanmean(stat[neg & bp] >= t)
        j = sens - fpr
        if j > best[0]:
            best = (j, float(t))
    thr = best[1]
R["gate_cal"]["threshold"] = thr
print("gate threshold:", thr, flush=True)

def gated_e5(X, stats, thr):
    f5, _, _ = excess_stats(X)  # not used; we reuse passed stats shape
    return None  # placeholder replaced below

def e5_gated_from_stats(stats, thr):
    """zero-out f for windows whose excess is wind-dominated (stat < thr)."""
    out = stats["_f5"].copy()
    s = np.log10(np.maximum(stats["r_lf_wnd"], 1e-6))
    wind = np.isfinite(s) & (s < thr)
    out[wind] = 0.0
    return out

# ---------------- VAL evaluations ----------------
print("\nVAL evaluations...", flush=True)
def run_val(tag, X, f, aux):
    f5, fpc, st = excess_stats(X)
    st["_f5"] = f5
    preds = {"e5": f5, "e5pcen": fpc}
    if thr is not None:
        preds["e5gate"] = np.clip(e5_gated_from_stats(st, thr), 0, 1)
    Fb, _, _ = assemble(X, base=True, t1=False, t2=False, stats=st)
    Ft, _, _ = assemble(X, base=True, t1=True, t2=True, stats=st)
    preds["lgb_base"] = np.clip(mc_b.predict_proba(Fb)[:, 1] * mr_b.predict(Fb), 0, 1)
    preds["lgb_t1t2"] = np.clip(mc_t.predict_proba(Ft)[:, 1] * mr_t.predict(Ft), 0, 1)
    eval_block(tag, f, preds)
    return preds

# train LGBM heads
print("\ntraining LGBM two-heads...", flush=True)
Fb_tr, _, st_tr = assemble(X_tr, base=True, t1=False, t2=False)
Ft_tr, names_t, _ = assemble(X_tr, base=True, t1=True, t2=True)
R["n_features"] = {"base": int(Fb_tr.shape[1]), "t1t2": int(Ft_tr.shape[1]),
                   "t1t2_names_tail": names_t[Fb_tr.shape[1]:Fb_tr.shape[1] + 12]}

def twohead(Ftr, ftr, seed=0):
    y = (ftr > 1e-9).astype(int)
    mc = lgb.LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31,
                            random_state=seed, verbose=-1, n_jobs=4)
    mc.fit(Ftr, y)
    mr = lgb.LGBMRegressor(n_estimators=600, learning_rate=0.05, num_leaves=63,
                           subsample=0.9, colsample_bytree=0.9, min_child_samples=30,
                           random_state=seed, verbose=-1, n_jobs=4)
    mr.fit(Ftr[y == 1], ftr[y == 1])
    return mc, mr

mc_b, mr_b = twohead(Fb_tr, f_tr)
mc_t, mr_t = twohead(Ft_tr, f_tr)

run_val("VAL_main(allpool)_", X_va, f_va, aux_va)
run_val("VAL_calm_", X_vc, f_vc, aux_vc)
for cls in X_cls:
    run_val(f"VAL_class_{cls}_", X_cls[cls], f_cls[cls], aux_cls[cls])

# ---------------- TEST-side diagnostics (no submission change) ----------------
print("\nTEST diagnostics per G0/G1/G2...", flush=True)
test = pd.read_csv(f"{BASE}/data/Test.csv", dtype={"ID": str})
TX = test.drop(columns=["ID"]).to_numpy(float).reshape(-1, WIN, NB)
TX_lin = 10.0 ** (TX / 10.0)
m01m = np.isnan(TX[:, 0, :]).all(1); m15m = np.isnan(TX[:, 14, :]).all(1)
grp = np.where(m01m, "G1", np.where(m15m, "G2", "G0")).astype("<U2")
R["test_groups"] = {g: int((grp == g).sum()) for g in ["G0", "G1", "G2"]}

# real group fingerprints in the same 25-dim bed space
gfp = {}
for g in ["G0", "G1", "G2"]:
    idx = np.where(grp == g)[0]
    gfp[g] = np.nanmedian(np.stack([bed_profile(TX_lin[i]) for i in idx]), axis=0)
np.save(f"{POOL}/test_group_fingerprints.npy", np.stack(list(gfp.values())))

# class-vs-group agreement (mapping sanity check)
agree = {}
for g, fp in gfp.items():
    d = {c: float(np.sqrt(np.nanmean((fp - cfp) ** 2))) for c, cfp in class_fp.items()}
    agree[g] = sorted(d.items(), key=lambda kv: kv[1])
R["class_group_agreement"] = agree
print(json.dumps(agree), flush=True)

def test_diag(tag_fn):
    f5, fpc, st = excess_stats(TX_lin)
    st["_f5"] = f5
    out = {"e5": f5, "e5pcen": fpc}
    if thr is not None:
        out["e5gate"] = np.clip(e5_gated_from_stats(st, thr), 0, 1)
    Ft, _, _ = assemble(TX_lin, base=True, t1=True, t2=True, stats=st)
    out["lgb_t1t2"] = np.clip(mc_t.predict_proba(Ft)[:, 1] * mr_t.predict(Ft), 0, 1)
    diag = {}
    for g in ["G0", "G1", "G2"]:
        m = grp == g
        diag[g] = {k: {"mean": float(np.nanmean(v[m])), "p50": float(np.nanpercentile(v[m], 50)),
                       "p90": float(np.nanpercentile(v[m], 90))} for k, v in out.items()}
    # pinned-moment check on the E5 vector (informational)
    R[f"test_moments_{tag_fn}"] = {"E_mean": float(np.nanmean(f5)),
                                   "E_f2": float(np.nanmean(f5 ** 2)),
                                   "pinned_m2": 0.060581047570230605}
    np.savez(f"{OUT}/r8_test_diag.npz", **out, grp=grp)
    return diag

R["test_diag"] = test_diag("e5")
print(json.dumps(R["test_diag"], indent=1), flush=True)

json.dump(R, open(f"{OUT}/r8_t1t2_report.json", "w"), indent=1, default=float)
print("\nsaved ->", f"{OUT}/r8_t1t2_report.json", flush=True)
print("DONE", flush=True)
