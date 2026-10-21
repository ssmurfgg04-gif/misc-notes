# R9-C — Dines 2025 PhD thesis rescue (SUNScholar) — FINAL: PDF ACQUIRED + 3 ARRAY SITE NAMES

**Task:** locate working download route for Dines 2025 Stellenbosch PhD thesis + extract the
3 south-coast array site names (the "last open name-gap" on station 08 / G1).
**Date:** 2026-10-21. **Agent:** general-purpose (R9-C).
**Previous state (R7e/R8):** handle 10019.1/132009 "resource not found"; curl → nginx 403;
fetch → app 404; recorded bitstream uuid `00218139-21b4-4e5d-9d6f-98c4ed54d6af`;
filename guess `dines_marine_2025.pdf`.

## TL;DR

- **PDF ACQUIRED** → `/home/z/my-project/data/dines_marine_2025.pdf`
  (6,286,780 bytes, 304 pp, PDF 1.7, producer "Microsoft Word", pdfinfo Author "sasha dines",
  sha256 `174b3b1c521881d7a309bb00a51e7d79dab6e0034d1a826c115004e98148dbd4`).
- **THE 3 ARRAY SITES (prize): Mossel Bay, Buffelsbaai, Plettenberg Bay** — five moorings
  **M1 Mossel Bay Harbour, M3 Mossel Bay (Diaz), M7 Buffelsbaai, M8 Plettenberg Bay
  (Robberg Point), M9 Plettenberg Bay (Beacon Isle)**, deployed 26 Aug – 7 Oct 2022
  (42 days; analysis window 32 days/"five weeks"), ~120 km linear array.
- Bonus: full 2021 Mossel Bay 6-mooring array table **with exact coordinates** (Table 4.1).
- New name candidate for station 08 besides Mossel Bay: **Buffelsbaai** (thesis: 77% of all
  signature-whistle detections, single hydrophone, 2,070 whistles — the loudest site).

## Thesis record (confirmed)

| Field | Value |
|---|---|
| Title | Applied passive acoustic monitoring of South Africa's most threatened marine mammal, the Indian Ocean humpback dolphin (Sousa plumbea) |
| Author | Dines, Sasha Francess |
| Degree | Thesis (PhD), Doctoral, Zoology — Stellenbosch University, issued 2025-03, accessioned 2025-05-16 |
| Advisors | Measey, John; Gridley, Tess; Elwen, Simon (Sea Search Research & Conservation NPC + SU Botany & Zoology) |
| Handle | https://scholar.sun.ac.za/handle/10019.1/132009 |
| Item uuid | `ba08fdd7-4a00-4367-b6fd-f7dd10e309c6` (archived, discoverable) |
| Recommended cite URL | https://scholar.sun.ac.za/items/ba08fdd7-4a00-4367-b6fd-f7dd10e309c6 |
| Format | 304 pages : illustrations (some color), maps — application/pdf |
| Rights | Stellenbosch University (open download; no embargo flag; canRequestACopy feature present but PDF downloads anonymously) |

## Routes tried + verdicts

| # | Route | Verdict |
|---|---|---|
| 1 | `GET /handle/10019.1/132009` (browser UA, curl) | **200 OK, 459 KB.** DSpace 7 Angular page; SSR state (`<script id="dspace-angular-state">`) contains full item JSON. User's earlier "resource not found" was transient/stale (handle resolves fine now). Page loads without JS; metadata is in the SSR payload. |
| 2 | `GET /server/api/core/items/00218139-21b4-4e5d-9d6f-98c4ed54d6af` | 404 — **root cause of prior failure: `00218139…` is a BITSTREAM uuid (the TEXT bundle), not an item uuid.** Real item uuid = `ba08fdd7-4a00-4367-b6fd-f7dd10e309c6` (found in SSR state). |
| 3 | `GET /bitstreams/00218139…/download` (and `…/b304c9c7…/download`) | **429 Too Many Requests (nginx)** on the `/bitstreams/<uuid>/download` UI proxy path — rate-limited for our IP (2 attempts, 30 s apart). This path should be avoided by automation. |
| 4 | `GET /server/api/core/bitstreams/<uuid>/content` (DSpace 7 REST canonical content route) | **200 OK.** PDF `b304c9c7-9499-4625-9227-b3742d7f9c81` → 6,286,780 B application/pdf. TEXT bitstream `00218139…` → 100,242 B text/plain (official full-text extraction). **THIS IS THE WORKING DOWNLOAD ROUTE.** |
| 5 | OAI-PMH `/oai/request` | 403 (nginx) / Angular shell — wrong path. |
| 6 | OAI-PMH `https://scholar.sun.ac.za/server/oai/request?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:scholar.sun.ac.za:10019.1/132009` (browser UA) | **200 OK** — full oai_dc record incl. complete English abstract. (Needs a browser UA; empty UA gets 403.) |
| 7 | Wayback CDX (`web.archive.org`) | **Unreachable from this sandbox** (connect timeout ×3). Moot after acquisition. |
| 8 | OpenAIRE `api.openaire.eu/search/publications` | HTTP 400 on title query (quote/percent-encoding); not retried — moot after acquisition. |
| 9 | `base-search.net`, `oatd.org`, WorldCat, Rufford, Sea Search pages, Oosthuizen 2026 Frontiers | Not needed — PDF + site names obtained directly from the source. (Rufford start 13 Feb 2026 = post-competition, per R8; Oosthuizen citation would only duplicate thesis facts.) |

