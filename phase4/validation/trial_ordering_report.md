# Trial Ordering Generation Report

**Timestamp (UTC):** 2026-07-07T13:20:58.471849+00:00
**Software Version:** 1.0.0

## Purpose
Generate a strict deterministic trial schedule for Phase 5.

## Inputs Evaluated
- phase4/configs/phase5_schema_freeze.json
- phase1/ledger/payload_provenance_ledger.json
- phase4/configs/model_set_freeze.yaml
- phase4/configs/defense_config_freeze.yaml

## Checks Performed
- Cross-product generation
- Isolated PRNG shuffle (seed 42)
- Trial uniqueness check
- Payload integrity check

## Summary
Status: PASS

Generated 2808 unique trial combinations deterministically utilizing valid upstream artifacts.

## Failures
No failures detected.

## Warnings
No warnings detected.

## Recommendations
- Lock CSV hash into cryptographic manifest.

## Evidence Log
```json
{
  "defenses_included": [
    "IHR_SPCE"
  ],
  "densities_included": [
    "D1",
    "D3",
    "D5"
  ],
  "models_included": [
    "M1",
    "M2",
    "M3",
    "M4"
  ],
  "payload_count": 234,
  "total_trials": 2808,
  "trial_order_sha256": "2c0e96bd07245b95021c6521b7730db645acbd7686af6bb8127e7d36f3fb426f"
}
```
