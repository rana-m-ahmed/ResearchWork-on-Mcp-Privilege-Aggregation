# P06 CI line ending fix report

## Summary
- Scoped git attributes were added to keep all verified frozen text artifacts checked out with CRLF line endings on all platforms.
- This preserves the verified SHA-256 values already recorded in `phase5/configs/upstream_artifact_registry.json` and prevents Linux CI from rehashing the same frozen files with LF-only bytes.

## Files changed
- `.gitattributes`
- `phase5/tests/test_scaffold_guards.py`

## Validation
- Added a guard test to assert the frozen trees retain explicit CRLF checkout rules.
- Re-ran the Phase 5 registry and test suite locally after the change.
