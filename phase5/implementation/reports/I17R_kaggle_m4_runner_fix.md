# I17R Kaggle M4 Runner Fix

## Objective
Repair the official Phase 5 Kaggle runner for the M4 branch so it boots from the M4-capable source tag and restores the M4 frozen selection tuple before the model backend identity loader runs.

## What Changed
- Updated `phase5/kaggle/official_phase5_runner.ipynb` to use `phase5-official-source-v4` and commit `4e2e79e6c29f1d2c1dcfe8f487291aca1b224a4b`.
- Updated the M4 runner again to use `phase5-official-source-v5` and commit `0274eec1e349d0e0c459fd2a88785332ac0a3c50` after the Phi cache compatibility fix.
- Updated the M4 runner again to use `phase5-official-source-v6` and commit `9224241688579abbe059aa01cdc636d64d45c2de` after the Phi `get_usable_length` compatibility fix.
- Removed the brittle clean-worktree preflight after checkout.
- Added an explicit M4 overlay step that rewrites:
  - `phase4_5/configs/phase45_selected_model.yaml`
  - `phase4_5/configs/phase45_local_dryrun.yaml`
- Moved strict Gate 0 execution before the M4 overlay, while the detached source checkout is still clean.
- Changed the later `strict_gate0` notebook cell into a status-only cell so it cannot fail on the intentional overlay dirtiness.
- Reworked GitHub evidence sync to clone `phase5-model-4` into a separate clean push repository, copy only changed evidence/validation/checkpoint outputs, and push from that branch clone.
- Pinned notebook campaign commands to `phase5/manifests/batch_partition_manifest_v3.json` and `phase5/validation/kaggle_run_plan_v3.json` instead of relying on older CLI defaults.
- Added the required `--until-safety-horizon` flag to the official `run-campaign` invocation.
- Extended the Phi-3.5 DynamicCache compatibility shim to provide the legacy `from_legacy_cache` method expected by the frozen remote model code under `transformers==5.0.0`.
- Extended the same shim to provide the legacy `get_usable_length` method expected by the frozen Phi-3.5 prefill path.
- Forced the Phi-3.5 runtime path to use eager attention and disable KV cache at model-load and generation time, avoiding flash-attention probing and further `DynamicCache` drift during official execution.
- Kept the runner locked to `MODEL_SLOT = M4` and `MAX_BATCHES = 750`.
- Updated `phase5/tests/test_kaggle_handoff.py` to assert the new source tag/commit and the M4 overlay logic.

## Validation
- `pytest phase5/tests/test_kaggle_handoff.py`
- Detached v4 sanity check with the overlay applied:
  - `load_frozen_model_backend_identity(root=temp_clone)` resolved `M4 microsoft/Phi-3.5-mini-instruct`
- Notebook startup dry-run:
  - detached `phase5-official-source-v4`
  - clean-tree precheck
  - `phase5 gate0 --strict`
  - M4 overlay
  - frozen identity resolved as `M4 microsoft/Phi-3.5-mini-instruct`
- Static notebook regression now asserts the v3 manifest/run-plan paths and `--until-safety-horizon` are present in the official campaign call.
- Runtime adapter regression now verifies the Phi-3.5 DynamicCache shim installs `from_legacy_cache` when the current `transformers` cache class does not provide it.
- Runtime adapter regression also verifies the shim installs `get_usable_length` with max-length bounding semantics.
- Runtime adapter regression verifies Phi-specific load/generation kwargs force eager attention and no-cache execution without changing non-Phi model kwargs.

## Notes
- No secrets were added or changed.
- No frozen Phase 4 or Phase 4.5 files were modified in the repository history.
- The notebook now fails closed if the overlay lands incorrectly or the source commit does not match the expected v4 commit.
- The final GitHub push no longer commits from the detached source checkout, avoiding non-fast-forward evidence pushes caused by source-tag ancestry.
- The notebook no longer lets v2 CLI defaults select a `P5-DV-1.0.1` resume batch during a `P5-DV-1.0.2` M4 run.
- The M4 source tag must point at a source commit containing the cache shim; otherwise the notebook will still check out the older v4 adapter and crash in generation.
