# P06 CI prompt line ending fix report

## Summary
- CI collection reached the prompt compiler tests but failed when frozen prompt asset hashes were checked on Linux checkout bytes.
- The failing prompt assets were already consistent with `prompts/prompt_hash_manifest.json` on the verified Windows working tree.
- `.gitattributes` now forces `prompts/*.txt` to CRLF checkout bytes so CI materializes the same frozen prompt bytes without changing prompts or manifest hashes.

## Files changed
- `.gitattributes`
- `phase5/tests/test_scaffold_guards.py`

## Validation
- `git check-attr text eol -- prompts\phase3_tool_call_contract.txt prompts\phase3_tool_result_template.txt prompts\phase3_user_task_template.txt prompts\phase3_system_prompt.txt`
- `pytest -q phase5\tests\test_scaffold_guards.py phase5\tests\test_prompt_compiler_and_token_budget.py`
- `pytest -q phase5\tests`
- `python -m compileall phase5`
- `git diff --check`
- `python -c "import hashlib,json,pathlib; ..."`

## Result
- All prompt manifest hashes verified locally.
- Full Phase 5 test suite passed with `142 passed`.
- No frozen prompt text or prompt manifest content was rewritten.
