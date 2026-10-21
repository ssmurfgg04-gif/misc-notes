# intel_r10 — ruicodex round 2: execution-style profile, pipeline reconstruction, next-move prediction, external-data sweep, execute-better checklist

**Task:** R10-C · **Date:** 2026-10-22 · **Agent:** general-purpose · **Probes:** ~36 network calls (log §6)
**Privacy rule:** rival principals are referenced only as "founder" and "second member"; no personal identifiers.
**Baseline facts carried from R9 (VERIFIED):** Belgian sole proprietorship (KBO-registered 4 Feb 2026), founder-led, one probable NL-based collaborator ("second member"); declared external data = VTUAD rebuilt v1.3.2 (Zenodo 23037895, CC-BY-4.0, byte-identical to ours); declared method = one-minute deci-decade band power via the official starter conversion, no absolute calibration, no Test.csv fitting, no test-window clip identification; GitHub RuiCodex-dev had 8 repos, zero competition code; #1 on LB at 0.8720 vs pack 0.816–0.824.

---

## 1. Skill profile (founder + second member, from public execution artifacts)

### 1.1 New evidence this round (✅ fetched directly)

**itch.io (studio page):** 4 browser games live (Ringflip: Circus Pinball, Idle Defense: Cosmic TD, The Forbidden Index, Rainy Day), all self-described small-scope ("play in browser"), studio-branded, bio repeats "39 titles live on Google Play (25 games, 14 apps)" + "22 case studies" on the company site. No game jams visible on the profile page.

**Devpost profile:** **11 Projects, 12 Hackathons, 1 Achievement, 0 followers / 0 likes.** All 11 project pages fetched:
| Project | Theme | Stack | Signal |
|---|---|---|---|
| green-pipeline-steward | GitLab Duo agents, pipeline carbon cost | python | LLM-agent ops |
| scopecast | Monte-Carlo fixed-price quoting for freelancers | python, react, ts | statistical simulation, confidence levels |
| purser | AI treasurer w/ "mandate the agent can't break" (PayPal toolkit + Gemini) | node, react, ts | constraint-wrapped agents |
| hearthnote | family care notebook (NVIDIA Nemotron on Nebius) | node, docker | LLM app, sponsor-matching |
| hostwise | dinner-party host agent (Qloo taste graph) | node, docker | sponsor hackathon 2026 |
| inspectloop | PCB inspection: OpenCV checks vs golden board, "DNN patch memory" | **opencv, numpy, scikit-learn, python**, AWS | the only classical-CV/ML project |
| payloop | invoice-chasing agent, NL/FR/EN reply understanding | python, AWS SES/SNS | NL automation |
| pocket-grove | mixed-reality desk garden | C#, unity | game side |
| shelf-to-skin | beauty-shop skin-match w/ YouCam AI | node | integration |
| family-room | TV evening planner | android, zxing | integration |
| wordroom | AR Dutch learning (SPECS Lens) | ts, AR | integration |
**Zero winner/runner-up/prize badges found on any project page.** "1 Achievement" = participation-level.

**GitHub RuiCodex-dev (org page HTML):** now **10 repos** (R9 saw 8): learn-ar-specs, scopecast, purser, hearthnote, .github, hostwise, **tempoladder-legal (new), meterwise-legal (new)**, lumenloop-legal, starharbor-legal. Languages across all 10: **HTML ×8, TypeScript ×3, JavaScript ×2 — zero Python, zero notebooks, zero audio/ML.** The two new repos since R9 are legal/terms pages for new products — shipped within days of product launches. All descriptions are product one-liners; no stars/community traction visible. GitHub repository search for "whales-initiative" login-walled (logged).

**Zindi competition page (SSR text, no login needed):** 467 joined / 185 active, $5,000, close **13 Dec 2026** (reveal 29 Jan 2027), **submission limits: 2/day, 200 total**, team ≤4, public LB ≈ 30% of test, private = 70%, **metric = 1 − RMSE on share_added_vessel only**, "automl are not permitted", "do not set thresholds (or round your probabilities)", external acoustic datasets permitted with public declaration of source/versions/access; sponsor = French Embassy (Le Shift Lab) + SAEON; supported by SANBI, ITU AI for Good; **additional prizes for methodology or research write-ups** (pressure map on real SA data).

### 1.2 Profile synthesis

