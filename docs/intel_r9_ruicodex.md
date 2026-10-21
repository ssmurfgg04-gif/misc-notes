# intel_r9 — Rival dossier: team "ruicodex" (Zindi underwater vessel noise, rank #1)

**Task:** R9-B · **Date:** 2026-10-21 · **Agent:** general-purpose (OSINT) · **Probes:** 80 network calls
**Evidence legend:** ✅ VERIFIED (fetched/seen directly) · ◐ PROBABLE (strong secondary evidence) · ⚠ UNCONFIRMED · ⛔ BLOCKED (source inaccessible, reason given)
All timestamps UTC. Declared text being investigated (posted 2026-10-18) is quoted in §1.0.

---

## 1.0 The declaration under investigation

> "External data declaration (team ruicodex): we also use VTUAD (rebuilt) v1.3.2, Yuan et al.,
> https://doi.org/10.5281/zenodo.23037895 (CC BY 4.0; upstream Ocean Networks Canada,
> https://doi.org/10.17616/R3RW43). Files: vtuad_strict_wav_vessel.zip (parts 01-03, reassembled,
> SHA-256 verified), vtuad_strict_wav_background.zip, metadata.csv, registry_anonymized.csv.
> Free download from Zenodo, no account needed. Preprocessing: one-minute deci-decade band power
> with the starter notebook's reference conversion, no absolute calibration. Nothing is fitted on
> Test.csv and no attempt is made to identify which clip appears in any test window."

---

## 1. Zenodo deposit — ✅ VERIFIED (record exists, fully public, matches declaration exactly)

### 1.1 Record identity
| Field | Value | Evidence |
|---|---|---|
| DOI (version) | `10.5281/zenodo.23037895` | ✅ doi.org 302 → zenodo.org; API 200 |
| Concept DOI (all versions) | `10.5281/zenodo.22274549` | ✅ API `conceptrecid: 22274549` |
| Title | "VTUAD: An AIS-Auto-Labeled Vessel-Type Underwater Acoustic Dataset Reconstructed from Ocean Networks Canada Archives" | ✅ API metadata |
| Version deposited | **1.3.2**, published **2026-09-29** (created 2026-09-29T11:37Z) | ✅ |
| Resource type / license | Dataset / **cc-by-4.0** | ✅ |
| Creators | **Yuan, Hao** (Wuhan Univ. of Science & Technology + CSSC-LINCOM Electronics Wuhan; ORCID 0009-0009-5544-5414), **Wang, Wenbo** (WUST, 0000-0002-2130-7672), **Li, Tian**, **Chen, Guici**, **Zeng, Lingjiang**, **Liu, Sixian** (CSSC-LINCOM) | ✅ API + CITATION.cff |
| Related identifiers | `https://data.oceannetworks.ca` (isDerivedFrom, dataset) | ✅ — note: the re3data DOI is NOT in related_identifiers; it is cited only inside `license_evidence_v131.md` |
| Owner | Zenodo owner id 1863231 | ✅ |
| Stats | 9,536 downloads / 2,841 unique; 704 views (as of 2026-10-21) | ✅ |

**Cross-check vs declaration:** the declared file set is *exactly* what v1.3.2 ships (§1.4) — declaration is internally consistent. ✅

### 1.2 Version chain — ✅ VERIFIED (6 versions, all listed)
| Version | RecID | DOI | Date | Files | Total size |
|---|---|---|---|---|---|
| v1.0.0 | 22274550 | 10.5281/zenodo.22274550 | 2026-09-03 | 2 | 255 KB (metadata only) |
| v1.1 | 22282021 | 10.5281/zenodo.22282021 | 2026-09-03 | 13 | 25.79 GB (first WAVs) |
| v1.2.0 | 22773623 | 10.5281/zenodo.22773623 | 2026-09-15 | 29 | 36.24 GB (+features, split, code) |
| v1.3.0 | 22920817 | 10.5281/zenodo.22920817 | 2026-09-23 | 44 | 40.88 GB (strict re-cut + anonymized registry) |
| v1.3.1 | 23028171 | 10.5281/zenodo.23028171 | 2026-09-29 | 61 | 40.89 GB (audit pack) |
| **v1.3.2** | **23037895** | **10.5281/zenodo.23037895** | **2026-09-29** | **63** | **40.89 GB** |

