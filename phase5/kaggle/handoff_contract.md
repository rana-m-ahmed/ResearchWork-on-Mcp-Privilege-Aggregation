# P15 Handoff Contract

This contract defines the allowed shape of the Kaggle-native handoff interface.
It is intentionally narrow.

## Scope

- Build a notebook that prepares future Kaggle validation.
- Keep the notebook thin and deterministic.
- Route bootstrap, session, sync, and finalize actions through the public
  `python -m phase5` CLI.
- Keep notebook parameters limited to source references, branch references, and approved
  operational limits.

## Allowed Parameters

- `repository_branch`
- `source_tag_or_commit`
- `model_branch`
- `evidence_branch`
- `approved_operational_limits`

The approved operational limits object is limited to:

- `safe_session_hours`
- `checkpoint_barrier_interval_trials`

## Forbidden Content

- Scientific logic, parser logic, queue logic, or grader logic inside notebook
  cells.
- Output repair, hidden retries, or nested Docker assumptions.
- Secret values.
- Branch-HEAD source execution for official launch.
- Trial execution in this task.
- Rebalancing or recreating the frozen trial matrix.

## Required Sync Behavior

After sync, the notebook must not continue until the CLI re-verification step
and reseal step succeed.

## Secret Handling

Use Kaggle Secret names only. Do not hardcode credential values into cells or
reports.

## Non-Goal

This notebook is a future non-official validation handoff, not authorization
for official trials.
