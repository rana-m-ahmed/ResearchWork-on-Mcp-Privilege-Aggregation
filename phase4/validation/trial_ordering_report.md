# Trial Ordering Generation Report

**Timestamp (UTC):** 2026-07-04T20:23:19.610366+00:00
**Software Version:** 1.0.0

## Purpose
Generate a strict deterministic trial schedule for Phase 5.

## Inputs Evaluated
- phase3/tasks/task_corpus.json
- phase2_5/inputs/payload_approved_set.json
- phase4/configs/model_set_freeze.yaml

## Checks Performed
- Cross-product generation
- Deterministic PRNG shuffle (seed 42)

## Summary
Status: PASS

Generated 36 unique trial combinations successfully utilizing valid upstream artifacts.

## Failures
No failures detected.

## Warnings
No warnings detected.

## Recommendations
- Lock CSV hash into cryptographic manifest.

## Evidence Log
```json
{
  "total_trials": 36,
  "models_included": [
    "M1",
    "M2",
    "M3",
    "M4"
  ],
  "densities_included": [
    "D1",
    "D3",
    "D5"
  ],
  "payload_conditions": [
    "CLEAN",
    "POISON-TD",
    "POISON-CA"
  ]
}
```
