# Phase 4.5 Hybrid Dry-Run Scaffold

Phase 4.5 is a non-official bridge between the Phase 4 freeze and any later Phase 5 work.
It exists to validate the repository shape, the local preflight, and the Kaggle smoke path
without turning the dry run into an official adversarial evaluation.

## Purpose

- Verify that the Phase 4 freeze artifacts are intact.
- Prepare a local GitHub-controlled dry-run scaffold.
- Prepare a Kaggle execution substrate for model-heavy smoke checks.
- Keep every Phase 4.5 output clearly non-official and non-counting.

## Local GitHub Responsibilities

- Keep GitHub as the source of truth.
- Run the Phase 4 freeze preflight.
- Record hashes, reports, and run manifests.
- Keep the scaffold free of model weights, credentials, `.env` files, and absolute local paths.
- Return Kaggle outputs back into the repository after each smoke run.

## Kaggle Responsibilities

- Host the model-heavy smoke execution.
- Use the notebook and Python runner in `phase4_5/kaggle/`.
- Produce only smoke evidence, not official trial evidence.
- Return outputs to GitHub for review and archiving.

## Strict Boundary

- No official Phase 5 trials.
- No ASR computation.
- No exploit-rate claims.
- No defense-effectiveness claims.
- No vulnerability claims.
- No `official_trial: true`.
- No `counts_for_phase5: true`.

## Required Execution Order

1. Confirm the Phase 4 freeze artifacts.
2. Run `phase4_5/scripts/verify_phase45_preflight.py`.
3. Review the generated preflight report.
4. Prepare the Kaggle smoke run.
5. Run the Kaggle notebook and Python runner.
6. Return the Kaggle outputs to GitHub.
7. Keep the dry-run status separate from any later Phase 5 work.

## What Counts As Evidence

- SHA256 hashes of the frozen Phase 4 files.
- The branch-start report.
- The preflight report.
- Kaggle smoke outputs returned to GitHub.
- Run manifests and validation notes.

## What Must Not Be Committed

- Model weights.
- Caches.
- `.env` files.
- Credentials.
- Local absolute paths.
- Official trial rows.
- `official_trial: true`.
- `counts_for_phase5: true`.

## How To Run Preflight

```powershell
python phase4_5/scripts/verify_phase45_preflight.py
```

If the environment uses `python3`, use that instead.

## Current Readiness Status

`READY_FOR_EXTERNAL_AUDIT` / `PHASE_4.5_COMPLETE`

Reason: Authentic Kaggle GPU timing metrics have successfully been ingested, analyzed, and approved by the strict independent auditor. The repository is authorized to branch to Phase 5.
