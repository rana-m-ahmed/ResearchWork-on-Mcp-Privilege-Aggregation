# I17E Real Execution Adapter

## Verdict

`TARGETED_IMPLEMENTATION_REQUIRED`

## Completed

- Removed implicit campaign acceptance derived from `batch.row_count`.
- Made planning explicit through `--plan-only`; planning results always carry
  zero accepted rows and are never finalized.
- Added `OfficialDispatchBlockedError` and command-level refusal for official
  `run-batch` and `run-campaign` during I17E development.
- Added `RepositoryBatchExecutionAdapter`, which selects contiguous rows from
  the verified corrected queue bundle and requires a sealed session plus an
  explicitly marked real pipeline.
- Added strict acceptance-proof invariants for infrastructure, reset, schema,
  evidence hashes, uniqueness, and count eligibility.
- Kept all development lineage non-official, non-counting, and
  non-publication.
- Added replacement attempt indexing and parent lineage after orphaned or
  invalid attempts.
- Replaced the passive canonical notebook with a deterministic operational
  notebook containing source verification, pinned dependency preparation,
  Gate 0, model verification, synthetic canary, resume planning, exact operator
  confirmation, seal/sync/reverify stages, and an I17E dispatch lock.

## Verification

- `python -m compileall -q phase5` -> PASS
- `python -m pytest phase5/tests -q` -> 236 passed
- `python phase5/scripts/check_phase5_instructions.py` -> PASS
- `python phase5/scripts/lint_phase5_secrets.py --root phase5` -> PASS
- `python phase5/scripts/lint_phase5_forbidden_analysis.py --root phase5` -> PASS
- Official campaign refusal -> exit 70 before dispatch
- Plan-only campaign -> exit 0, accepted count 0, finalized count 0

## Remaining Implementation Gaps

- `load_frozen_state_machine_controls()` still intentionally raises instead of
  returning a verified control mapping.
- The frozen model backend adapter validates identity but does not expose a
  concrete inference implementation for the campaign adapter.
- A concrete task-content resolver and complete grading/materialization hook
  composition have not yet been bound into `RepositoryBatchExecutionAdapter`.
- The canonical notebook remains protected by `I17E_DEVELOPMENT_LOCK = True`.
- Real non-official Kaggle qualification across all four models has not run.
- Independent readiness audit, v3 tag creation, and evidence-branch
  initialization have not run.

## Safety State

- Official trials executed: 0
- Official accepted evidence created: no
- Phase 4 / Phase 4.5 files modified: no
- Official tags created or moved: no
- Official evidence branches changed: no
