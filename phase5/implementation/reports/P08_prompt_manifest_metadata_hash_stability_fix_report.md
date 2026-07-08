# P08 prompt manifest metadata hash stability fix report

## Summary
- The latest `phase5-source-ci` run `28935792078` failed on commit `fc05cf2` in the `Unit tests` step.
- A clean local clone with `core.autocrlf=false` reproduced the failure in `test_null_payload_compile_matches_golden_fixture`.
- The remaining mismatch was `bundle.manifest_sha256`; the Windows checkout hashed CRLF working-tree bytes while the clean clone hashed LF working-tree bytes for `prompts/phase3_prompt_manifest.json`.
- Prompt bundle metadata now hashes the parsed prompt manifest as canonical JSON, making metadata stable across checkout line-ending modes.
- Raw frozen prompt asset hashes are still verified against `prompts/prompt_hash_manifest.json`.

## Files changed
- `phase5/runtime/prompt_compiler.py`
- `phase5/tests/test_prompt_compiler_and_token_budget.py`
- `phase5/tests/fixtures/p08/compiled_prompt_null_payload_metadata.json`
- `phase5/implementation/reports/P08_prompt_manifest_metadata_hash_stability_fix_report.md`
- `phase5/implementation/reports/P08_prompt_manifest_metadata_hash_stability_fix_report.json`

## Validation
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py::test_manifest_metadata_hash_is_line_ending_stable phase5\tests\test_prompt_compiler_and_token_budget.py::test_null_payload_compile_matches_golden_fixture` -> `2 passed`
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py` -> `15 passed`
- `python phase5\scripts\check_phase5_frozen_paths.py --changed phase5/runtime/prompt_compiler.py phase5/tests/test_prompt_compiler_and_token_budget.py phase5/tests/fixtures/p08/compiled_prompt_null_payload_metadata.json` -> `phase5 frozen path guard: PASS`
- `pytest -q phase5\tests` -> `144 passed`
- `python -m compileall phase5` -> `PASS`
- `python phase5\scripts\check_phase5_instructions.py` -> `phase5 instruction hierarchy: PASS`
- `python phase5\scripts\lint_phase5_forbidden_analysis.py --root phase5` -> `phase5 forbidden analysis lint: PASS`
- `python phase5\scripts\lint_phase5_secrets.py --root phase5` -> `phase5 secret lint: PASS`

## Notes
- Clean-clone reproduction before the fix showed `manifest_sha256` as `f1e935dd34ea1e8ff8af0f291714f11d85592a03011c5f36fff07adfa54da71a` while the old fixture expected `5c97477483e62ce9ed192f55e1afacef687c9d2dd4d1599cb7925f465022c0af`.
- The updated canonical metadata digest is `7552c194e9f0faa771e632edf06ebc8b47169d83d620f6fc404a53f6451bed1d`.
- No Phase 4 or Phase 4.5 files were modified.
