#!/usr/bin/env python3
"""Physics-provisional reference library (same schema as vtuad refs.parquet).

Used only as SCENARIO-A stress test until VTUAD ingest lands. Wittekind-style
source spectra (low-freq cavitation, high-freq cavitation, machinery) with
randomised vessel params + randomised 15-minute passage envelopes.
"""
import numpy as np
import pandas as pd
import os

OUT = "/home/z/my-project/data/refs_physics"
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(7)

N_CLIPS = 80
MINUTES = 15
CENTRES = 10.0 ** (1.5 + 0.1 * np.arange(25))
f = CENTRES

c_n = [125, 0.35, -8e-3, 6e-5, -2e-7, 2.2e-10]
rows, mrows = [], []
for i in range(N_CLIPS):
    D = 10 ** rng.uniform(0.7, 3.2)          # displacement 5 t .. 1600 t
    C_B = rng.uniform(0.55, 0.85)
    v = rng.uniform(3, 18)
    v_c = rng.uniform(4, 12)
    E_mass = rng.uniform(0.5, 20)
    E_num = rng.integers(1, 5)
    L1 = sum(c_n[n] * f ** n for n in range(6)) + 80*np.log10(4*C_B*v/v_c) + (20/3)*np.log10(D/1e4)
    L2 = -5*np.log10(f) - 1000/f + 10 + (20/3)*np.log10(D/1e4) + 60*np.log10(np.maximum(1000*C_B*v/v_c, 1e-6))
    L3 = 1e-7*f - 0.01*f + 140 + 15*np.log10(E_mass) + 10*np.log10(E_num) + rng.choice([0.0, 15.0])
    spec = 10 ** (np.minimum(np.maximum(10*np.log10(10**(L1/10) + 10**(L2/10) + 10**(L3/10)), 0), 200) / 10)
    spec = spec / spec.sum()                   # normalised shape
    # 15-minute passage envelope: rise-CPA-fade with randomised shape
    mode = rng.integers(0, 3)
    t = np.linspace(0, 1, MINUTES)
    if mode == 0:
        env = np.exp(-((t - rng.uniform(0.3, 0.7))**2) / rng.uniform(0.02, 0.15))
    elif mode == 1:
        env = np.clip(t / rng.uniform(0.3, 0.6), 0, 1) ** rng.uniform(0.5, 2)   # long fade
    else:
        env = np.clip(rng.uniform(0.3, 0.6) + rng.uniform(0.2, 0.8) - t, 0, 1) ** rng.uniform(0.5, 2)
    env = 0.05 + 0.95 * env / env.max()
    # per-minute band gain jitter (channel variation)
    band_gain = rng.lognormal(0, 0.15, size=(MINUTES, 25))
    P = env[:, None] * spec[None, :] * band_gain
    P = P / P.sum()                            # unit energy; generator rescales by f
    rows.append(pd.DataFrame({
        "clip_uid": f"phys_{i:03d}", "kind": "physics",
        "minute_idx": np.repeat(np.arange(1, MINUTES + 1), 25).astype(np.int16),
        "band": np.tile(np.arange(25), MINUTES).astype(np.int8),
        "power": P.ravel().astype(np.float32)}))
    mrows.append({"clip_uid": f"phys_{i:03d}", "kind": "physics", "label": "physics",
                  "hull_id": f"phys_{i:03d}", "length_m": float(2 * D ** (1/3)), "beam_m": np.nan,
                  "minutes": MINUTES, "sample_rate": 0})
refs = pd.concat(rows, ignore_index=True)
pd.DataFrame(mrows).to_parquet(f"{OUT}/refs_meta.parquet", index=False)
refs.to_parquet(f"{OUT}/refs.parquet", index=False)
print("physics refs:", refs.shape, "->", OUT)
