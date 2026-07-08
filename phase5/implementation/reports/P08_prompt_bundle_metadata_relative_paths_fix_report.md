# P08 prompt bundle metadata relative paths fix report

## Summary
- CI golden fixture comparison can fail when compiled prompt metadata serializes checkout-local absolute paths.
- Prompt bundle metadata now records the frozen prompt manifest locations as repository-relative paths.
- The null-payload golden metadata fixture was updated only for `bundle.manifest_path` and `bundle.hash_manifest_path`.
- Regression coverage asserts that bundle metadata paths remain relative.

## Files changed
- `phase5/runtime/prompt_compiler.py`
- `phase5/tests/test_prompt_compiler_and_token_budget.py`
- `phase5/tests/fixtures/p08/compiled_prompt_null_payload_metadata.json`
- `phase5/implementation/reports/P08_prompt_bundle_metadata_relative_paths_fix_report.md`
- `phase5/implementation/reports/P08_prompt_bundle_metadata_relative_paths_fix_report.json`

## Frozen inputs
- `prompts/phase3_prompt_manifest.json`
- `prompts/prompt_hash_manifest.json`
- `prompts/phase3_system_prompt.txt`
- `prompts/phase3_tool_call_contract.txt`
- `prompts/phase3_user_task_template.txt`
- `prompts/phase3_tool_result_template.txt`
- `phase4/configs/model_4_freeze.yaml`
- `phase5/configs/upstream_artifact_registry.json`

## Validation
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py::test_frozen_prompt_bundle_matches_hash_manifest phase5\tests\test_prompt_compiler_and_token_budget.py::test_null_payload_compile_matches_golden_fixture` -> `2 passed`
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py` -> `14 passed`
- `python phase5\scripts\check_phase5_instructions.py` -> `phase5 instruction hierarchy: PASS`
- `python phase5\scripts\lint_phase5_secrets.py` -> `phase5 secret lint: PASS`
- `python phase5\scripts\check_phase5_frozen_paths.py --changed phase5/runtime/prompt_compiler.py phase5/tests/test_prompt_compiler_and_token_budget.py phase5/tests/fixtures/p08/compiled_prompt_null_payload_metadata.json` -> `phase5 frozen path guard: PASS`
- `pytest -q phase5\tests` -> `143 passed`
- `python -m compileall phase5` -> `PASS`
- `git diff --check` -> `PASS with line-ending warnings only`

## Notes
- Pytest emitted cache-write warnings because `.pytest_cache` is not writable in this checkout; tests still passed.
- No Phase 4 or Phase 4.5 files were modified.
