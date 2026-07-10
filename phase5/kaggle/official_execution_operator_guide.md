# Official Kaggle Execution Operator Guide

This guide is the final I17R operator package for official Phase 5 Kaggle execution. It does not authorize local official trials, protocol edits, queue edits, model changes, prompt changes, parser changes, grader changes, trial-count changes, or batch-order changes.

## Final Authority

- Official source tag: `phase5-official-source-v2`
- Official source commit: `c38a339327891b229bcce12d7c04a8a4e6cc63d5`
- Official tag object: `38fab6c096f0de72a649eabd2f3c460ba8221ca7`
- Dataset version: `P5-DV-1.0.1-A7C91E42`
- Superseded before official dispatch: `phase5-official-source-v1`, `P5-DV-1.0.0-A7C91E42`
- Official accepted trials before supersession: `0`
- Canonical notebook: `phase5/kaggle/phase5_runner.ipynb`
- Operator runbook: `phase5/kaggle/operator_runbook.md`
- Active run plan: `phase5/validation/kaggle_run_plan_v2.json`
- Active batch manifest: `phase5/manifests/batch_partition_manifest_v2.json`
- Unified CLI surface: `python -m phase5`

## Model Campaigns

| Model slot | Exact model ID | Evidence branch | Initial remote head | First pending batch | Batch count | Checkpoint threshold |
| --- | --- | --- | --- | --- | --- | --- |
| `M1` | `Qwen/Qwen2.5-7B-Instruct` | `phase5-model-1` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` | `1` | `51` | `6` trials |
| `M2` | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `phase5-model-2` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` | `1` | `51` | `6` trials |
| `M3` | `mistralai/Mistral-7B-Instruct-v0.3` | `phase5-model-3` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` | `1` | `51` | `6` trials |
| `M4` | `microsoft/Phi-3.5-mini-instruct` | `phase5-model-4` | `c38a339327891b229bcce12d7c04a8a4e6cc63d5` | `1` | `51` | `6` trials |

Operational granularity remains: one canonical notebook, one model slot per campaign, preferred one long Kaggle session per model, many contiguous finalized batches per session, and extra sessions only when the safety horizon requires them. A Kaggle session is not one small batch, and all four models are not one inseparable session.

## Kaggle Steps

1. Open/import `phase5/kaggle/phase5_runner.ipynb`.
2. Select the approved Kaggle GPU accelerator.
3. Enable Internet only for clone, preparation, dependency/model access if required, and GitHub sync.
4. Attach required Kaggle Secrets without printing values.
5. Set `SOURCE_TAG_OR_COMMIT = "phase5-official-source-v2"`.
6. Set `EXPECTED_SOURCE_COMMIT = "c38a339327891b229bcce12d7c04a8a4e6cc63d5"`.
7. Select one model slot and its evidence branch from the table above.
8. Clone, fetch tags, checkout detached `SOURCE_TAG_OR_COMMIT`, and verify `git rev-parse HEAD` equals `EXPECTED_SOURCE_COMMIT`.
9. Run Gate 0: `python -m phase5 gate0 --strict --root /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --report-dir phase5/validation`.
10. Review only operational preflight results.
11. Run the non-official startup canary placeholder; do not count it as an official trial.
12. Confirm `phase5/validation/kaggle_run_plan_v2.json` and `phase5/manifests/batch_partition_manifest_v2.json`.
13. Open and seal the official session: `python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 1 --output phase5/validation/p15_handoff_report.json`.
14. Start the unified campaign: `python -m phase5 run-campaign --model-slot <MODEL_SLOT> --run-id <RUN_ID> --utcdate <YYYYMMDD> --until-safety-horizon --batch-manifest phase5/manifests/batch_partition_manifest_v2.json --run-plan phase5/validation/kaggle_run_plan_v2.json --output phase5/validation/p15_handoff_report.json`.
15. Allow finalized checkpoints at the configured barrier.
16. Stop before the safety horizon instead of relying on Kaggle forced termination.
17. Confirm final synchronization and remote SHA verification.
18. Save the executed notebook and Kaggle output version.
19. Start another session only if pending batches remain.
20. Repeat for the next model after the current model campaign is complete or safely checkpointed.

## Secrets

| Secret label | Purpose | Retrieval window | Minimum permission | Purge point |
| --- | --- | --- | --- | --- |
| `GITHUB_READ_TOKEN_PHASE5` | Clone/checkout if the repository is private | Preparation only | Repository read | Before sealed execution |
| `GITHUB_WRITE_TOKEN_PHASE5` | Push allowlisted finalized evidence | After seal closure only | Write access restricted to the repository and evidence branches | Immediately after sync before reverify/reseal |
| HF/model-access token if required | Download gated model assets during preparation | Preparation only | Read access to required model assets | Before sealed official execution |

Do not print secret values. Do not store tokens permanently in `.git/config`. Do not pass Git write credentials to trial-facing subprocesses.

## Resume Procedure

For a fresh Kaggle session: clone the correct evidence branch, fetch and checkout detached `phase5-official-source-v2`, verify `HEAD == c38a339327891b229bcce12d7c04a8a4e6cc63d5`, verify the expected remote checkpoint head, run Gate 0, load manifests and lineage, identify finalized accepted rows and preserved orphans, calculate the next contiguous pending batches, avoid duplicate accepted trials, and continue under a new run ID and seal epoch.

## Safety

- Source paths cannot be staged by checkpoint synchronization.
- Only allowlisted evidence/checkpoint/manifest/report paths may be staged.
- Force push, automatic pull, automatic merge, and automatic rebase are prohibited.
- Unexpected remote divergence aborts.
- Remote SHA verification is required after every checkpoint push.
- M4 active status is `PASS` and bound to `phase5/validation/m4_loader_status_reconciliation.json`.

## Emergency Procedure

For kernel interruption, GPU reset, disk pressure, push failure, remote divergence, hash mismatch, reset failure, model OOM, or Kaggle session termination: stop official execution, preserve the working directory and Kaggle output version, do not delete attempts, do not manually edit final trial rows, close the seal if possible, archive finalized local evidence, validate hashes, sync only allowlisted finalized evidence when safe, and fail closed on any mismatch or unexpected remote head.
