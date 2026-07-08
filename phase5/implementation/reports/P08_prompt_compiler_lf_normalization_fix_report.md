# P08 prompt compiler LF normalization fix report

## Summary
- CI exposed a platform-dependent byte mismatch in `test_null_payload_compile_matches_golden_fixture`.
- Frozen prompt assets are still verified against their manifest bytes, including CRLF checkout bytes where required.
- The compiled prompt artifact now normalizes final assembled prompt text to LF before encoding, making prompt bytes deterministic across Windows and Linux.
- The null-payload golden metadata was updated only for the compiled prompt byte length, SHA-256, and prompt token counts.

## Files changed
- `.gitattributes`
- `phase5/runtime/prompt_compiler.py`
- `phase5/tests/fixtures/p08/compiled_prompt_null_payload.txt`
- `phase5/tests/fixtures/p08/compiled_prompt_null_payload_metadata.json`
- `phase5/tests/test_prompt_compiler_and_token_budget.py`
- `phase5/tests/test_scaffold_guards.py`

## Validation
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py::test_null_payload_compile_matches_golden_fixture phase5\tests\test_prompt_compiler_and_token_budget.py::test_compile_normalizes_prompt_bytes_to_lf`
- `pytest -q phase5\tests\test_prompt_compiler_and_token_budget.py`
- `pytest -q phase5\tests`
- `python -m compileall phase5`
- Prompt manifest hashes verified locally against `prompts/prompt_hash_manifest.json`.

## Result
- Full Phase 5 test suite passed with `143 passed`.
- The compiled null-payload prompt now matches the LF golden fixture bytes.
- Empty `tool_results` marker behavior was preserved because the checked-in golden fixture includes `<|tool_results|>`.
