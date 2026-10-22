---
license: CC-BY-4.0
authors:
  - name: Hao Yuan
    orcid: https://orcid.org/0009-0009-5544-5414
    affiliation: School of Mathematics and Systems Science, Wuhan University of Science and Technology; CSSC-LINCOM Electronics (Wuhan) Co., Ltd.
  - name: Wenbo Wang
    orcid: https://orcid.org/0000-0002-2130-7672
    affiliation: School of Mathematics and Systems Science, Wuhan University of Science and Technology
  - name: Tian Li
    orcid: https://orcid.org/0009-0002-3378-2646
    affiliation: CSSC-LINCOM Electronics (Wuhan) Co., Ltd.
  - name: Guici Chen
    orcid: https://orcid.org/0000-0002-3069-0829
    affiliation: School of Mathematics and Systems Science, Wuhan University of Science and Technology
  - name: Lingjiang Zeng
    orcid: https://orcid.org/0009-0001-2488-6657
    affiliation: CSSC-LINCOM Electronics (Wuhan) Co., Ltd.
  - name: Sixian Liu
    orcid: https://orcid.org/0009-0008-8317-5274
    affiliation: CSSC-LINCOM Electronics (Wuhan) Co., Ltd.
date-released: 2026-09-23
version: 1.3.0
---

# VTUAD (rebuilt) v1.3.0 - Dataset Card

## What is new in v1.3.0 (candidate)
1. `strict_interval_wav/` - all 525 clips re-cut to the exact AIS-qualified
   interval bounds (v1.2.0 released archive-aligned containers; both views
   describe the same scenarios).
2. `registry_anonymized.csv` - clip registry with the MMSI column removed;
   a persistent pseudonymous `hull_id` retains per-hull grouping for
   split isolation and provenance auditing without vessel identifiers.
3. Documentation: this dataset card, CITATION.cff, environment.yml.
4. `registry_verification_sample30.csv` (+ companion README) - manual
   registry-verification ledger: a stratified sample of 30 released MMSI
   (covering 9 of the 11 vessel classes; 82 of the 525 recordings)
   cross-checked on 2026-09-23 against the Canadian ISED vessel registry
   (NMID), VesselFinder, MarineTraffic, and MyShipTracking.
5. Packaging: the 525 strict-interval clips ship as two standard ZIP
   archives (deflate; WAV members byte-identical to the per-clip ledger):
   `vtuad_strict_wav_vessel.zip` (509 clips; uploaded as three equal
   byte-split parts `vtuad_strict_wav_vessel.zip.part01`-`.part03` -
   concatenate them in order to restore the archive, see
   `README_vtuad_strict_wav_vessel_parts.txt`) and
   `vtuad_strict_wav_background.zip` (16 clips) - the same single-archive
   convention as v1.2.0's per-class `vtuad_wav_*.zip` files. Inside the
   archives the
   `strict_interval_wav/inclusion_4000_exclusion_6000/{vessel,background}/`
   relative paths are preserved. `strict_interval_wav_SHA256SUMS.txt` lists
   the per-clip SHA-256 of every WAV inside the archives, so integrity can
   be verified per clip after extraction; per-file hashes are also
   traceable against the v1.2.0/v1.3.0 staging ledgers.
6. Static AIS field audit: `static_field_fill_audit.csv` (1,068 rows,
   hull x field) and `static_field_conflicts.csv` (178 rows, one per
   hull), with `static_audit_README.md`, document how each released
   `class_code`/`length`/`beam` was reconstructed from AIS static
   messages (primary single-line decode loses all multi-fragment type 5
   and - via a pyais `part_num`/`partno` key mismatch - type 24 part B
   messages; a reassembly-based static-fill patch rescues them,
   first non-null value in the deployment window wins), flag hulls that
   broadcast conflicting static values (15 in the surviving evidence
   window; none with two different real type codes), and cross-check the
   resolved codes against the shipped labels.

## Summary
VTUAD (rebuilt) is a 525-recording, 12-class vessel-type corpus for
underwater acoustic classification, independently regenerated from the
public Ocean Networks Canada (ONC) archive (hydrophone ICLISTENAF2523,
Strait of Georgia, 2016-05-09..2017-05-28) with fully automatic AIS-based
annotation. v1.2.0 provides 133,784 three-second log-mel segments with a
frozen, checksummed recording-level split (369/80/76) and a ResNet-18
baseline (test macro-F1 = 0.2766, seed 42).

## Label authority and known limitations
Labels derive from the AIS scenario predicate (single AIS-tracked vessel
inside the 4,000 m inclusion radius, no other AIS-tracked vessel inside
6,000 m, sustained >= 2 min), not from human listening. Known error
channels (AIS gaps/darkness, non-equipped traffic, class-code
misdeclaration) are documented in the v1.2.0 descriptor. A manual
registry cross-check of a stratified 30-MMSI sample (2026-09-23; ledger in
registry_verification_sample30.csv) confirmed 28/30 (93.3%), contradicted
none, and left 2 unresolved (suspected MMSI reuse after the recording
window; 3 recordings in total). v1.3.0 adds the
strict-interval view that removes archive-boundary audio outside the
qualified interval.

## Provenance
- Source streams: ONC hydrophone ICLISTENAF2523 (32 kHz), shore AIS
  receiver DIGITALYACHTAISNET1302-0097-01, CTD SBECTD19p6935.
- Construction code: released with v1.2.0 (code/), plus
  paper7_preB/b13_stage_v130.py for the strict re-cut and anonymization.
- DOI lineage: v1.2.0 (10.5281/zenodo.22274549) -> v1.3.0 (this draft).
