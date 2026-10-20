#!/usr/bin/env python3
"""Synthetic mixture factory v1 (documented organiser transforms).

M = B + alpha*V on linear energy over observed cells; target
f = sum(alpha*V) / sum(M) on the SAME cells.

Reference transforms replicating the starter-notebook notices:
  - gain discarded (unit-energy normalisation; scale set by f)
  - time trajectory varied (stretch/tile with randomised envelope)
  - relative channel/energy varied (per-band random lognormal gains + tilt)

Background: real SA parquet minutes, grouped into 15-minute windows with the
site's own missingness pattern. Split keys: background (site, period) and
reference clip -> grouped holdout.
"""
import numpy as np
import pandas as pd
import glob, os, json, argparse

CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
BAND_COLS = [f"TOL_{c:.1f}" if c != int(c) else f"TOL_{int(c)}" for c in
             [round(10 ** (1.5 + 0.1 * k), 1) for k in range(25)]]


def load_backgrounds(data_dir, per_site_cap=4000, seed=0):
    """Sample 15-minute windows per site, preserving missingness; returns
    windows (N,15,25) linear power + meta (site, start_iso)."""
    rng = np.random.default_rng(seed)
    wins, meta = [], []
    for fp in sorted(glob.glob(os.path.join(data_dir, "acoustics", "*.parquet"))):
        site = os.path.basename(fp).replace(".parquet", "")
        df = pd.read_parquet(fp, columns=["t"] + BAND_COLS)
        df = df.sort_values("t").reset_index(drop=True)
        db = df[BAND_COLS].to_numpy(dtype=np.float64)
        ok = np.isfinite(db).all(axis=1)          # window needs all 25 bands per minute
        # candidate starts: runs of 15 consecutive complete minutes
        idx = np.where(ok)[0]
        if len(idx) < 20:
            continue
        starts = idx[(idx >= 14) & (idx <= len(df) - 1)]
        # choose starts whose full 15-min run is complete
        run_ok = []
        sset = set(idx.tolist())
        for s in starts:
            if all((s - k) in sset for k in range(15)):
                run_ok.append(s)
        if not run_ok:
            continue
        run_ok = np.array(sorted(set(run_ok)))
        cap = min(per_site_cap, len(run_ok))
        pick = rng.choice(run_ok, size=cap, replace=False)
        for s in pick:
            block = 10 ** (db[s - 14:s + 1] / 10.0)      # (15,25) linear
            wins.append(block)
            meta.append({"site": site, "start_t": str(df["t"].iloc[s - 14])})
    return np.stack(wins), pd.DataFrame(meta)


def load_refs(refs_dir):
    refs = pd.read_parquet(os.path.join(refs_dir, "refs.parquet"))
    meta = pd.read_parquet(os.path.join(refs_dir, "refs_meta.parquet"))
    R = {}
    for uid, g in refs.groupby("clip_uid"):
        m = int(g["minute_idx"].max())
        R[uid] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, 25).astype(np.float64)
    return R, meta


def transform_reference(V, rng, minutes=15):
    """Unit-energy reference adapted to `minutes` with documented variations."""
    m = V.shape[0]
    if m >= minutes:
        s0 = rng.integers(0, m - minutes + 1)
        W = V[s0:s0 + minutes]
    else:
        mode = rng.integers(0, 2)
        if mode == 0:   # linear stretch of the trajectory (time-trajectory variation)
            pos = np.linspace(0, m - 1, minutes)
            lo = np.floor(pos).astype(int); hi = np.ceil(pos).astype(int)
            w = (pos - lo)[None, :, None]
            W = V[lo] * (1 - w) + V[hi] * w
        else:           # cyclic tiling with per-cycle gains
            reps = int(np.ceil(minutes / m))
            tiled = np.concatenate([V * rng.uniform(0.6, 1.4) for _ in range(reps)], axis=0)[:minutes]
            W = tiled
    # channel/energy variation: per-band lognormal gain + random tilt
    tilt = rng.normal(0, 0.25, size=(25, 1))
    band_gain = rng.lognormal(0, 0.18, size=(1, 25)) * np.exp(tilt * (np.arange(25)[:, None] - 12) / 12).T
    W = W * band_gain
    W = np.clip(W, 0, None)
    W = W / W.sum()                                 # unit energy (gain discarded)
    return W