- **Execution archetype: high-throughput product generalist.** 39 Play Store titles + 4 itch games + 11 Devpost projects + 10 GitHub repos, all since ~2024 (company registered Feb 2026) — this is a "ship small, ship often" agency tempo, not a research tempo. The GitHub delta since R9 (+2 legal-page repos) shows continuous parallel shipping even mid-competition.
- **ML depth: thin but real.** Public ML evidence = one OpenCV/scikit-learn CV project, one Monte-Carlo confidence tool, and LLM-agent work throughout. No public deep-audio, no NN-training-at-scale, no calibration research. "machine-learning" is a listed skill; the absence of any Python on GitHub means all data-science work is in private repos.
- **Second member (NL):** "Software Developer and Electronic Technician" — electronics/DSP-adjacent profile, publicly invisible otherwise. Plausibly the person who makes the audio plumbing work, but UNCONFIRMED.
- **Compliance/repro discipline: high.** The declaration text (correct file names, SHA-256 mention, version pin, correct upstream DOI) plus version-pinned consumption of a 6-version Zenodo chain = careful data plumbing and DQ-shield posture. This is their strongest measurable trait.
- **Competition experience: low.** Zindi aggregate rank #7060/100k, no visible Devpost wins, this event is their breakout. They are not LB veterans; they are execution-speed novices-with-good-habits.
- **Implication for us:** their edge is NOT data (zero asymmetry, R9) and NOT research depth. It is (a) fast, disciplined iteration, (b) clean output handling, (c) full use of the 2-subs/day budget. Everything we do must therefore compete on the same axis: more submissions spent with more information extracted per submission, and zero hygiene losses.

---

## 2. Their method, reconstructed (assumptions + confidence)

### 2.1 The scoreboard algebra (from Zindi rules, fetched this round)

Metric = 1 − RMSE on `share_added_vessel` only, test windows equally weighted, public LB = 30% (~450 windows).
Truth = controlled addition: each test window is real SA background + an added vessel component with known energy fraction f ∈ [0,1].
Our measured constants (r7_shrink.py, three-LB): μ = E[f] = 0.13007576, E[f²] = 0.06057998 ⇒ **σ_f = 0.20895 ⇒ constant-at-μ scores 1 − 0.209 = 0.791.**

Convert the LB into correlation ρ between prediction and truth (RMSE² = σ_f²(1−2kρ+k²) for a shrink-to-μ family at factor k):
| LB score | RMSE | implied ρ at k=1 (raw) | implied ρ if k*=ρ (optimal shrink) |
|---|---|---|---|
| pack 0.816 | 0.184 | 0.612 | — |
| pack 0.824 | 0.176 | 0.645 | — |
| **leader 0.8720** | **0.128** | **0.812** | **0.790** |
| constant 0.791 | 0.209 | 0.000 (k=0) | — |

Reading: the pack sits at ρ ≈ 0.61–0.65; the leader needs effective ρ ≈ 0.79–0.81. **That is a +0.17 correlation jump over the pack — the largest single gap on the board is between "fitted something" and "modeled the background".**

### 2.2 Most-likely exact pipeline (with confidence)

1. **Data:** VTUAD v1.3.2 strict WAVs only (509 vessel clips, 3.7 GB reassembled + 926 MB background zip) + metadata.csv + registry_anonymized.csv (hull IDs kept → split hygiene). Deliberately skipped the precomputed 16 kHz/3 s log-mel store (wrong granularity for a 60-s share task). [conf 95% — declaration matches the file set exactly, R9-verified]
2. **Conversion:** the starter notebook's TOL conversion replicated on VTUAD clips — non-overlapping 2 s Hann-periodogram segments, integrated over the 25 base-10 deci-decades (31.6 Hz–7.9 kHz), linear mean of 30 segments/min ⇒ per-minute 25-band power for all 525 clips (56 h). Identical to our `src/tol_convert.py`. [conf 95%]
3. **Training signal = synthesized mixtures.** VTUAD clips are single-vessel (no share labels), so the only way to learn a share regressor is to mix vessel + background at controlled SNRs and compute the known share. A generalist reinvents exactly our mixture factory: mix VTUAD vessel clip + VTUAD background, share = E_vessel/(E_vessel+E_bg). [conf 75% — the only tractable supervised route; alternative = pure physics/bump-reading unsupervised (conf 15%), or presence-classifier + hand rule (conf 10%)]
4. **Features:** 25-band log power per minute + simple aggregates (tilt, LF/HF ratios, excess over a per-window or per-clip background reference). "No absolute calibration" implies relative/excess features survive the BC→SA domain shift. [conf 80%]
5. **Model:** GBDT (LightGBM/sklearn) — consistent with their stack and the tabular shape of the problem; small NN possible but there is zero public NN-training evidence. [conf 65% GBDT, 20% small NN, 15% other]
6. **Heads:** two outputs — share regressor + a detection-confidence score (presence probability or background-distance), matching the required columns. [conf 85%]
7. **Output handling:** shrinkage/flooring toward a conservative center and full-precision floats. Their 0.8720 sits at the optimal-shrink interpretation of ρ≈0.79, so SOME deliberate output calibration is almost certain (whether k was tuned on train CV or spent on LB probes). [conf 80%]
8. **Domain transfer:** no SA-domain calibration ("no absolute calibration"), no test-window identification — i.e., they deliberately forgo transductive tricks. [conf 90% that this is a real self-restriction, not a smokescreen: every declared element is checkable and has checked out]

