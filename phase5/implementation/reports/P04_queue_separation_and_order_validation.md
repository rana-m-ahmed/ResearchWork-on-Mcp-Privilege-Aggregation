# P04 Frozen Queue Loading Report

## Verdict

- Task: `P04`
- Status: `PASS`
- Generated UTC: `2026-07-10T13:02:48.682688Z`

## Summary

Frozen queue loading passed with strict hash verification, queue separation, exact order preservation, and registry-bound row reconciliation.

## Queue Metrics
- core: `{"by_defense": {"BASELINE": 5400}, "by_density": {"D1": 1800, "D3": 1800, "D5": 1800}, "by_model": {"M1": 1350, "M2": 1350, "M3": 1350, "M4": 1350}, "duplicates": [], "first_row_reference": "core:00001:T04470", "last_row_reference": "core:05400:T01066", "non_empty_cells": 64800, "queue_name": "core", "row_count": 5400, "statuses": ["PENDING"], "unique_rows": 5400, "unique_trial_ids": 5400}`
- defense: `{"by_defense": {"IHR_SPCE": 2400}, "by_density": {"D3": 1200, "D5": 1200}, "by_model": {"M1": 600, "M2": 600, "M3": 600, "M4": 600}, "duplicates": [], "first_row_reference": "defense:00001:T05752", "last_row_reference": "defense:02400:T06478", "non_empty_cells": 28800, "queue_name": "defense", "row_count": 2400, "statuses": ["PENDING"], "unique_rows": 2400, "unique_trial_ids": 2400}`
- utility: `{"by_defense": {"BASELINE": 1200, "IHR_SPCE": 1200}, "by_density": {"D3": 1200, "D5": 1200}, "by_model": {"M1": 600, "M2": 600, "M3": 600, "M4": 600}, "duplicates": [], "first_row_reference": "utility:00001:T09699", "last_row_reference": "utility:02400:T09706", "non_empty_cells": 26400, "queue_name": "utility", "row_count": 2400, "statuses": ["PENDING"], "unique_rows": 2400, "unique_trial_ids": 2400}`

## Findings
- none

## Frozen Inputs
- Upstream registry: `753441faa3aff10fbf081e4dc2d405f1492da6a51d0f26e287618f3e1064a431`
- Defense freeze: `5934137bd5e741b1ce700879691040d215648b409316c3cf09bc559b098d47a8`
- Payload reference map: `a14fb6217f7484135c71530cf2521fd149b35b5e60f73a8340fdef0adbaebafe`
- Phase 4 cryptographic lock: `4a5ed03c2a7bee2b8ef985fcb67ccaeaebe7d85d10cee21afec3ff88a3cc274d`
- Phase 5 execution manifest: `5613a19080400ca5e41a9d3e38d3f0221a22c2676b6fc0da6c119b9494a91505`
- Trial order core: `d97c7dda394aace668d2916b71b5bea36416af425dfbe1a99b25c0c128630711`
- Trial order defense: `1a391e9dcd35e0d6c0a8f1690cfb2b6c388f71cddbfabb5db2fef93f9b916588`
- Trial order utility: `3d4588b35e5453cf981f19f6a25f35f9f1e74aa66f9bcb9f41bac59f82bed94a`

## Queue Hashes
- core: `d97c7dda394aace668d2916b71b5bea36416af425dfbe1a99b25c0c128630711`
- defense: `1a391e9dcd35e0d6c0a8f1690cfb2b6c388f71cddbfabb5db2fef93f9b916588`
- utility: `3d4588b35e5453cf981f19f6a25f35f9f1e74aa66f9bcb9f41bac59f82bed94a`
