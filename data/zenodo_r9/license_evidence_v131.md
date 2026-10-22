# VTUAD (rebuild) — Per-stream license evidence (v1.3.1 supplementary)

Scope: redistribution basis for every upstream data stream used by this release.
Compiled 2026-09-29; URLs verified by direct access on that date.

## Governing policy

Ocean Networks Canada (ONC) Data Policy (https://www.oceannetworks.ca/data/data-policy/, accessed 2026-09-29):

- "All data solely-owned by ONC are available free of charge … under a Creative Commons CC-BY 4.0 License, open and free for anyone to use with attribution."
- "Data owned or co-owned by a data partner may be subject to alternative licensing such as a Creative Commons CC-BY-NC license, or a more restrictive license … In such cases … the notice on the ONC dataset page prevails."
- ONC-owned data "can be re-used and redistributed without restriction, requiring only attribution, including intermixing with other datasets."

## Per-stream ledger

| Stream | ONC device / source | Used for | Ownership basis | Redistribution in this release |
|---|---|---|---|---|
| Hydrophone audio (ICLISTENAF2523, LSBBL/FAE/CRIP deployments) | ONC hydrophone, Strait of Georgia / Campbell River | 525 released WAV clips (32 kHz), strict-interval re-cuts | ONC-operated instrument; no partner restriction notice on the dataset pages at compile time | CC BY 4.0 with ONC attribution (12 per-class zips + strict volumes) |
| AIS messages (DIGITALYACHTAISNET1302-0097-01 receiver feed) | Shore AIS receiver network feed hosted in the ONC archive | Scenario-interval tables (06a), per-clip MMSI/UTC provenance | Third-party AIS receiver network (Digital Yacht AISNet) delivered through ONC; AIS messages are broadcast in the clear on public VHF channels (ITU-R M.1371) | Derived interval tables and MMSI/UTC metadata only; raw NMEA not redistributed. If the ONC dataset page adds a partner notice, that notice prevails |
| CTD casts (SBE 19plus, 1,020 daily files) | ONC CTD instrument | Per-clip environmental covariates in metadata.csv | ONC-operated instrument | Derived per-clip averaged values only (t1/c1/p1/sal/sv + normalized) |

## Notes

1. Attribution required by this release: cite ONC (Oceans 3.0, re3data 10.17616/R3RW43) and the VTUAD descriptor.
2. Where any individual data stream later carries a partner sharing restriction, the notice on the corresponding ONC dataset page prevails over this file.
3. MMSI numbers are retained deliberately: they are broadcast in the clear on public VHF and are required for vessel-identity-disjoint evaluation; an anonymised registry (registry_anonymized.csv) is shipped for users who prefer it.