### 2.3 Is 0.8720 consistent with "band-power + honest GBDT + good shrinkage" alone?

**Yes — with numbers, not vibes:**
- The controlled-addition design makes truth f a *deterministic function of observed band energies plus two nuisances* (background level/state, vessel spectral template). If you estimate the per-window background band vector (rolling quiet-bed / P20 machinery — the physics any careful generalist discovers) and carry a vessel spectral template from VTUAD, band-excess regression plausibly reaches ρ ≈ 0.75–0.85. Our own r7 pinned bump-reading family is *believed* to be in the 0.82–0.87 equivalent band on exactly this reasoning (pending our ρ readout), and it shares zero secret data with theirs.
- The pack's 0.816–0.824 (ρ 0.61–0.65) is what a *naively executed* version of the same data produces: regressor fit on bands without per-window background modeling, or with no output calibration. The +0.05 gap from pack to leader is fully explained by execution (background modeling + calibration), NOT by extra data.
- Would 0.8720 *require* something extra? Pseudo-labeling on test — contradicted by their declaration and unnecessary for ρ≈0.8 (label-free transduction helps maybe +0.005–0.015 at this scale; and they self-restricted). External AIS beyond VTUAD — the test truth is synthetic addition, so AIS adds nothing to share estimation. TTA/ensembling — worth +0.002–0.008; likely present but not decisive. **Verdict: 0.8720 is reachable honestly; nothing on the board proves cheating; the leader's advantage is execution quality on the same public inputs.** Confidence ~80%.
- Caveat: public LB = 30% (~450 windows) ⇒ 0.8720 carries ±~0.005 sampling noise; their true private score may differ. Also our constant math uses μ/E[f²] measured from LB constants on the *public* portion.

---

## 3. Next-move predictions (their remaining-lever priority)

Context: ~40 submission-days left (close 13 Dec), 2/day = ~80 subs left, 200 cap irrelevant. Solo+1, generalists, no SA hydrophone domain expertise, Zindi novices but fast shippers. Currently #1 public.

