# I17R Final Launch Setup Report

## Scope

Resolved the three I17 blockers only: evidence branches, explicit source tag/commit notebook parameterization, and active M4 loader-status reconciliation. No official trials were executed. Phase 4 and Phase 4.5 frozen scientific artifacts were not modified.

## Source Authority

- New official source tag: `phase5-official-source-v2`
- Official source commit: `c38a339327891b229bcce12d7c04a8a4e6cc63d5`
- Official tag object: `38fab6c096f0de72a649eabd2f3c460ba8221ca7`
- Dataset version: `P5-DV-1.0.1-A7C91E42`
- Superseded before official dispatch: `phase5-official-source-v1`, `P5-DV-1.0.0-A7C91E42`
- Official accepted trials before supersession: `0`

## Evidence Branches

| Model slot | Evidence branch | Initial remote head |
| --- | --- | --- |
| `M1` | `phase5-model-1` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M2` | `phase5-model-2` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M3` | `phase5-model-3` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |
| `M4` | `phase5-model-4` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` |

## M4 Reconciliation

- Prior active status: `LOAD_FAILURE`
- Final non-official Kaggle status: `PASS`
- Active official run-plan status: `LOAD_SUCCESS`
- Executed source commit: `6e2cafe989ce60572a868b9a31dbcd0b6a1f8898`
- Executed `run_kaggle_smoke.py` SHA-256: `c708cd3c6eab21a420384025290d1a6fc2f4122a3cb644b88261e65c5e717a4d`
- Real synthetic generation: `PASS`
- Official trials executed: `0`

## Targeted Checks

- `python -m json.tool phase5\validation\kaggle_run_plan_v2.json > $null` -> PASS
- `python -m json.tool phase5\manifests\batch_partition_manifest_v2.json > $null` -> PASS
- `python -m json.tool phase5\validation\m4_loader_status_reconciliation.json > $null` -> PASS
- `pytest -q phase5\tests\test_kaggle_handoff.py phase5\tests\test_cli_contract.py phase5\tests\test_sync_github.py phase5\tests\test_campaign_runner.py phase5\tests\test_batch_partition_and_planner.py --basetemp phase5\.pytest_tmp_precommit` -> 45 passed
- `python phase5\scripts\lint_phase5_secrets.py` -> PASS
- `git diff --cached --check` -> PASS before source commit
- `git ls-remote --tags origin phase5-official-source-v2 phase5-official-source-v2^{}` -> tag and dereferenced commit visible
- `git ls-remote --heads origin phase5-model-1 phase5-model-2 phase5-model-3 phase5-model-4` -> all heads equal source commit

Strict Gate 0 was run before the source commit and failed only on `checkout-clean: working tree is dirty`. After the source commit, the v2 tag and branch checks established the final launch authority. No official trial command was run.

## Verdict

OFFICIAL KAGGLE LAUNCH PACKAGE VERDICT:
READY TO RUN M1
