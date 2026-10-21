# station-intel.md — SA station intelligence (R1 profile, 2026-10-20)

Derived from the official package (checksums verified). Coordinates are
"working site-level candidates" — never treat as verified hydrophone positions.

## 1. Site matrix
| site | coords (lat, lon) | rows | period | recorders (sample rate) | TOL p50 | p01–p99 | notes |
|---|---|---|---|---|---|---|---|
| 01 Richards Bay | −28.8087, 32.0897 | 1,001,174 | 2017-05→2024-05 | 201383949 (24k) 2017–19 · 5708 (24k) 2020–21 · 7005 (24k) 2022–24 | 75.3 | 29.7–131.2 | major port; 58% of corpus |
| 02 Durban | −29.9083, 31.0587 | 44,640 | 2025-10→2025-12 | 8230 ST600 (48k) | 77.3 | 42.8–118.6 | freshest; also used at Riy Banks |
| 03 Cape Recife | −34.0490, 25.7090 | 5,928 | 2024-03 (19 d) | 8210 ST600 (48k) | 78.2 | 58.5–124.5 | |
| 04 Bird Island | −33.8982, 26.2914 | 47,552 | 2022→2024 | URN.BirdIsland 6509 (24k) · URN 8321 (12k, 1 d) | **94.4** | 54.6–127.5 | Cape fur seal colony — biological LF/HF loud |
| 05 St Croix Island | −33.8266, 25.7511 | 250,717 | 2022→2025 | URN.StCroix 6509 (24k) · URN.BirdIsland 6509 (24k) · URN 8321 (12k) | 81.3 | 50.1–127.4 | near Algoa Bay shipping |
| 06 Riy Banks | −33.9890, 25.8880 | 4,121 | 2024-03 (31 d) | 8230 ST600 (48k) | 79.9 | 61.6–124.3 | offshore reef |
| 07 St Francis | −34.1245, 24.9494 | 169,488 | 2015→2018 | SM2M (48k) | 84.1 | 66.6–116.6 | long baseline, oldest |
| 09 Fish Hoek | −34.1404, 18.4428 | 53,767 | 2016→2021 | ST300 201650217 (96k) · ST300 5344 (96k) | 64.6 | 31.6–127.1 | quiet bay, False Bay |
| 10 Sea Point | −33.9195, 18.3521 | 3,660 | 2018-10 (3 d) | ST300 201650217 (96k) | 60.7 | 23.0–129.9 | tiny; same unit as Fish Hoek |
| 13 Saldanha Bay | −33.0472, 17.9546 (alt −33.0864, 17.8988) | 134,732 | 2022→2023 | ST300 5344 (96k) · ST500 5350 (48k) | 67.2 | 35.4–123.2 | 2 unresolved candidate coords |

## 2. Hardware fingerprint (band trust)
- 12 kHz units (URN_8321): Nyquist 6 kHz ⇒ top band(s) unreliable on Bird
  Island 2024 + St Croix 2024–25 rows.
- 24 kHz (icListen-class): reliable through ~8 kHz — fine for all 25 bands.
- 48 kHz (SM2M/ST500/ST600): full support.
- 96 kHz (ST300): full support.
⇒ Build per-recorder band-availability matrix in R3; use as feature mask AND
  as realism filter for synthetic mixtures (a test window whose top band is
  structurally missing was probably recorded on a 12 kHz unit).

## 3. Test-set fingerprints (legal: distribution-level design inputs)
- m01 missing 41.6%, m15 6.7%, m02–13 ≈ 0 ⇒ recorder duty-cycle artefact at
  window start. Model must handle it; per-minute availability mask = feature.
- 48.3% of test rows have ≥1 missing cell (3.3% overall).
- dB range [29.3, 152.9]: outliers present ⇒ robust scaling, no hard clipping
  before energy conversion (10^(dB/10) is sensitive to 150+ dB cells).
- Site-blind requirement: no site ID in test ⇒ site-specific calibration must
  be inferred per window (or marginalised), never memorised.

## 4. Background climatology (R3 TODO)
- per site × recorder × hour-of-day × band: median + IQR of linear band energy
- wind proxy: broadband slope (Wenz: wind dominates >500 Hz; shipping <200 Hz)
- gap census per site (min-res grid) for honest "coverage" maps
- pressure-map deliverable: relative acoustic activity, never absolute claims

## 5. Legal rails for AIS weak labels
- Join key: time-window × distance-to-candidate-coords; Saldanha = 2 candidates.
- Validate export-clock vs UTC on obvious port-traffic diurnal patterns first.
- Output = confidence-scored likelihood, never 0/1 label.

## 6. Withheld stations {08, 11, 12} — R7b intel (2026-10-21)

**A38–A39:** station 09 Fish Hoek = the Sea Search False Bay ST300 network
(Ross-Marsh et al. 2020, Bioacoustics; coords exact match). Network sites:
| name | coords | effort | note |
|---|---|---|---|
| Smitswinkel Bay | −34.267, 18.147 | 162 d | most humpback song |
| Fish Hoek | −34.141, 18.444 | 201 d | = registry 09 |
| Strandfontein | −34.088, 18.636 | 183 d | north shore |
| Rooi Els | −34.263, 18.847 | 60 d | east shore |
Moored, 14–25 m, Sept 2016–Jan 2018 (package Fish Hoek runs to 2021).
Sea Point (10) = same recorder 201650217, Oct 2018, 3 d (side deployment).

**08 (A40):** a second Sea Search False Bay site — lead **Strandfontein**,
alternates Rooi Els / Smitswinkel Bay. Simon's Town rejected (no deployment
record; "site 8 = Simon's Town" tables in the wild are whale-watch lists —
numbering coincidence).

**11/12 (A41):** west-coast block (Sea Point → Saldanha). Ranked: **Robben
Island** (ST300 field activity proven by Probert et al. 2025), **Dassen
Island** (Sea Search humpbacks), **Langebaan** (MPA history), **Yzerfontein**,
**Table Bay/Milnerton**. Strand/Gordon's Bay rejected (wrong block).
**A44:** Saldanha (13) shares ST300 5344 with Fish Hoek ⇒ same equipment pool
(Sea Search-linked) deployed the west coast 2022–2023.

Ordering law (R7b): registry = regional blocks (01–02 KZN, 03–06 Algoa Bay
[non-geographic internal order], 07 south coast, 08 False Bay?, 09–10 peninsula,
11–12 west coast, 13 Saldanha); Cape block happens to be longitude-monotone.