Cadence read: v1.0→v1.3.2 in **26 days** — rapid release-and-patch discipline; v1.3.1 and v1.3.2 released the *same day* (audit-pack re-publishes). "Rebuilt" is the deposit's own framing: an *independent re-generation* from the ONC archive, not a re-upload of an existing dump.

### 1.3 Small files downloaded (kept in `/home/z/my-project/data/zenodo_r9/`)
`metadata.csv` (166,858 B), `registry_anonymized.csv` (164,251 B), `dataset_card.md`, `CITATION.cff`,
`license_evidence_v131.md`, `interval_audit_readme.md`, `SHA256SUMS.txt`, `strict_interval_wav_SHA256SUMS.txt`,
`v131_supplementary_SHA256SUMS.txt`, `README_vtuad_strict_wav_vessel_parts.txt`.
Checksums: `registry_anonymized.csv` SHA-256 `92a1cba9ca73…de5` matches the record's `SHA256SUMS.txt` ✅;
`metadata.csv` MD5 `3d597065…cd2` and `registry_anonymized.csv` MD5 `f58655ef…5de` match the API file entries ✅.

### 1.4 File list highlights (63 files, ~40.9 GB total) — ✅ VERIFIED
- **The files ruicodex declared:** `vtuad_strict_wav_vessel.zip.part01/02/03` (1,237,445,900 / 1,237,445,900 / 1,237,445,899 B; reassembled = 3,712,337,699 B, SHA-256 `96564721a917…8ac6` per `README_vtuad_strict_wav_vessel_parts.txt`) + `vtuad_strict_wav_background.zip` (926,037,631 B) + `metadata.csv` + `registry_anonymized.csv` (164,251 B). Parts 01-03 ship per-clip SHA-256 ledger in `strict_interval_wav_SHA256SUMS.txt` (69,228 B).
- Older loose-cut per-class WAVs (v1.1-era): `vtuad_wav_{tug 8.68GB, background 4.98GB, cargo 3.92GB, passengership 2.52GB, pleasurecraft 1.30GB, fishing 1.63GB, other 1.63GB, sailing 261MB, dredger 330MB, rescue 215MB, tanker 253MB, pilotvessel 69MB}.zip`.
- Precomputed log-mel feature store: `vtuad_features_{train parts 01-07, val, test}.zip` (~6.9 GB) + `npy_sha256.csv.gz`.
- Frozen split manifests: `manifest_train.csv` (13.9 MB), `manifest_val.csv` (2.9 MB), `manifest_test.csv` (2.6 MB) → 369/80/76 recording-level split.
- Benchmark artifacts: `per_seed_test_predictions_s42-46.csv` (7.1 MB), `vtuad_v120_s4{2..6}_test_probs.npz`, `rev1_paired_bootstrap_s42-46.json`.
- Audits: `interval_uid_closure_v1deployment.csv`, `grouping_defect_3day_audit.csv`, `cut_rule_simulation_525clips.csv`, `wrap_feature_recompute_check.csv`, `clip_acoustic_stats.csv` (151 KB), `static_field_fill_audit.csv`, `static_field_conflicts.csv`, `mmsi_stability_20160908.csv`, `registry_verification_sample30.csv`.
- Rebuild pipeline code: `zenodo_vtuad_v1.2.0.zip` (163 KB) + `environment.yml`.