Predicted priority order (day-level):
1. **Output-calibration sweep (weeks 1–2):** k-shrink variants, floor softening, possibly a second submission pair to solve k* from two equations (our §7k #1 recipe — it's the standard play and they have the subs to burn). Cheapest points on the board.
2. **Background/reference modeling refinement:** per-window excess features, sequence context — the same lever our T1/T2 occupies. This is where the +0.05 pack-to-leader gap came from; expect incremental polish, not a jump.
3. **VTUAD exploitation deepening:** bigger/better mixture factory, per-class band-shape templates, hull-diversity weighting (registry_anonymized is exactly the UniqueShip hygiene input).
4. **Convenience external data — the Yuan-group companion deposits (see §4):** MIT-licensed embedding caches + trained checkpoints are the lowest-friction next grab for a generalist (no form, no email, no token). Also: more ONC Strait of Georgia background via the free ONC API token — unlabeled BC audio for background modeling. Unlikely: request-gated corpora (DeepShip/ShipsEar — email friction, research-only licenses), cross-domain NOAA/SanctSound.
5. **Ensembling/TTA (late-stage):** seed averaging, minute-shift TTA — worth a few thousandths; typical endgame filler.
6. **Pseudo-labeling on test windows: NOT expected** — their declaration explicitly forgoes Test.csv fitting; they have shown every declared claim to be verifiable so far.
7. **Research write-up investment (non-LB):** "additional prizes for methodology or research write-ups" + pressure-map requirement. Their agency DNA (case studies, docs) makes this likely — it does not move the LB but can move their total prize. **Note for us: the write-up prize is a parallel scoring track we are currently ignoring.**

If I were them with their constraints, I would: burn 2 subs/day on a k-sweep grid (0.30→0.60 in 0.05 steps, then fine-tune), rebuild the mixture factory with hull-disjoint splits, grab the MIT caches and ONC background, and stop. What they *can't easily do* without domain knowledge: notice the 3-fingerprint station structure (m01/m15 missingness), the G0/G1/G2 class split, wind-state handling, and south-coast site identification — the entire transductive layer we have already built (A59–A70, T1/T2, 08-slate). Their self-declared "no test-window identification" walls them off from it even if they noticed.

---

## 4. External-data sweep (on their behalf) — and our grab-first list

| # | Source | What | Access friction | License | Who should grab it, when |
|---|---|---|---|---|---|
| 1 | **Yuan-group FM embedding caches** — zenodo 23037895's sibling **23345657** (✅ re-verified today) | CLAP/wav2vec2/HuBERT/wav2vec2-large/**PANNs CNN14**/**BEATs iter3**/WavLM/AST embeddings of ALL VTUAD clips, 8 × 240–380 MB | none (direct DL) | **MIT** | **US — TONIGHT.** Zero-compute T5: frozen-embedding LGBM probe with per-station re-standardization (F2/F16). Also the rival's most convenient next grab — beat them to it |
| 2 | **Yuan-group frozen splits + checkpoints** — **23312809** (✅ verified today, 58 files, 1.34 GB) | trained VTUAD classifiers incl. `paper3_checkpoints_oceanship_family.zip` (291 MB), frozen splits, SHA-256 ledger | none | MIT | **US — tonight.** Ready-made vessel/background pseudo-labeler for BC audio + honest split reference |
| 3 | **Yuan-group UDA/SFUDA supplements** — 23028253, 23411528, 23328407, 23455106 (✅ all live) | CORAL/AdaBN code + benchmark artifacts for exactly our T5 recipe | none | MIT/CC-BY | US — with T5 build (7k #3) |
| 4 | **ONC Strait of Georgia full archive** (data.oceannetworks.ca) | ICLISTENAF2523 full deployments (VTUAD uses only 33 duty days / 56 h of a much larger archive) + other SoG hydrophones | free account + API token; portal JS-walled to scripts | CC-BY-4.0 | **Them: likely next grab** (more BC background for their factory). Us: medium (domain shift), but cheap once token exists |
| 5 | **UniqueShip 12class-5h subset** (uniqueshipdata.org, inventoried R1) | 4,218 vessels / vessel-disjoint benchmark | Google-Drive 10 GB chunks (rclone) | CC-BY-4.0 (ONC) | **US — start download tonight** (big). Direct F5 lever: vessel-diversity beats duration for the factory |
| 6 | **NOAA SanctSound TOL products** — NCEI PAcM + public GCS bucket `noaa-passive-bioacoustic` (✅ verified live today) | ready-made third-octave/PSD level products + raw audio, US sanctuaries | public bucket, no auth | US gov (public) | US — this week as extra background grammar for synthetic mixing (domain shift noted) |
| 7 | **Oceanship corpus** (121 h, 15 classes, AIS metadata; checkpoints hint at availability) | extra real-vessel clips | unclear (surface via 23312809 supplement) | check on grab | US — after #1–5 |
| 8 | SAEON / SA URN additional SA archives | more unlabeled SA minutes at the exact test domain | SAEON portal **timed out ×2 from sandbox**; try manual/user channel; our Sea Search/SAMSA/SAEON enquiry (A66 slate) is the human route | varies | **US — highest domain value; blocked for automation, push the enquiry** |
| 9 | DeepShip (265 ships) | vessel diversity | request form | research-only | low priority both sides (friction) |
| 10 | ShipsEar | vessel diversity | request + **not on organiser allowlist note** (R1 finding) | research-only | skip |
| 11 | IEEE DataPort original VTUAD 10.21227/msg0-ag12 | — | gated | — | skip (rebuilt version supersedes; R9-verified gated) |
| 12 | AURAL/Mingan, JASCO, ICES | cetacean/industry hydrophone archives | SLGO 403; no turnkey AIS-paired passive-noise product; ICES = fisheries echosounders (wrong modality) | — | skip (reasoned, probes logged) |
| 13 | "whales-initiative" | unknown referent | **UNRESOLVED** — DDG 202 ×2, Ecosia 403, Marginalia redirect-wall, GitHub search login-walled | — | deprioritize; no known public AIS-paired cetacean archive with band-level products |
| 14 | Zenodo "vessel noise" newest (Oct 2026) | new deposits | searched via API | — | only the Yuan constellation surfaced — nothing else to grab |

**Bottom line:** the only ungrabbed public assets that matter are #1–#4 + #6. All are license-clean and scriptable tonight except ONC (token) and SAEON (timeout). Nothing here is exclusive — zero data asymmetry persists — so the race stays an execution race.

---

## 5. "Execute better than them" checklist (ranked; our gaps found in plan §7g–§7k, r7/r8 scripts, and the PIN file)

1. **SPEND THE SUBMISSION.** r7_v3_k045 has been staged for two full rounds and still not submitted (worklog "blocked-on-user" in R8 AND R9). The rival converts 2 subs/day into information; we have converted zero since R7's constants. The ρ readout collapses our 0.82–0.87 uncertainty band into k* = ρ and decides r8 vs T5 pivot (7k #2). If the user won't submit tonight, pre-build the two-k hedge pair (k=0.35/k=0.55) so one ρ readout + one k readout solves the family exactly.
2. **Break the floor point-mass in our share vector.** The PIN file has **33.8% of rows at/near the shrink floor μ(1−k) = 0.07154 (260 rows exactly at min)** — the shrink erases all ordering among the calmest third of windows. Cheap upgrades, validate on group-split val: (a) soft floor = floor + ε·percentile-rank within the floor set; (b) per-window k(window) from val uncertainty (F11 ZOIB/conformal — already harvested in R9-A). This is exactly the kind of output-handling edge the leader is beating the pack with.
3. **One-file, one-command, asserted submission build.** Our chain (r7_repin → r7_shrink → PIN) has hardcoded paths OUTSIDE the repo tree (`/workspace/misc-notes-data/submissions/...` in r7_shrink.py) and no built-in final assertions. Make `scripts/submit_build.py`: one command → file + assertions (1,500 rows, ID order == Test.csv order ✅ (verified today), no NaN ✅, [0,1] ✅, no rounding/thresholding ✅ per Zindi rule) + SHA-256 ledger like the rival's declaration. Reproducibility IS the DQ shield; match and exceed theirs.
4. **Grab the MIT caches/checkpoints tonight (§4 #1–#3)** and wire the T5 probe (frozen PANNs/BEATs embeddings + per-station re-standardization + LGBM) so the 7k #2 pivot is executable the moment the ρ readout lands. UniqueShip subset download (#5) starts in parallel — it is the biggest vessel-diversity lever we have not pulled.
5. **Score column is zero-weight — cap effort there; the write-up is not.** Zindi eval text confirms LB = share only (matches our A33). Keep `score_added_vessel` honest-but-cheap; redirect one page of that effort to the pressure-map write-up, which carries **additional prizes** the rival (a documentation-native agency) is likely competing for and we currently ignore.
6. **Press our transductive edge; assume they never will.** Their declaration self-walls them off from test-side group fingerprints; our T1 (31.2% importance), A59–A70 station work, and planned AdaBN/CORAL per-group alignment (7k #3) are rules-legal (features only, no labels) and impossible for them to copy without abandoning their public statement. This is the one axis where we are structurally ahead — fund it.
7. **Private-split discipline.** Public LB = 30% (~450 windows ⇒ ±~0.005 noise). Decide on Spearman-vs-r7_v2 checks and the two-k solve, never on rank jitter. Reserve the last 3 days before 13 Dec for re-pinning best-known + write-up + declaration text (mirror the compliance template of their declaration, §5.1 of intel_r9).

---

## 6. Probe log (~36 network calls)

**OK (fetched):** itch.io profile ×1 · Devpost profile + 11 project pages ×12 · GitHub org repos HTML ×1 · Zindi competition page (wrong slug 404 ×1, correct slug 200 with SSR text ×1) · Zenodo API ×5 (23345657 ✓, search "vessel noise", search "Oceanship", 23312809 ✓, 23411528 ✓) · NOAA NCEI PAcM ×1 · GitHub rate_limit check ×1.
**Blocked / misses (do not re-probe):** Wayback (archive.org) timeout — unreachable from sandbox ×1 · SAEON data portal timeout ×2 · DuckDuckGo lite 202-throttle ×2 (both queries) · SLGO 403 ×1 · Ecosia 403 ×1 · Marginalia 302 wall ×1 · GitHub REST API 403 rate-limited ×2 (reset epoch 1792615924; not waited — HTML covered it) · GitHub raw README 404 ×2 (wrong default branch; abandoned, R9-A data reused) · ONC DataSearch = JS app, no scrapeable content ×1 · GitHub repo search login-walled ×1.
**Known-blocked, not retried (per directive):** LinkedIn (999), Kaggle (reCAPTCHA), companyweb (403).

**Local artifacts:** none created beyond this doc; no plan.md or submission changes. Probe evidence files in /tmp (dp_*.html, z_fm.json, z_splits.json, zindi2.html, etc.).