def make_mixtures(bg_windows, bg_meta, refs, rng, n_samples, scenarios,
                  clip_ids=None, sites=None):
    """Returns X (N,15,25) linear, f (N,), aux rows (site, clip, scenario, true f)."""
    rows_X, rows_f, rows_aux = [], [], []
    clip_ids = clip_ids or sorted(refs)
    sites = sites or sorted(bg_meta["site"].unique())
    site_idx = {s: np.where(bg_meta["site"].to_numpy() == s)[0] for s in sites}
    per_scen = n_samples // len(scenarios)
    for scen in scenarios:
        zero_rate, lo, hi = scen["zero_rate"], scen["lo"], scen["hi"]
        for j in range(per_scen):
            site = sites[rng.integers(0, len(sites))]
            bi = site_idx[site][rng.integers(0, len(site_idx[site]))]
            B = bg_windows[bi]
            obs = np.isfinite(B)
            uid = clip_ids[rng.integers(0, len(clip_ids))]
            V = transform_reference(refs[uid], rng)
            if rng.random() < zero_rate:
                X = B.copy(); ftrue = 0.0
            else:
                ftrue = float(10 ** rng.uniform(np.log10(lo), np.log10(hi)))
                # alpha such that sum(alpha*V)/sum(B+alpha*V) = f  -> alpha = f/(1-f) * sum(B)/sum(V)
                alpha = ftrue / (1 - ftrue) * B.sum() / max(V.sum(), 1e-30)
                X = B + alpha * V
            rows_X.append(X.astype(np.float32))
            rows_f.append(ftrue)
            rows_aux.append({"site": site, "clip_uid": uid, "scenario": scen["name"],
                             "f_true": ftrue, "bg_start": bg_meta["start_t"].iloc[bi]})
    return np.stack(rows_X), np.array(rows_f), pd.DataFrame(rows_aux)


SCENARIOS = [
    {"name": "S1_logunif_z35", "zero_rate": 0.35, "lo": 1e-4, "hi": 0.6},
    {"name": "S2_unif_z25",    "zero_rate": 0.25, "lo": 1e-3, "hi": 0.5},
    {"name": "S3_low_z45",     "zero_rate": 0.45, "lo": 1e-4, "hi": 0.2},
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="/home/z/my-project/data/South_African_Real_Acoustics")
    ap.add_argument("--refs_dir", default="/home/z/my-project/data/refs_physics")
    ap.add_argument("--out", default="/home/z/my-project/data/synth_v1")
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--per_site_cap", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)
    print("loading backgrounds...", flush=True)
    bg, bg_meta = load_backgrounds(a.data_dir, a.per_site_cap, a.seed)
    print("background windows:", bg.shape, bg_meta["site"].value_counts().to_dict(), flush=True)
    print("loading refs...", flush=True)
    refs, rmeta = load_refs(a.refs_dir)
    print("refs:", len(refs), flush=True)
    X, f, aux = make_mixtures(bg, bg_meta, refs, rng, a.n, SCENARIOS)
    np.save(f"{a.out}/X.npy", X)
    np.save(f"{a.out}/f.npy", f)
    aux.to_csv(f"{a.out}/aux.csv", index=False)
    bg_meta.to_csv(f"{a.out}/bg_meta.csv", index=False)
    print("saved:", X.shape, "f quantiles:", {q: round(float(np.quantile(f, q)), 4) for q in [0, .25, .5, .75, 1]})


if __name__ == "__main__":
    main()
