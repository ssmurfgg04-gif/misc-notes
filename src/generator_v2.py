#!/usr/bin/env python3
"""Synthetic mixture factory v2 (R4) — f-grid corrected per benchmark anchor.

Changes vs v1 (R2, S1_logunif_z35 — DISCARDED, ~2.5x miscalibrated):
  - f ~ U{0, 0.1, 0.2, 0.3, 0.4}  (A16 RESTATED: statistically inferred from the
    all-zeros benchmark anchor E[f^2]=0.06058 (A15); NOT organiser-disclosed.
    Hedged against weighted-grid variants; any change must be surfaced to user.)
  - band-gain sigma ~ U{0, 0.05, 0.1, 0.2} per window (marginalized; replaces
    the guessed fixed sigma=0.18)
  - tilt sd ~ U{0, 0.1, 0.25} per window (marginalized; replaces fixed 0.25)

Unchanged structure (documented organiser transforms, plan.md A5/A13/A14):
  M = B + alpha*V, alpha = f/(1-f) * sum(B)/sum(V)  -> f exact at window level.
  Unit-energy refs (gain discarded), stretch/tile trajectory variation,
  per-band lognormal channel gains + tilt, real SA backgrounds w/ native NaN.

Build discipline (D2): one command, fixed seed, .sha256 sidecars + manifest.
"""
import argparse, glob, hashlib, json, os
import numpy as np
import pandas as pd

CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
BAND_COLS = [f"TOL_{c:.1f}" if c != int(c) else f"TOL_{int(c)}" for c in
             [round(10 ** (1.5 + 0.1 * k), 1) for k in range(25)]]

# --- f-grid scenarios (A16 restated) -------------------------------------
PRIMARY = {"name": "G_unif_04", "grid": [0.0, 0.1, 0.2, 0.3, 0.4],
           "p": [0.2, 0.2, 0.2, 0.2, 0.2]}          # E[f^2]=0.0600 ~ anchor 0.06058
HEDGE_LOW = {"name": "G_weighted_low", "grid": [0.0, 0.1, 0.2, 0.3, 0.4],
             "p": [0.30, 0.30, 0.20, 0.10, 0.10]}    # extra mass at 0 and 0.1
HEDGE_NONUNIF = {"name": "G_nonuniform", "grid": [0.0, 0.1, 0.2, 0.3, 0.4],
                 "p": [0.10, 0.15, 0.20, 0.25, 0.30]}  # mass toward 0.3/0.4
SIGMA_GRID = [0.0, 0.05, 0.1, 0.2]
TILT_SD_GRID = [0.0, 0.1, 0.25]


