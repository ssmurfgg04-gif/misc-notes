# vessels.md — vessel reference profiles (R1)

Purpose: what the injected "vessel passage references" likely look like, and
which corpora give us real, licensed examples of each.

## 1. Class taxonomy (union of permitted sources)

| Class | VTUAD clips (h) | Mean length | Acoustic signature (lit-consensus) | Competition relevance |
|---|---|---|---|---|
| tug / tow | 188 (18.8 h) | 24 m | strong LF tonals (engine + prop), high dB re small size; variable load | "smaller craft" refs |
| cargo | 97 (8.5 h) | 161 m (112–348) | strong blade-rate tonals 10–100 Hz, broadband 50–500 Hz hump | "larger ships" refs |
| passengership | 71 (5.5 h) | 142 m | cargo-like but faster, cleaner tonals | larger ships |
| fishing | 34 (3.5 h) | 29 m | engine tonals + winch/gear transients | small craft |
| pleasurecraft | 32 (2.8 h) | 19 m (5–46) | fast small craft; mid-band (500 Hz–2 kHz) dominant, speed-dependent | small craft — likely over-represented in SA coastal refs |
| other | 40 (3.5 h) | 134 m | mixed | generic |
| dredger | 8 (0.7 h) | 124 m | machinery-rich + pump tonals | niche |
| tanker | 5 (0.6 h) | 155 m | slow, LF-heavy | sparse — supplement from UniqueShip 5-class set |
| sailing | 6 (0.6 h) | 11 m | mostly sail noise + engine aux | rare |
| rescue | 4 (0.5 h) | 24 m | fast transit profile | rare |
| pilotvessel | 2 (0.2 h) | 20 m | short transits | rare |
| background | 38 (10.8 h) | — | ambient-only (ONC BC) | negative examples (different ocean!) |

VTUAD hull registry: **178 unique hulls**, length 5–452 m, beam 3–26 m,
UTC 2016-05 → 2017-05, Strait of Georgia BC, icListen hydrophone, 32 kHz.

## 2. Physics priors — Wittekind model (for generator stress-tests)

Source levels per 1/1-octave band from (v, v_c, C_B, D, E):
- L1 = Σ c_n f^n + 80·log10(4·C_B·v/v_c) + (20/3)·log10(D/D_ref)  [LF cavitation]
- L2 = −5·log10 f − 1000/f + 10 + (20/3)·log10(D/D_ref) + 60·log10(1000·C_B·v/v_c)  [HF cavitation]
- L3 = 1e-7·f − 0.01·f + 140 + 15·log10(E_mass) + 10·log10(E_num) + mount  [machinery]
- c_n = [125, 0.35, −8e-3, 6e-5, −2e-7, 2.2e-10], D_ref = 10,000 t
- total = 10·log10(10^(L1/10) + 10^(L2/10) + 10^(L3/10))

Use for: (a) sanity envelopes on VTUAD spectra, (b) speed/size-conditioned
augmentation, (c) stress-test scenarios. NOT as primary reference (organiser
refs are real recordings, and "a reference may include ambient from its origin").

## 3. What this implies for the generator

1. Reference library must span **5 m → 350 m** (test states both small craft and
   large ships) — VTUAD alone covers this; tanker class too thin → pad with
   UniqueShip 5-class balanced (tug/tow, tanker, passenger, cargo).
2. Real passage **time profiles** (rise → CPA → fade) must be preserved; VTUAD
   strict-interval cuts keep true passage geometry.
3. Third-octave conversion: band energies from 32 kHz audio via Welch →
   1/3-octave aggregation onto the exact 25 centres (31.6 Hz–7.94 kHz, base-10).
   Document samplerate/units; ONC icListen dB re 1 µPa convention — the SA
   export convention is "not independently verified", so scale-mismatch between
   reference and background is part of the problem. Inject in **linear energy**
   and let the fraction target absorb absolute calibration.
4. Dedupe VTUAD vs UniqueShip by hull before mixing (both ONC).

## 4. Files / pointers

- VTUAD per-class zips: `vtuad_wav_{tug,cargo,passengership,...}.zip` —
  pull classes in weight order (tug, cargo, passengership, fishing, pleasurecraft)
- `registry_anonymized.csv` → hull_id for split isolation (adopted in plan §3.1)
- Profile JSONs: `data/profile/vessels_vtuad.json`
