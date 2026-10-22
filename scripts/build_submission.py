#!/usr/bin/env python3
"""build_submission.py — THE single gate for every future submission.

Fixes silent issues found in R10 code review:
  (1) wrong-column reads (share vs score col — score has zero weight, A33)
  (2) authoritative outputs scattered outside repo tree
  (3) unledgered / untraced submission files
  (4) point-mass / floor collapse detection (33.8% at 0.07154 in r7_v3_k045)

Usage:
  python scripts/build_submission.py --name r7_v3_k045 \
      --vector workspace/misc-notes-data/submissions/submission_r7_v3_k045.csv
  python scripts/build_submission.py --name r8b_v1 --npz data/train_v3/r8b_test_diag.npz \
      --key softfloor --shrink 0.45
  python scripts/build_submission.py --name X --csv path.csv --repin   # re-solve a,gamma

Always: asserts ID order == data/Test.csv order, share col finite in [0,1],
1500 rows; prints point-mass census + moments; writes download/<name>.csv,
appends sha256 to download/backups/LEDGER.sha256 + submission ledger line;
NEVER overwrites an existing file without --force.
"""
import argparse, hashlib, json, os, sys
import numpy as np
import pandas as pd

BASE = "/home/z/my-project"
TEST = f"{BASE}/data/Test.csv"
DL = f"{BASE}/download"
MU, E_F2 = 0.1300757620833333, 0.06057997689999998

def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()

def moment_pin(v):
    """re-solve p=a*v^gamma s.t. E[p]=mu, E[p^2]=E_f2 (monotone, needs v>0)."""
    v = np.asarray(v, float)
    assert (v > 0).all(), "repin needs strictly positive vector; use softfloor first"
    lo, hi = 0.5, 20.0
    tgt = E_F2 / MU**2
    def G(g): return np.mean(v**(2*g)) / np.mean(v**g)**2
    for _ in range(200):
        mid = 0.5*(lo+hi)
        if G(mid) < tgt: lo = mid
        else: hi = mid
    gam = 0.5*(lo+hi)
    a = MU / np.mean(v**gam)
    return a*v**gam, a, gam

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--csv"); ap.add_argument("--npz"); ap.add_argument("--key")
    ap.add_argument("--shrink", type=float, default=None)
    ap.add_argument("--repin", action="store_true")
    ap.add_argument("--softfloor", type=float, default=None,
                    help="replace predicted-0 windows with alpha*f_pc style floor value")
    ap.add_argument("--floor_mask_key", default="nobump_mask",
                    help="npz key holding boolean mask of no-bump windows")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    test = pd.read_csv(TEST, dtype={"ID": str})
    assert len(test) == 1500, "Test.csv unexpected"

    # ---- obtain raw vector + optional mask ----
    mask = None
    if a.npz:
        Z = np.load(a.npz, allow_pickle=True)
        v = np.asarray(Z[a.key], float)
        if a.floor_mask_key in Z: mask = np.asarray(Z[a.floor_mask_key], bool)
    elif a.csv:
        d = pd.read_csv(a.csv, dtype={"ID": str})
        col = "share_added_vessel"
        assert col in d.columns, f"cols={d.columns.tolist()}"   # EXPLICIT share col
        v = d[col].to_numpy(float)
    else:
        sys.exit("need --csv or --npz/--key")
    assert len(v) == 1500 and np.isfinite(v).all(), "bad vector"

    # ---- optional soft floor: spread exact-zero/nobump predictions ----
    if a.softfloor is not None:
        m = (v <= 0) if mask is None else mask
        v = v.copy()
        v[m] = a.softfloor
        print(f"softfloor: {int(m.sum())} windows -> {a.softfloor}")

    # ---- optional shrink / repin (in that order) ----
    tag = a.name
    if a.shrink is not None:
        v = MU + a.shrink*(v - MU)
        tag += f"_k{int(a.shrink*100):03d}"
    if a.repin:
        v, av, gam = moment_pin(np.maximum(v, 1e-12))
        tag += "_repin"
        print(f"repin: a={av:.6f} gamma={gam:.6f}")

    # ---- HARD ASSERTS (the gate) ----
    out = test[["ID"]].copy()
    out["share_added_vessel"] = np.clip(v, 0.0, 1.0)
    n_clip = int(np.sum(np.abs(np.clip(v, 0, 1) - v) > 1e-12))
    assert out["share_added_vessel"].notna().all()
    assert len(out) == 1500 and out["ID"].equals(test["ID"]), "ID order broken"

    path = f"{DL}/submission_{tag}.csv"
    if os.path.exists(path) and not a.force:
        sys.exit(f"REFUSING to overwrite {path} (use --force)")

    # ---- census + moments ----
    s = out["share_added_vessel"].to_numpy()
    ties = pd.Series(np.round(s, 9)).value_counts()
    pm = [(float(k), int(c)) for k, c in ties.head(3).items()]
    rep = {
        "name": tag, "file": os.path.basename(path), "n": 1500,
        "E_p": float(s.mean()), "E_p2": float((s*s).mean()),
        "sigma_p": float(s.std(ddof=0)), "min": float(s.min()), "max": float(s.max()),
        "clipped_rows": n_clip,
        "point_masses_top3": pm,
        "mass_at_min": float((s == s.min()).mean()),
        "notes": "share col verified (A33 zero-weight score col excluded)",
    }
    # spearman vs pinned references
    ref = f"{DL}/submission_r7_v3_k045_PIN.csv"
    if os.path.exists(ref):
        r = pd.read_csv(ref)["share_added_vessel"].to_numpy(float)
        rep["spearman_vs_r7_v3_k045"] = float(pd.Series(s).corr(pd.Series(r), method="spearman"))
    ref2 = f"{BASE}/workspace/misc-notes-data/submissions/submission_r7_v2_bumpshare_repinned.csv"
    if os.path.exists(ref2):
        r2 = pd.read_csv(ref2)["share_added_vessel"].to_numpy(float)
        rep["spearman_vs_r7_v2"] = float(pd.Series(s).corr(pd.Series(r2), method="spearman"))

    out.to_csv(path, index=False)
    h = sha(path)
    rep["sha256"] = h
    with open(f"{DL}/backups/LEDGER.sha256", "a") as f:
        f.write(f"{h}  {os.path.basename(path)}\n")
    with open(f"{DL}/backups/SUBMISSION_LEDGER.jsonl", "a") as f:
        f.write(json.dumps(rep) + "\n")
    print(json.dumps(rep, indent=1))
    print("WROTE", path)
    # warnings
    if rep["mass_at_min"] > 0.20:
        print(f"!! WARNING: {rep['mass_at_min']*100:.1f}% rows share one value — consider --softfloor")
    if abs(rep["E_p"] - MU) > 0.02:
        print(f"!! WARNING: E[p]={rep['E_p']:.4f} far from pinned mu={MU:.4f}")

if __name__ == "__main__":
    main()
