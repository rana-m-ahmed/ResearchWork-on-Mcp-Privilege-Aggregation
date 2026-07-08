# P15 Operator Runbook

This runbook is for a future Kaggle validation operator. It is not an
authorization to run official trials from this task.

## Preconditions

- Verify the repository is on the intended evidence branch.
- Confirm the notebook parameters only edit the branch fields and approved
  operational limits.
- Confirm the notebook imports `phase5.kaggle.handoff` only.
- Confirm no secret value is present in the notebook or reports.

## Stage Order

1. Environment identity.
2. Clone and checkout.
3. Preparation and Gate 0.
4. Campaign plan.
5. Canary command placeholder.
6. Open and seal the first epoch.
7. Unified campaign.
8. Optional sync barrier.
9. Final closure and sync.
10. Report.

## Operational Rules

- One model campaign is the target per Kaggle session.
- The actual campaign count comes from the frozen P05 run planning output.
- Do not duplicate queue logic, parser logic, prompt logic, or scientific
  logic in notebook cells.
- Do not bypass Gate 0, seal, finalization, sync, re-verification, or reseal.
- After sync, stop and reverify before any reseal or continuation.

## Sync Barrier Sequence

When the predeclared sync barrier is reached:

1. close the active seal;
2. run `sync-github`;
3. run `session-reverify`;
4. run `session-seal` only after re-verification succeeds;
5. continue only if the session remains valid.

If re-verification fails, the session must stop.

## Outputs

The notebook should only point to the public CLI and generated reports. It must
not embed Kaggle trial output or scientific conclusions.
