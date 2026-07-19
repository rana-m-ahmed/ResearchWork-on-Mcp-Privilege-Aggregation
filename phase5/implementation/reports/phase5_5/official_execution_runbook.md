# Phase 5.5 Execution Runbook

## Select the Branch

Use only the branch matching the model slot:

| Slot | Branch | Official notebook |
|---|---|---|
| M1 | `phase5_5-model-1` | `phase5_5/kaggle/phase5_5_official_runner.ipynb` |
| M2 | `phase5_5-model-2` | `phase5_5/kaggle/phase5_5_official_runner.ipynb` |
| M3 | `phase5_5-model-3` | `phase5_5/kaggle/phase5_5_official_runner.ipynb` |
| M4 | `phase5_5-model-4` | `phase5_5/kaggle/phase5_5_official_runner.ipynb` |

Do not use an older downloaded notebook or a notebook from another slot.

## Pretrial

Run `phase5_5/kaggle/phase5_5_pretrial_runner.ipynb` first. It requires only
the Kaggle secret `HF_TOKEN`. It executes three complete real-backend trials
with isolated non-official attempt and evidence roots.

The pretrial is successful only when its report, three attempt records, hashed
manifest, and evidence archive are present. `resume_required: true` is
expected because this bounded run does not finish the official queue. Pretrial
artifacts are diagnostic only and must never be counted as accepted evidence.

## Official Run

The official notebook requires these Kaggle secrets, stored as secrets rather
than notebook literals:

- `HF_TOKEN`
- `PHASE5_GITHUB_TOKEN` with write access to the selected branch

The notebook performs Gate 0 and publication preflight before dispatch. It
publishes a checkpoint after every six completed trials and at batch tail. It
also emits model-cache and heartbeat logs before and during dispatch.

## Interruption and Resume

If Kaggle stops, do not delete the checkout, branch evidence, or checkpoint
receipts. Relaunch the same slot's official notebook from the latest branch.
The adapter reads published lineage and skips completed targets, so accepted,
invalid, and orphaned targets are not duplicated. At most the work since the
last successful checkpoint publication can require re-execution.

Do not interpret an unpushed local attempt as durable official evidence. A
checkpoint receipt and its remote branch update are the durability boundary.

## Completion

Official completion requires a successful final publication receipt, remote
head reconciliation, intact evidence hashes, and a sealed branch report. Do
not merge findings into `main` until all four branches pass the cross-model
audit.