### 1.5 Dataset structure (from metadata.csv + registry_anonymized.csv + dataset_card) — ✅ VERIFIED
- **525 rows in both CSVs** (row counts counted directly). 509 vessel clips + 16 dedicated background; label counter: tug 188, cargo 97, passengership 71, other 40, background 38, fishing 34, pleasurecraft 32, dredger 8, sailing 6, tanker 5, rescue 4, pilotvessel 2.
- **178 unique hulls** ✅ (matches the 178-hull structure we track): `hull_id` non-null for 509 clips, unique 178; 22 background clips carry a hull_id (6 unique hulls — near-vessel ambient windows), 16 have none.
- metadata.csv `MMSI`: 179 unique; mapping MMSI↔hull is 1:1 (0 hulls with >1 MMSI, 0 MMSIs with >1 hull) — the extra MMSI is the one belonging to the hull of a dedicated-background clip.
- **Anonymization = MMSI → pseudonymous `hull_id`** (H123, H149, …): `registry_anonymized.csv` drops MMSI, keeps per-hull grouping. Vessel dimensions (length 77 unique values, beam 33) and AIS `class_code` retained.
- Per-clip covariates (22 columns): `clip_uid, label, duration_sec, path, utc_begin, utc_end, sample_rate, class_code, date, [MMSI|hull_id], length, beam, t1, c1, p1, sal, sv, *_norm`. t1/c1/p1/sal/sv are **CTD-derived** (SBE 19plus): **p1 = 144.5–149.2 dbar ⇒ hydrophone ~14.5–14.9 m depth**; t1 7.6–10.8 °C; sal 29.9–31.0 PSU; sound speed 1477–1490 m/s. 10 clips have empty covariates.
- **One deployment site only:** ONC icListen hydrophone **ICLISTENAF2523**, Strait of Georgia, BC, Canada (license ledger mentions LSBBL/FAE/CRIP deployment codes); **32 kHz mono**; period **2016-05-09 → 2017-05-28** but only **33 distinct UTC days** (≈ 5% duty); durations 119–2,220 s, total **56.0 h**.
- Scenario predicate: single AIS-tracked vessel inside 4,000 m inclusion radius, no other vessel within 6,000 m, ≥2 min sustained — labels are **AIS silver-standard, never human-verified** (their own words).
- Baseline (their ResNet-18, frozen split): **test macro-F1 = 0.2766** (seed 42), 5 seeds 42–46, clip-clustered bootstrap — the 12-class task is HARD; background/SNR-shift is the dominant error channel (mirrors our A58).
- Known data-quality findings disclosed in the audit pack: 167/525 clips are archive **wrap-around splices** (duration = span + 300 s); v1.3.x "strict" cut trims archive-boundary audio; published grouping "drops the first minute of every run"; raw v1 AIS streams survive only for 3 days (2016-09-02/08/10), bounding any re-audit.

### 1.6 License evidence — ✅ VERIFIED (their `license_evidence_v131.md`)
- ONC Data Policy quoted: ONC-sole-owned data are **CC-BY 4.0**, "can be re-used and redistributed without restriction, requiring only attribution, including intermixing with other datasets."
- Per-stream ledger: hydrophone audio (ICLISTENAF2523) = ONC-operated → redistributable CC-BY 4.0 with ONC attribution; AIS messages = third-party Digital Yacht receiver feed broadcast in the clear (ITU-R M.1371) → only derived interval tables/MMSI-UTC metadata redistributed, raw NMEA not redistributed; CTD → derived per-clip averages only.
- Attribution requirement: cite ONC (Oceans 3.0, **re3data 10.17616/R3RW43**) + the VTUAD descriptor. MMSI retained deliberately for vessel-identity-disjoint evaluation; anonymized registry shipped for those who prefer it.

### 1.7 ONC re3data DOI — ✅ VERIFIED
`10.17616/R3RW43` resolves (302) to **re3data r3d100011094 = "Oceans 3.0 Data Portal" / ONC / Ocean Networks Canada** (UVic initiative; repositoryURL data.oceannetworks.ca). Declaration's upstream pointer is correct.

---

## 2. Belgian company registry — core facts ✅ VERIFIED via KBO Public Search + VIES

### 2.1 KBO/BCE record (kbopub.economie.fgov.be, official KBO Public Search) — ✅ VERIFIED
Retrieved via deep link `https://kbopub.economie.fgov.be/kbopub/toonondernemingps.html?ondernemingsnummer=1033974468` (GET renders the entity page):

