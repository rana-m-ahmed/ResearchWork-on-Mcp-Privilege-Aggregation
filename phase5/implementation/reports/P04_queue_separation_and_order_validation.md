# P04 Frozen Queue Loading Report

## Verdict

- Task: `P04`
- Status: `PASS`
- Generated UTC: `2026-07-07T20:11:07.099847Z`

## Summary

Frozen queue loading passed with strict hash verification, queue separation, exact order preservation, and registry-bound row reconciliation.

## Queue Metrics
- core: `{"by_defense": {"IHR_SPCE": 2808}, "by_density": {"D1": 936, "D3": 936, "D5": 936}, "by_model": {"M1": 702, "M2": 702, "M3": 702, "M4": 702}, "duplicates": [], "first_row_reference": "core:00001:T00534", "last_row_reference": "core:02808:T02620", "non_empty_cells": 22464, "queue_name": "core", "row_count": 2808, "statuses": ["PENDING"], "unique_rows": 2808, "unique_trial_ids": 2808}`
- defense: `{"by_defense": {}, "by_density": {}, "by_model": {}, "duplicates": [], "first_row_reference": null, "last_row_reference": null, "non_empty_cells": 0, "queue_name": "defense", "row_count": 0, "statuses": [], "unique_rows": 0, "unique_trial_ids": 0}`
- utility: `{"by_defense": {}, "by_density": {}, "by_model": {}, "duplicates": [], "first_row_reference": null, "last_row_reference": null, "non_empty_cells": 0, "queue_name": "utility", "row_count": 0, "statuses": [], "unique_rows": 0, "unique_trial_ids": 0}`

## Findings
- none

## Frozen Inputs
- Upstream registry: `332dd39debd845e7cc222131eddd058ab45d64bb8856bdfaa971055acec50e7b`
- Defense freeze: `5934137bd5e741b1ce700879691040d215648b409316c3cf09bc559b098d47a8`
- Payload reference map: `a14fb6217f7484135c71530cf2521fd149b35b5e60f73a8340fdef0adbaebafe`
- Phase 4 cryptographic lock: `09122acabc4ea034aae2ea43adfbfb9b6b370e926db1222861d11d37e87cd11f`
- Phase 5 execution manifest: `290a397e795a40dc97f497ada3a6c42c1d5ffdec2bdeb03046565996c2b350c2`
- Trial order core: `2c0e96bd07245b95021c6521b7730db645acbd7686af6bb8127e7d36f3fb426f`
- Trial order defense: `cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182`
- Trial order utility: `66f088402c2a494a12fadd542477c6f1463583508e492217816e9fca15f79de7`

## Queue Hashes
- core: `2c0e96bd07245b95021c6521b7730db645acbd7686af6bb8127e7d36f3fb426f`
- defense: `cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182`
- utility: `66f088402c2a494a12fadd542477c6f1463583508e492217816e9fca15f79de7`
