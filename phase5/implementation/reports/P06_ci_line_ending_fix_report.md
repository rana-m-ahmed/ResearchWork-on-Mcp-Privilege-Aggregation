# P06 CI line ending fix report

## Summary
- Scoped git attributes were added to keep verified frozen text artifacts checked out with the line endings expected by `phase5/configs/upstream_artifact_registry.json`.
- Most verified files require CRLF checkout bytes, while five verified files retain LF checkout bytes because their registry hashes match the Git blob.
- Kaggle run planning now uses the frozen P05 evidence timestamp instead of checkout file mtime, keeping generated manifests stable in CI.

## Files changed
- `.gitattributes`
- `phase5/kaggle/run_planner.py`
- `phase5/tests/test_batch_partition_and_planner.py`
- `phase5/tests/test_domain_registry.py`
- `phase5/tests/test_scaffold_guards.py`

## Validation
- Added guard tests for the frozen checkout rules and registry/hash consistency.
- Added a regression test proving timing evidence generation ignores checkout mtime.
- Re-ran the Phase 5 registry and test suite locally after the change.