| Field | Value |
|---|---|
| Ondernemingsnummer (KBO) | **1033.974.468** |
| Status | **Actief**; rechtstoestand "normale toestand" since **4 February 2026** |
| Begindatum (founding) | **4 February 2026** |
| Naam | **Altinay, Selman** |
| Type entiteit | **Natuurlijk persoon** (natural person → sole proprietorship, NOT a BV/SA) |
| Founder (functies) | Altinay, Selman — "oprichter van een geregistreerde entiteit-natuurlijk persoon" since 4 Feb 2026 |
| VAT status | Onderworpen aan btw since 4 Feb 2026; inschrijvingsplichtige onderneming |
| Nacebel 2025 codes | 62.100 computer programming · 70.200 business/management consultancy · 58.290 other software publishing · 63.100 data processing/hosting · 62.200 computer consultancy |
| Establishments | 1 (address not shown in KBO public page) |

### 2.2 VIES VAT validation (ec.europa.eu) — ✅ VERIFIED
`BE 1033.974.468` → `isValid: true`, name **"Altinay, Selman"**, address **Wingerstraat 27, 3390 Tielt-Winge** (Flemish Brabant, Belgium). Independent confirmation of KBO holder + address.

### 2.3 Self-declared registry number — ✅ VERIFIED
ruicodex.com footer: "© 2026 Rui Codex. All rights reserved. **VAT · KBO/BCE: BE 1033.974.468**" — matches KBO/VIES exactly.

### 2.4 "2 employees" cross-check
- KBO registers **no employee counts** (that data lives at NSZ/NBB and is not public per-company) — ⛔ cannot verify from registry.
- Entity is a **sole proprietorship**; site and itch.io describe a founder-led studio with contractor-style "team of senior engineers" copy. LinkedIn company page (blocked, ⛔ HTTP 999) is the claimed source of "2 employees".
- **Assessment: ◐ PROBABLE** — "2 employees" is consistent with a 1-person KBO entity + 1 collaborator (e.g., Mirac Orhan as NL-based contractor); nothing contradicts it, nothing confirms it beyond LinkedIn.