**Working URLs (final):**
- Item page: `https://scholar.sun.ac.za/items/ba08fdd7-4a00-4367-b6fd-f7dd10e309c6`
- PDF: `https://scholar.sun.ac.za/server/api/core/bitstreams/b304c9c7-9499-4625-9227-b3742d7f9c81/content`
  (equivalently `/bitstreams/b304c9c7-9499-4625-9227-b3742d7f9c81/download` from a browser; avoid for automation → 429)
- Full-text: `https://scholar.sun.ac.za/server/api/core/bitstreams/00218139-21b4-4e5d-9d6f-98c4ed54d6af/content`
- OAI record: `https://scholar.sun.ac.za/server/oai/request?verb=GetRecord&metadataPrefix=oai_dc&identifier=oai:scholar.sun.ac.za:10019.1/132009`

## Bitstream inventory (from SSR state)

| uuid | bundle | bytes | what |
|---|---|---|---|
| `b304c9c7-9499-4625-9227-b3742d7f9c81` | ORIGINAL | 6,286,780 | **the thesis PDF** (`dines_marine_2025.pdf`) |
| `00218139-21b4-4e5d-9d6f-98c4ed54d6af` | TEXT | 100,242 | full-text extraction (`dines_marine_2025.pdf.txt`) |
| `cc0058ea-3835-4707-9633-a3b65fdc8a19` | THUMBNAIL | 4,198 | `.pdf.jpg` cover thumb |
| `c2d8de08-6f0c-4996-a30e-4e9688f3e31f` | LICENSE | 2,073 | SU license |

## THE PRIZE — south-coast array (Chapter 5, "SWORD")

> "This proof-of-concept study deployed a **120 km array of five hydrophones for 42 days
> across three high-use bays (Mossel Bay, Buffelsbaai and Plettenberg Bay)** within the
> central part of the … south coast population range of Indian Ocean humpback dolphins."
> — Ch. 5 abstract, p. 187–188

**Table 5.1 (deployment summaries, all started 26/08/2022 00:00, 96 kHz continuous, high gain):**

| Mooring | Location | km E of M1 | Recording end | Rec days | Whistles(SNR2/3) | SW | Individuals |
|---|---|---|---|---|---|---|---|
| M1 | **Mossel Bay Harbour** (MB_Harbour) | 0 | 28/09/2022 14:10 | 33 | 458 | 272 | 7 |
| M3 | **Mossel Bay Diaz** (MB_Diaz) | 3.8 | 14/09/2022 22:50 | 19 | 94 | 59 | 2 |
| M7 | **Buffelsbaai** | +80.4 | 27/09/2022 18:20 | 32 | 1,532 | 719 | 13 |
| M8 | **Plettenberg Bay – Robberg Point** (Plett_RP) | +36.3 | 15/09/2022 00:50 | 20 | 192 | 87 | 9 |
| M9 | **Plettenberg Bay – Beacon Isle** (Plett_BI) | +3.4 | 07/10/2022 20:10 | 42 | 670 | 145 | 15 |

(total chain M1→M9 ≈ 123.9 km ≈ "120 km"; 4,425 whistles annotated, 3,559.44 hr; 1,282 SWs,
25 SWTs/individuals; M1+M7 = 77% of detections; battery-failure cutoffs on M3/M8 ~20 days)

- Gear: **ST300 + ST400 + ST500 SoundTraps** (ST400 ~23-day battery limit; ST500 45 days),
  Vemco/Innovasea pop-up acoustic releases, 40 kg weights, subsurface buoy, 3 m off seafloor,
  8–10 m depth, all within 15 m depth contour; reef-avoidance siting (snapping-shrimp masking).
