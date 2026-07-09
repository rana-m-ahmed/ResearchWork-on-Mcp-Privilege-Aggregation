# Remediated Trial Ordering Generation Report

**Timestamp (UTC):** 2026-07-09T20:07:44.474823+00:00
**Software Version:** 1.0.0

## Purpose
Generate a strict deterministic trial schedule for Phase 5 conforming to the 7-column schema.

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
  "core_hash": "a81ce0d93df2fae979ccd1ddf42c11016f61a18d970c2b3d5ee67255ef9528a5",
  "core_trials": 5400,
  "defense_hash": "233389d23c20ae158e23c67fab430e05e93141dceb038b6b8483c7404a8bf4c0",
  "defense_trials": 2400,
  "utility_hash": "8677fd1c21a7387ad94d6800e72008f500cfa3535b461d3b24fd155c5bbd4c28",
  "utility_trials": 2400
}
```
