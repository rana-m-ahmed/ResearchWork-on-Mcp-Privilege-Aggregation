# Official Kaggle Launch Check

## Verdict

OFFICIAL KAGGLE LAUNCH PACKAGE VERDICT:
READY TO RUN M1

## Verified

- Remote annotated tag `phase5-official-source-v2` is visible.
- Remote tag dereference resolves to `c38a339327891b229bcce12d7c04a8a4e6cc63d5`.
- Dataset version `P5-DV-1.0.1-A7C91E42` is bound to the v2 source commit.
- `phase5-official-source-v1` and `P5-DV-1.0.0-A7C91E42` are superseded before official dispatch with `0` official accepted trials.
- Canonical notebook `phase5/kaggle/phase5_runner.ipynb` exposes `SOURCE_TAG_OR_COMMIT` and requires detached checkout plus `EXPECTED_SOURCE_COMMIT` verification.
- Active M4 status is `PASS`, with active run-plan status `LOAD_SUCCESS`, bound to `phase5/validation/m4_loader_status_reconciliation.json`.
- Evidence branches `phase5-model-1` through `phase5-model-4` exist remotely.
- All four initial evidence-branch heads equal `c38a339327891b229bcce12d7c04a8a4e6cc63d5`.
- Checkpoint sync allowlist excludes source and notebook paths.
- Remote divergence and credential-purge targeted tests pass.

## Launch Table

| Model slot | Exact model ID | Official source tag | Evidence branch | Dataset version | First pending batch | Total pending batches | Planned session capacity | Checkpoint threshold | Accelerator | Required secrets | Notebook parameter values | Resume source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `M1` | `Qwen/Qwen2.5-7B-Instruct` | `phase5-official-source-v2` | `phase5-model-1` | `P5-DV-1.0.1-A7C91E42` | `1` | `51` | `51` batches | `6` trials | Kaggle GPU | Git read if private, Git write after seal closure, HF token if required | `SOURCE_TAG_OR_COMMIT=phase5-official-source-v2`, `EXPECTED_SOURCE_COMMIT=c38a339327891b229bcce12d7c04a8a4e6cc63d5`, `MODEL_SLOT=M1`, `EVIDENCE_BRANCH=phase5-model-1` | `kaggle_run_plan_v2.json`, `batch_partition_manifest_v2.json`, lineage |
| `M2` | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `phase5-official-source-v2` | `phase5-model-2` | `P5-DV-1.0.1-A7C91E42` | `1` | `51` | `51` batches | `6` trials | Kaggle GPU | Git read if private, Git write after seal closure, HF token if required | `SOURCE_TAG_OR_COMMIT=phase5-official-source-v2`, `EXPECTED_SOURCE_COMMIT=c38a339327891b229bcce12d7c04a8a4e6cc63d5`, `MODEL_SLOT=M2`, `EVIDENCE_BRANCH=phase5-model-2` | `kaggle_run_plan_v2.json`, `batch_partition_manifest_v2.json`, lineage |
| `M3` | `mistralai/Mistral-7B-Instruct-v0.3` | `phase5-official-source-v2` | `phase5-model-3` | `P5-DV-1.0.1-A7C91E42` | `1` | `51` | `51` batches | `6` trials | Kaggle GPU | Git read if private, Git write after seal closure, HF token if required | `SOURCE_TAG_OR_COMMIT=phase5-official-source-v2`, `EXPECTED_SOURCE_COMMIT=c38a339327891b229bcce12d7c04a8a4e6cc63d5`, `MODEL_SLOT=M3`, `EVIDENCE_BRANCH=phase5-model-3` | `kaggle_run_plan_v2.json`, `batch_partition_manifest_v2.json`, lineage |
| `M4` | `microsoft/Phi-3.5-mini-instruct` | `phase5-official-source-v2` | `phase5-model-4` | `P5-DV-1.0.1-A7C91E42` | `1` | `51` | `51` batches | `6` trials | Kaggle GPU | Git read if private, Git write after seal closure, HF token if required | `SOURCE_TAG_OR_COMMIT=phase5-official-source-v2`, `EXPECTED_SOURCE_COMMIT=c38a339327891b229bcce12d7c04a8a4e6cc63d5`, `MODEL_SLOT=M4`, `EVIDENCE_BRANCH=phase5-model-4` | `kaggle_run_plan_v2.json`, `batch_partition_manifest_v2.json`, lineage |

## Exact Resume Command Sequence

```text
python -m phase5 gate0 --strict --root /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --report-dir phase5/validation
python -m phase5 checkpoint-status --model-slot <MODEL_SLOT> --run-plan phase5/validation/kaggle_run_plan_v2.json --batch-manifest phase5/manifests/batch_partition_manifest_v2.json
python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 1 --output phase5/validation/p15_handoff_report.json
python -m phase5 run-campaign --model-slot <MODEL_SLOT> --run-id <RUN_ID> --utcdate <YYYYMMDD> --until-safety-horizon --batch-manifest phase5/manifests/batch_partition_manifest_v2.json --run-plan phase5/validation/kaggle_run_plan_v2.json --output phase5/validation/p15_handoff_report.json
python -m phase5 session-close-seal --run-id <RUN_ID> --output phase5/validation/p15_handoff_report.json
python -m phase5 sync-github --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --manifest <SYNC_MANIFEST_PATH> --allowlist phase5/configs/sync_allowlist.yaml --receipt <SYNC_RECEIPT_PATH>
python -m phase5 session-reverify --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --receipt <SYNC_RECEIPT_PATH> --output phase5/validation/p15_handoff_report.json
```

## Remaining Blockers

None.
