# Remediated Trial Ordering Generation Report

**Timestamp (UTC):** 2026-07-09T15:44:14.414135+00:00
**Software Version:** 1.0.0

## Purpose
Generate a strict deterministic trial schedule for Phase 5 conforming to the 12-column schema.

## Inputs Evaluated
- phase4/configs/phase5_schema_freeze.json
- phase1/ledger/payload_provenance_ledger.json
- phase4/configs/model_set_freeze.yaml
- phase4/configs/defense_config_freeze.yaml

## Checks Performed
- Cross-product generation
- Isolated PRNG shuffle (seed 42)

## Summary
Status: PASS

Generated queues:
Core: 5400
Defense: 2400
Utility: 2400

## Failures
No failures detected.

## Warnings
No warnings detected.

## Recommendations
- Lock CSV hashes into cryptographic manifest.

## Evidence Log
```json
{
  "core_hash": "92ae497f768dce21705660eded2d74379a56f550e4183ea7654d76ef759ad9db",
  "core_trials": 5400,
  "defense_hash": "22b961b5cdec2efbd5abfb4cc9356026ffe359c2eb66288b263ee25011d09207",
  "defense_trials": 2400,
  "utility_hash": "16ec83b0cb2a8db756247273e25330c806216a23c7c5ad7cd75e86312700685d",
  "utility_trials": 2400
}
```