def sha256(path, buf=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()


def load_backgrounds(data_dir, per_site_cap=4000, seed=0, min_dur=55):
    """15-min SA background windows per site, native missingness preserved.
    Rows with dur < min_dur are excluded when dur exists (DATA_DICTIONARY caveat:
    16,896 rows are shorter than 55 s; a 'minute' is not guaranteed complete)."""
    rng = np.random.default_rng(seed)
    wins, meta = [], []
    for fp in sorted(glob.glob(os.path.join(data_dir, "acoustics", "*.parquet"))):
        site = os.path.basename(fp).replace(".parquet", "")
        df = pd.read_parquet(fp, columns=["t", "dur"] + BAND_COLS)
        df = df.sort_values("t").reset_index(drop=True)
        if "dur" in df.columns:
            df = df[(df["dur"].isna()) | (df["dur"] >= min_dur)].reset_index(drop=True)
        db = df[BAND_COLS].to_numpy(dtype=np.float64)
        ok = np.isfinite(db).all(axis=1)          # window needs all 25 bands per minute
        idx = np.where(ok)[0]
        if len(idx) < 20:
            continue
        sset = set(idx.tolist())
        run_ok = [s for s in idx[(idx >= 14) & (idx <= len(df) - 1)]
                  if all((s - k) in sset for k in range(15))]
        if not run_ok:
            continue
        run_ok = np.array(sorted(set(run_ok)))
        cap = min(per_site_cap, len(run_ok))
        pick = rng.choice(run_ok, size=cap, replace=False)
        for s in pick:
            wins.append(10 ** (db[s - 14:s + 1] / 10.0))
            meta.append({"site": site, "start_t": str(df["t"].iloc[s - 14])})
    return np.stack(wins), pd.DataFrame(meta)


def load_refs(refs_dir):
    refs = pd.read_parquet(os.path.join(refs_dir, "refs.parquet"))
    R = {}
    for uid, g in refs.groupby("clip_uid"):
        m = int(g["minute_idx"].max())
        R[str(uid)] = g.sort_values("minute_idx")["power"].to_numpy().reshape(m, 25).astype(np.float64)
    return R


def transform_reference(V, rng, minutes=15, sigma=None, tilt_sd=None):
    """Unit-energy reference adapted to `minutes` with marginalized variations."""
    m = V.shape[0]
    if m >= minutes:
        s0 = rng.integers(0, m - minutes + 1)
        W = V[s0:s0 + minutes]
    else:
        mode = rng.integers(0, 2)
        if mode == 0:   # linear stretch of the trajectory
            pos = np.linspace(0, m - 1, minutes)
            lo = np.floor(pos).astype(int); hi = np.ceil(pos).astype(int)
            w = (pos - lo)[:, None]
            W = V[lo] * (1 - w) + V[hi] * w
        else:           # cyclic tiling with per-cycle gains
            reps = int(np.ceil(minutes / m))
            tiled = np.concatenate([V * rng.uniform(0.6, 1.4) for _ in range(reps)], axis=0)[:minutes]
            W = tiled
    if sigma is None:
        sigma = float(rng.choice(SIGMA_GRID))
    if tilt_sd is None:
        tilt_sd = float(rng.choice(TILT_SD_GRID))
    tilt = rng.normal(0, tilt_sd, size=(25, 1))
    band_gain = rng.lognormal(0, sigma, size=(1, 25)) * \
        np.exp(tilt * (np.arange(25)[:, None] - 12) / 12).T
    W = W * band_gain
    W = np.clip(W, 0, None)
    W = W / max(W.sum(), 1e-30)                     # unit energy (gain discarded)
    return W, sigma, tilt_sd


def make_mixtures(bg_windows, bg_meta, refs, rng, n_samples, scen):
    rows_X, rows_f, rows_aux = [], [], []
    clip_ids = sorted(refs)
    sites = sorted(bg_meta["site"].unique())
    site_idx = {s: np.where(bg_meta["site"].to_numpy() == s)[0] for s in sites}
    grid = np.array(scen["grid"]); p = np.array(scen["p"]); p = p / p.sum()
    for j in range(n_samples):
        site = sites[rng.integers(0, len(sites))]
        bi = site_idx[site][rng.integers(0, len(site_idx[site]))]
        B = bg_windows[bi]
        uid = clip_ids[rng.integers(0, len(clip_ids))]
        ftrue = float(rng.choice(grid, p=p))
        V, sigma, tilt_sd = transform_reference(refs[uid], rng)
        if ftrue == 0.0:
            X = B.copy()
        else:
            alpha = ftrue / (1 - ftrue) * B.sum() / max(V.sum(), 1e-30)
            X = B + alpha * V
        rows_X.append(X.astype(np.float32))
        rows_f.append(ftrue)
        rows_aux.append({"site": site, "clip_uid": uid, "scenario": scen["name"],
                         "f_true": ftrue, "sigma": sigma, "tilt_sd": tilt_sd,
                         "bg_start": bg_meta["start_t"].iloc[bi]})
    return np.stack(rows_X), np.array(rows_f), pd.DataFrame(rows_aux)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="/home/z/my-project/data/South_African_Real_Acoustics")
    ap.add_argument("--refs_dir", default="/home/z/my-project/data/refs_vtuad_real")
    ap.add_argument("--out", default="/home/z/my-project/data/synth_v2")
    ap.add_argument("--n", type=int, default=24000)
    ap.add_argument("--per_site_cap", type=int, default=1500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--scenarios", default="primary,low,nonuniform",
                    help="comma set: primary,low,nonuniform")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    scen_map = {"primary": PRIMARY, "low": HEDGE_LOW, "nonuniform": HEDGE_NONUNIF}
    scens = [scen_map[s] for s in a.scenarios.split(",")]
    rng = np.random.default_rng(a.seed)

    print("loading backgrounds...", flush=True)
    bg, bg_meta = load_backgrounds(a.data_dir, a.per_site_cap, a.seed)
    print("background windows:", bg.shape, bg_meta["site"].value_counts().to_dict(), flush=True)
    refs = load_refs(a.refs_dir)
    print("refs:", len(refs), flush=True)

    manifest = {"seed": a.seed, "n_per_scenario": a.n, "scenarios": [],
                "inputs": {"sa_dir": a.data_dir, "refs_dir": a.refs_dir,
                           "sa_sha256": sha256(os.path.join(a.data_dir, "SHA256SUMS.txt")),
                           "refs_sha256": sha256(os.path.join(a.refs_dir, "refs.parquet"))}}
    for scen in scens:
        X, f, aux = make_mixtures(bg, bg_meta, refs, rng, a.n, scen)
        d = os.path.join(a.out, scen["name"])
        os.makedirs(d, exist_ok=True)
        np.save(f"{d}/X.npy", X)
        np.save(f"{d}/f.npy", f)
        aux.to_csv(f"{d}/aux.csv", index=False)
        bg_meta.to_csv(f"{d}/bg_meta.csv", index=False)
        rms = float(np.sqrt(np.mean(f ** 2)))
        ef2 = float(np.mean(f ** 2))
        rep = {"scenario": scen["name"], "n": int(len(f)), "rms_f": rms, "E_f2": ef2,
               "grid_mass": {str(g): float((f == g).mean()) for g in scen["grid"]},
               "accept_rms_0.24pm0.03": bool(0.21 <= rms <= 0.27),
               "accept_ef2_0.060pm0.006": bool(abs(ef2 - 0.060) < 0.006)}
        # sidecars
        for fn in ["X.npy", "f.npy", "aux.csv"]:
            with open(f"{d}/{fn}.sha256", "w") as fh:
                fh.write(sha256(f"{d}/{fn}") + "  " + fn + "\n")
        with open(f"{d}/gen_report.json", "w") as fh:
            json.dump(rep, fh, indent=2)
        manifest["scenarios"].append(rep)
        print(json.dumps(rep), flush=True)
    with open(f"{a.out}/build_manifest.json", "w") as fh:
        json.dump(manifest, fh, indent=2)
    with open(f"{a.out}/build_manifest.sha256", "w") as fh:
        fh.write(sha256(f"{a.out}/build_manifest.json") + "  build_manifest.json\n")
    print("saved ->", a.out, flush=True)


if __name__ == "__main__":
    main()