### 2.5 Blocked / unavailable registry sources
| Source | Status |
|---|---|
| kbopub.economie.fgov.be name search | ⛔ JSF form requires session POST (ViewState); number-based deep link works (used above) |
| companyweb.be | ⛔ HTTP 403 (bot wall) |
| belgiancompanies.com, northdata.be, trendstop.tribkf.com, opendata.efis.be | ⛔ DNS not resolvable from sandbox |
| northdata.de | ⛔ HTTP 429 throttled |
| staatsbladmonitor.be | ⛔ company paths 404 (not indexed) |
| DDG html / lite (queries #2+) | ⛔ 202 anomaly-throttled after first query |
| Mojeek | ⛔ connection timeout |

---

## 3. People & digital footprint

### 3.1 Selman A. = **Selman Altinay** — ✅ VERIFIED (deanonymized from "Selman A.")
- ruicodex.com JSON-LD (`schema.org/Person`): `name: "Selman Altinay", jobTitle: "Founder & Lead Engineer", url: https://ruicodex.com/About` ✅
- /About page text: "Rui Codex is a Belgian software company led by its founder, **Selman Altinay**, an engineer with more than **12 years of experience**… .NET Python AI/ML Cloud Architecture ERP Systems Leadership" ✅
- itch.io profile (ruicodex.itch.io): "Belgian software engineering studio (**Tielt-Winge, Flanders**), founded in **2026** by **Selman Altinay**. We make mobile games and apps with Flutter and Unity: **39 titles live on Google Play (25 games, 14 apps)**." ✅ — corroborates VIES address + founding year.
- Devpost profile `devpost.com/ruicodex`: "Rui Codex's (ruicodex) software portfolio… specializes in C#, .NET, Flutter, Python, **Machine Learning**, Asp.Net Core, Dart, JavaScript, Unity, Sql Server, Odoo, **Ai Agents, Llm, and Automation**." ✅
- Site product/SEO surface: EveryTranslate (translation API), E-Pool Aqua (fish-farm management), Feedback Center, Yirmibes Web ERP; insurance-tech blog; service areas Brussels/Antwerp/Ghent/Leuven/Liège; languages EN/TR/DE/FR/NL. No Istanbul presence on the site itself (LinkedIn says Istanbul — ⚠ UNCONFIRMED, plausibly personal origin; KBO/VIES say Belgium).

### 3.2 GitHub — ✅ VERIFIED (three accounts; none disclose the competition)
| Account | What it is | Public repos |
|---|---|---|
| `github.com/RuiCodex` | Personal/org shell — "GitHub is where RuiCodex builds software." | **0** |
| `github.com/RuiCodex-dev` | Company dev account — og:description: "**Belgian software engineering studio: AI agents and automation, custom software, integrations, Odoo/ERP, and mobile apps and games (39 titles on Google Play)**" | 8: learn-ar-specs, scopecast ("Monte-Carlo fixed-price quotes… Build With AI: Basics 2026"), purser ("AI treasurer… PayPal Agent Toolkit + Gemini"), hearthnote ("NVIDIA Nemotron on Nebius Token Factory"), .github, hostwise, lumenloop-legal, starharbor-legal |
| `github.com/ruicodexxx` | Minor account | 1: test_prj |

**Zero repositories mention VTUAD, Zindi, underwater, acoustics, or any ML competition code.** Confirms the known statement that their GitHub does not disclose the competition project. GitHub code search for "VTUAD" rebuild scripts: only unrelated repos exist (`Sameraaryaa/VTUADDA` 2026-04, `mominali12/vtuad_personal` 2024-08) — no ruicodex code anywhere. GitHub core API was rate-limited mid-session (0 remaining); all findings above are from rendered HTML pages. ⛔ GitHub code-search API needs auth (not attempted further).

### 3.3 Mirac ORHAN — ⚠ UNCONFIRMED link to ruicodex
- Known: LinkedIn shows "Mirac ORHAN — Software Developer And Electronic Technician, Netherlands" as team-affiliated. LinkedIn itself: ⛔ HTTP 999 (authwall).
- **Not** found in KBO (sole proprietorship has exactly one named person), **not** on ruicodex.com/About, itch.io, Devpost, or any GitHub account. Web search for "Mirac Orhan" ⛔ (DDG 202-throttled, Bing query mangling, Mojeek timeout).
- **Assessment: PROBABLE contractor/collaborator but never verifiable from public artifacts; his existence does not change the capability model** (see §5).

### 3.4 Competition profiles
- **Zindi:** `https://zindi.world/users/ruicodex` exists ✅ — og:title "**🇧🇪 ruicodex - AI Builder on Zindi**", "Ranked **#7060** among 100,000+ AI builders". Belgium flag on profile. Profile body is JS-rendered (⛔ competition list not scrapeable via curl; LB for the event needs login). No second account found: `zindi.world/users/selmanaltinay` has no profile meta (⚠ page shell; treated as nonexistent).
- **Kaggle:** `kaggle.com/ruicodex`, `/selmanaltinay` → ⛔ reCAPTCHA browser check. UNCONFIRMED.

---

## 4. VTUAD upstream: what is original vs rebuilt — ✅ VERIFIED

1. **Original VTUAD dataset** = **Domingos, Skelton & Santos (2022), "VTUAD: Vessel Type Underwater Acoustic Data", IEEE DataPort, DOI `10.21227/msg0-ag12`** — DOI 302-resolves to `ieee-dataport.org/documents/vtuad-vessel-type-underwater-acoustic-data`, title verified, author surnames Domingos/Skelton/Santos present on page. (Matches our R7e provenance note: ONC Strait of Georgia, 1-s clips, 5 classes, 3 SNR distance scenarios 2–3/3–4/4–6 km; the original has an IEEE DataPort access/licensing gate.)
2. **The "rebuilt" line** (what ruicodex actually uses) = Yuan, Hao; Wang, Wenbo; Li, Tian; Chen, Guici; Zeng, Lingjiang; Liu, Sixian — **MDPI Preprints `10.20944/preprints202609.0617`** (v1 2026-09-08, v2 2026-09-20), title identical to the Zenodo deposit: *"VTUAD: An AIS-Auto-Labeled Vessel-Type Underwater Acoustic Dataset Reconstructed from Ocean Networks Canada Archives."* Abstract: fully scripted six-stage pipeline from the public ONC archive; AIS-aligned automatic labels; "AIS-derived silver-standard labels rather than manually verified acoustic ground truth." ✅ via Crossref.
3. The same group shipped a **constellation of companion Zenodo deposits in Oct 2026** (all verified via Zenodo search): cross-water four-corpus benchmark (10.5281/zenodo.23028253 + preprint 10.20944/preprints202609.1124), in-corpus SimCLR pretraining eval (10.5281/zenodo.23411528), general-purpose audio foundation-model eval with **VTUAD embedding caches** (10.5281/zenodo.23345657), open-world source-free adaptation (10.5281/zenodo.23328407), frozen splits/checkpoints repo (10.5281/zenodo.23312809). ⇒ This is an active, well-tooled research program, and all of it is public — nothing about their data is private advantage.
4. "Rebuilt" therefore means: **Yuan et al. re-generated the corpus from ONC raw archives with AIS auto-labeling** (v1.0.0 2026-09-03 → v1.3.2 2026-09-29), which made it CC-BY-4.0 and freely downloadable (the IEEE DataPort original is gated). ruicodex's "rebuilt" wording is faithful, not inflated.

---

## 5. Assessment

### (a) What the declaration implies tactically
- They use **exactly two audio bundles**: the strict re-cut vessel set (509 clips, 3.7 GB reassembled) + the 16-clip background zip — i.e., the *newest, boundary-clean* cut, not the older 25 GB loose per-class set. They deliberately skipped the precomputed log-mel store (16 kHz, 3-s segments — wrong granularity for a 60-s-window share task).
- **Features = ours.** "One-minute deci-decade band power with the starter notebook's reference conversion, no absolute calibration" is precisely the 25-band minute-level linear power pipeline in our `src/tol_convert.py` / `src/vtuad_ingest.py` (our ingest literally targets the same three parts + background zip from record 23037895). Their TOL/reference library will be nearly identical to ours. Any edge must come from *how* it is exploited, not *what* is computed.
- Most plausible usage: **auxiliary pretraining / mixture or reference-side prior** — e.g., vessel-vs-background discrimination and per-band vessel signatures from VTUAD feeding the share head, or per-class band-shape templates. A 12-class classifier does not transfer directly (their own baseline macro-F1 = 0.2766), and ONC BC audio is domain-shifted vs SA waters — they must be using it for *shape/prior*, not absolute levels ("no absolute calibration" confirms this).
- "Registry_anonymized" in their file list = they track **hull identity** (178 hulls) — the right thing for split hygiene — and "no attempt to identify which clip appears in any test window" is a competition-rules shield (ONC data is May 2016–May 2017 BC; Test windows are SA 2021+ — genuinely disjoint, and their declared features carry no site/state information that could leak).
- "Nothing is fitted on Test.csv" + SHA-256 + version pinning = reproducibility posture aimed at disqualification-proofing the external-data claim.

### (b) What is legally reusable by us
- **Everything they use, we may use identically.** CC-BY-4.0 with attribution (ONC + Yuan et al. descriptor) — no exclusivity, no account wall, 2,841 unique downloaders already. Our `src/vtuad_ingest.py` + `tol_convert.py` already implement the exact conversion; WAV download (~4.6 GB total for parts 01-03 + background) is the only missing step (already flagged "next round" in data-links.md).
- Attribution string for any submission/declaration: Yuan, H. et al., VTUAD (rebuilt) v1.3.2, Zenodo 10.5281/zenodo.23037895 (CC-BY-4.0); upstream ONC Oceans 3.0, re3data 10.17616/R3RW43.
- We may also reuse their derived artifacts (features zips, manifests, audit CSVs) under the same license if useful — e.g., `clip_acoustic_stats.csv` and the frozen manifests as sanity references.

### (c) Intel on their modeling angle & engineering culture
- **Careful-engineering culture, high release cadence is the depositor's (Yuan et al.), not ruicodex's** — ruicodex is a *consumer* of the deposit. But their declaration shows they read it closely (correct file names, correct reassembly procedure, correct upstream DOI) ⇒ competent data plumbing.
- Their stack (Devpost: .NET/Flutter/Unity/Odoo + "AI Agents, LLM, Automation"; hackathon participation "Build With AI: Basics 2026"; games studio side-business) = **generalist AI-automation builders, hackathon tempo, likely pragmatic LGBM/tabular or stock NN pipelines rather than bespoke deep-audio research**. Expect: solid feature engineering + ensembling + diligent validation, not novel architectures.
- Solo-proprietor + (probably) one collaborator ⇒ limited parallel experimentation capacity; #1 LB position suggests the band-power + prior-shrink family (very close to our r7 family) is currently winning — consistent with our LB autopsy (r7_v3 family).
- Zindi profile #7060 of 100k (aggregate rank, not event rank) = not a Zindi platform veteran; the #1 event position is likely their breakout event.

### 5.1 Threat read & recommended actions (for next plan revision — no plan.md edits made)
1. **Data parity is total**: same dataset, same conversion, same license. No asymmetry to close there; the lever is T1 station-fingerprint conditioning / wind-shape (our §7g) which their declared pipeline conspicuously lacks ("no absolute calibration", no site/state features mentioned).
2. Download the ~4.6 GB strict WAV set next round (parts 01-03 + background; SHA-256s in `README_vtuad_strict_wav_vessel_parts.txt` / `SHA256SUMS.txt` / `strict_interval_wav_SHA256SUMS.txt` already captured in `data/zenodo_r9/`) — closes the only gap between us and their declared setup.
3. Their "no test-window identification" line is a useful compliance template for our own declarations if we ship VTUAD-augmented models.

---

## 6. Blocked-source log
| # | Source | Reason |
|---|---|---|
| 1 | linkedin.com/company/ruicodex (+ people pages) | HTTP 999 authwall |
| 2 | kaggle.com/ruicodex, /selmanaltinay | reCAPTCHA browser check |
| 3 | companyweb.be | HTTP 403 bot wall |
| 4 | belgiancompanies.com, northdata.be, trendstop.tribkf.com, opendata.efis.be | DNS unresolvable from sandbox |
| 5 | northdata.de | HTTP 429 |
| 6 | staatsbladmonitor.be | 404 (entity not indexed) |
| 7 | kbopub name-search form | JSF ViewState POST required (number deep-link works) |
| 8 | DuckDuckGo html/lite after query #1 | 202 anomaly throttle |
| 9 | Mojeek | connection timeout |
| 10 | Bing | results query-mangled (served dictionary results for 'defense') — unusable |
| 11 | GitHub REST core API | unauthenticated rate limit exhausted mid-session (0 remaining); HTML pages used instead |
| 12 | Zindi competition leaderboard / profile detail | login required; profile body JS-rendered |

## 7. Probe log (80 network calls)
Zenodo: DOI resolution ×1, API record ×1, versions ×1, file downloads ×10, search ×1. re3data ×3. arXiv API ×1. GitHub: HTML ×8, REST search ×8, REST core ×6 (3 rate-limited). Crossref ×2. IEEE DataPort ×1. ruicodex.com ×3 (+About), itch.io ×2, Devpost ×2, openrocket wiki ×1. Registry: kbopub ×6, VIES ×2, staatsbladmonitor ×3, companyweb/northdata/trendstop/efis ×6, northdata.de ×1. Search engines ×8. Zindi ×2, Kaggle ×2, LinkedIn ×1. Local: checksum verification ×1, CSV analysis ×3 (no network).

**Local artifacts produced:** `/home/z/my-project/data/zenodo_r9/` (10 files listed in §1.3) — metadata.csv (525 rows, MD5-verified), registry_anonymized.csv (525 rows, SHA-256-verified), audit/license docs. No modifications to plan.md or submissions.
