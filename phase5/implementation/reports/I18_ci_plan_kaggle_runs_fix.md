# I18 CI Plan Kaggle Runs Fix

## Summary

- Fixed the `plan-kaggle-runs` CLI exit-code 20 failure by making the batch manifest markdown renderer match the checked-in v2 artifact exactly.
- Updated the CLI contract test to assert the active reconciled v2 batch manifest path.
- Shortened finalization bundle temporary staging directory names to avoid Windows path-length failures while preserving the final output path and atomic write semantics.

## Root Cause

`python -m phase5 plan-kaggle-runs ...` rebuilt `phase5/manifests/batch_partition_manifest_v2.md` with one extra trailing blank line. The immutable write guard correctly refused to rewrite the existing artifact and returned `FROZEN_ARTIFACT_HASH_FAILURE` exit code `20`.

The test contract also still checked the original `batch_partition_manifest.json` even though the active official planner defaults and campaign commands now use `batch_partition_manifest_v2.json`.

## Changed Paths

- `phase5/queues/batch_partitioner.py`
- `phase5/tests/test_cli_contract.py`
- `phase5/evidence/manifest_builder.py`
- `phase5/implementation/reports/I18_ci_plan_kaggle_runs_fix.md`

## Verification

- `python -m phase5 plan-kaggle-runs --timing-report phase4_5/validation/phase45_kaggle_quota_feasibility_report.md --safe-session-hours 7.5 --output .tmp/kaggle_run_plan.json` -> PASS, exit `0`
- `python -m pytest phase5/tests/test_cli_contract.py::test_plan_kaggle_runs_cli_writes_outputs -q` -> PASS
- `python -m pytest phase5/tests/test_cli_contract.py phase5/tests/test_batch_partition_and_planner.py phase5/tests/test_campaign_runner.py phase5/tests/test_kaggle_handoff.py -q` -> PASS, `35 passed`
- `python -m pytest phase5/tests -q` -> PASS, `227 passed`
- `python -m compileall phase5` -> PASS
- `python phase5/scripts/check_phase5_instructions.py` -> PASS
- `python phase5/scripts/lint_phase5_forbidden_analysis.py --root phase5` -> PASS
- `python phase5/scripts/lint_phase5_secrets.py --root phase5` -> PASS
- `python -m pytest phase5/tests/test_scaffold_agreements.py -q` -> PASS
- `python -m pytest phase5/tests/test_scaffold_workflows.py -k schema -q` -> PASS
- `python -m pytest phase5/tests/test_scaffold_imports.py -q` -> PASS
- `python -m pytest phase5/tests/test_scaffold_guards.py -k "instruction or frozen or evidence" -q` -> PASS
- `python -m pytest phase5/tests/test_scaffold_workflows.py -k checkpoint -q` -> PASS
- Phase 5 workflow YAML parse -> PASS

Local Windows note: pytest commands that use `tmp_path` require a writable temp root on this machine, so full-suite verification was run with `TMP` and `TEMP` pointed at a repo-local scratch directory. The scratch directory was removed after verification.
