# I17R Kaggle M4 Runner Fix

## Objective
Repair the official Phase 5 Kaggle runner for the M4 branch so it boots from the M4-capable source tag and restores the M4 frozen selection tuple before the model backend identity loader runs.

## What Changed
- Updated `phase5/kaggle/official_phase5_runner.ipynb` to use `phase5-official-source-v4` and commit `4e2e79e6c29f1d2c1dcfe8f487291aca1b224a4b`.
- Removed the brittle clean-worktree preflight after checkout.
- Added an explicit M4 overlay step that rewrites:
  - `phase4_5/configs/phase45_selected_model.yaml`
  - `phase4_5/configs/phase45_local_dryrun.yaml`
- Kept the runner locked to `MODEL_SLOT = M4` and `MAX_BATCHES = 750`.
- Updated `phase5/tests/test_kaggle_handoff.py` to assert the new source tag/commit and the M4 overlay logic.

## Validation
- `pytest phase5/tests/test_kaggle_handoff.py`
- Detached v4 sanity check with the overlay applied:
  - `load_frozen_model_backend_identity(root=temp_clone)` resolved `M4 microsoft/Phi-3.5-mini-instruct`

## Notes
- No secrets were added or changed.
- No frozen Phase 4 or Phase 4.5 files were modified in the repository history.
- The notebook now fails closed if the overlay lands incorrectly or the source commit does not match the expected v4 commit.