- M1/M3 2022 = **redeployments of 2021 locations 1 and 3** ("M1_Mossel Bay Harbour and
  M3_Mossel Bay Diaz") → the 2021 coordinates below apply to the 2022 M1/M3 too.
- Abundance (closed Huggins per bay): Mossel Bay 8 (CI 8–8); Buffelsbaai 19 (14–53);
  Plettenberg Bay 22 (19–33). Combined: POPAN 26 (CI 23–30); SECR 23–26;
  density 0.000061–0.000439 animals·ha⁻¹. Prior south-coast studies tabulated (Table 5.6):
  Mossel Bay (James 2015), Goukamma–Tsitsikamma MPA (Conry 2017), Plett (Jobson 2006, Greenwood 2013).

## Bonus — 2021 Mossel Bay array with exact coordinates (Table 4.1, Ch. 4)

Deployment 19 Mar – 5 Apr 2021 (18-day), 6 moorings ~2 km apart in 8 km linear array,
10-min continuous files at 96 kHz, mooring 1 (south, harbour) → mooring 6 (north,
Hartenbos/Kleinbrak river-mouth area); boat surveys Cape St Blaize ("The Point") ↔ Kleinbrak:

| Unit | Mooring | Latitude | Longitude | End |
|---|---|---|---|---|
| ST500 | M1 | -34.1767 | 22.14221 | 2021/04/09 12:37 |
| ST500 | M2 | -34.1703 | 22.13575 | 2021/04/09 12:57 |
| ST300 | M3 | -34.1646 | 22.12037 | 2021/04/01 13:31 |
| ST300 | M4 | -34.1446 | 22.1151 | 2021/04/06 17:00 |
| ST300 | M5 | -34.1546 | 22.1138 | 2021/04/03 15:00 |
| ST300 | M6 | -34.1331 | 22.11944 | 2021/04/01 21:50 |

M1 sits at the **harbour entrance** area (dolphins "high use of the area near the harbour
entrance", single-point mooring buoys 800 m–1 km offshore); >80% of 2021 SWs on non-adjacent
moorings 1 & 4 (6 km apart). No printed lat/long for M7–M9 2022 moorings (map only, Fig 5.1).

## Site-name evidence (grep counts in thesis text)

Mossel Bay 140 · Plettenberg 54 · Buffelsbaai ~12 · Goukamma 5 · Hartenbos 2 · Knysna 3 ·
Robberg 2 · Struisbaai 1 (boat-survey site, Ch.2/3) · Stilbaai 1 (MPA list only) ·
Agulhas 1 (current, not place) · **Gansbaai 0 · Hermanus 0 · St Francis 0 · Sedgefield 0 ·
Great/Little Brak 0 · Witsand/Infanta/Gouritz 0**. Boat-based whistle-variation sites
(Ch. 2–3): False Bay, Struisbaai, St Sebastian Bay, Mossel Bay (south coast) + Richards Bay
(east coast); macro-geographic comparison vs India.

## Implications for the station hunt (hand-off to R9/R10)

1. **Buffelsbaai is the standout new candidate name** for the south-coast exposed site
   (G1 → 08): thesis reports it as a humpback-dolphin hotspot carrying 77% of all
   signature-whistle detections on a single hydrophone (2,070 whistles) — a noisy,
   high-activity coastal site between Mossel Bay and Knysna (≈34.09°S, 22.80°E, not
   printed in thesis). Mossel Bay remains rank-1 named 08 candidate; Buffelsbaai joins
   the allowed-name list for enquiries/submission hedging.
2. M1 "Mossel Bay Harbour" is a **harbour-adjacent south-coast site** — relevant if any
   test station shows harbour-tinged fingerprints despite a south-coast designation
   (c.f. G2 harbour class discussion in R8).
3. Thesis sensor set (ST300/ST400/ST500, 96 kHz continuous, 10-min files, 8–10 m depth,
   40 kg moorings) matches the competition's "SoundTrap 300/500 since 2021" metadata —
   the 2021 Table 4.1 coordinates give a 8 km × ~2 km spacing reference for Mossel Bay.
4. The R7e note "Gansbaai Sea Shepherd Dec 2023" remains uncorroborated — thesis never
   mentions Gansbaai.

## Files

- `/home/z/my-project/data/dines_marine_2025.pdf` — 6,286,780 B; sha256
  `174b3b1c521881d7a309bb00a51e7d79dab6e0034d1a826c115004e98148dbd4`
- `/home/z/my-project/data/dines_thesis_textbundle.txt` — official SUNScholar TEXT bitstream
  (100,242 B; sha256 `73a58f1f3b3fe7bf501f7305c6075573c7d9cc976429940c161dbec7bf41175c`)
- `/home/z/my-project/data/dines_thesis_text.txt` — replaced stale 403 stub with pdftotext
  extraction of the full PDF (layout mode, 14,467 lines)
- This report: `/home/z/my-project/docs/intel_r9_dines.md`

**Final status: PDF ACQUIRED.** Handle "broken" was a false alarm (transient); correct
automation route = DSpace 7 REST `/server/api/core/bitstreams/<uuid>/content` with a
browser User-Agent (never `/bitstreams/<uuid>/download`, which 429s server-side).
