#!/usr/bin/env python3
"""synth_v3_mixed.py — recipe-robust synthetic training set (R4/R5 bridge).

Motivation (see plan.md 6g + data/train_v2/recipe_discrimination.json):
The effective organiser recipe is contested between
  H_A vessel-shaped addition   M = B + alpha*V (R2/R4 generator; cell-9 reading)
  H_B background-matched       M = B/(1-f)    (hunt-note plant-protocol claim)
Independent checks: planted H_A additions into real backgrounds are detected at
99.5% (model works), but raw test reads 98.7% PRESENT under the same head while
the hunt-note's detector reads 98% ABSENT -> detector outputs on test are
condition-dominated (test periods are louder/flatter than the pool tail).
Dominant strategy: train on a MIX of both recipes (+ loud-tail condition
oversampling) so the two-head learns whichever signal exists. Additionally
train lock-v2: conditional sumB-hat regressor on REAL pool backgrounds
(shape+cluster -> sumB), the H_B-optimal estimator, exact under H_B.

Targets stay exact by construction: H_A: alpha = f/(1-f) sumB/sumV.
                                             H_B: M = B/(1-f) => f = 1 - sumB/sumM.
"""
import argparse, hashlib, json, os
import numpy as np
import pandas as pd

def sha256(path, buf=1 << 22):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(buf), b""):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data_dir", default="/home/z/my-project/data/South_African_Real_Acoustics")
    ap.add_argument("--refs_dir", default="/home/z/my-project/data/refs_vtuad_real")
    ap.add_argument("--out", default="/home/z/my-project/data/synth_v3_mixed")
    ap.add_argument("--n", type=int, default=24000)
    ap.add_argument("--seed", type=int, default=43)
    ap.add_argument("--p_hb", type=float, default=0.5, help="mass on background-matched recipe")
    ap.add_argument("--loud_tail_frac", type=float, default=0.35,
                    help="fraction of bg draws taken from the loud tail (test-period mimic)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rng = np.random.default_rng(a.seed)

    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from generator_v2 import load_backgrounds, load_refs, transform_reference, PRIMARY, SIGMA_GRID, TILT_SD_GRID
    F_GRID = np.array(PRIMARY["grid"])

    bg, bg_meta = load_backgrounds(a.data_dir, per_site_cap=1500, seed=a.seed)
    sums = bg.astype(np.float64).sum(axis=(1, 2))
    sum_db = 10 * np.log10(sums)
    thr = np.quantile(sum_db, 1 - 0.25)          # loud tail = top quartile of window level
    loud_idx = np.where(sum_db >= thr)[0]
    print(f"bg windows {bg.shape} | loud tail (>= p75 {thr:.2f} dB): {len(loud_idx)}", flush=True)
    refs = load_refs(a.refs_dir)
    clip_ids = sorted(refs)

    X = np.empty((a.n, 15, 25), dtype=np.float32)
    f = np.empty(a.n)
    aux = []
    for i in range(a.n):
        # condition draw: loud-tail oversampling (test periods sit in the loud tail)
        if rng.random() < a.loud_tail_frac:
            bi = int(loud_idx[rng.integers(len(loud_idx))])
        else:
            bi = int(rng.integers(len(bg)))
        B = bg[bi]
        f_i = float(rng.choice(F_GRID))
        recipe = "H_B" if rng.random() < a.p_hb else "H_A"
        if f_i == 0.0:
            X[i] = B
        elif recipe == "H_B":
            X[i] = B / (1.0 - f_i)
        else:
            uid = clip_ids[rng.integers(len(clip_ids))]
            V, sigma, tilt_sd = transform_reference(refs[uid], rng)
            alpha = f_i / (1 - f_i) * B.sum() / max(V.sum(), 1e-30)
            X[i] = B + alpha * V
        f[i] = f_i
        aux.append({"window_id": i, "f_true": f_i, "recipe": recipe,
                    "site": bg_meta['site'].iloc[bi], "bg_start": bg_meta['start_t'].iloc[bi],
                    "loud_tail": bool(sum_db[bi] >= thr)})
        if (i + 1) % 6000 == 0:
            print(f"  {i+1}/{a.n}", flush=True)

    np.save(f"{a.out}/X.npy", X)
    np.save(f"{a.out}/f.npy", f)
    pd.DataFrame(aux).to_csv(f"{a.out}/aux.csv", index=False)
    rms = float(np.sqrt(np.mean(f ** 2)))
    rep = {"n": a.n, "rms_f": rms, "E_f2": float(np.mean(f ** 2)),
           "p_HB": a.p_hb, "loud_tail_frac": a.loud_tail_frac, "seed": a.seed,
           "grid_mass": {str(g): float((f == g).mean()) for g in F_GRID}}
    with open(f"{a.out}/gen_report.json", "w") as fh:
        json.dump(rep, fh, indent=1)
    with open(f"{a.out}/X.npy.sha256", "w") as fh:
        fh.write(sha256(f"{a.out}/X.npy") + "  X.npy\n")
    print(json.dumps(rep), flush=True)

    # ---- lock-v2 training data: conditional sumB regressor on REAL pool backgrounds
    # (no synthesis: pure background windows, target = observed sumB; features = shape)
    from tournament import featurize as feat2
    Fb, bnames = feat2(bg)                       # (M, F)
    np.save(f"{a.out}/bgfeat.npy", Fb)
    pd.DataFrame({"sumB": sums, "site": bg_meta["site"]}).to_csv(f"{a.out}/bg_sums.csv", index=False)
    print("lock-v2 training tables saved (bgfeat, bg_sums)", flush=True)

if __name__ == "__main__":
    main()
