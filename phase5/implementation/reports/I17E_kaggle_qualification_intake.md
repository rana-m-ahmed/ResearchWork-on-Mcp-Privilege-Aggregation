# I17E Kaggle Qualification Intake

- Intake status: `ACCEPTED_AS_NON_OFFICIAL_SYNTHETIC_QUALIFICATION_ARTIFACT`
- Candidate commit: `43337406c04ee0b7fefbcc527bf29056725fc72a`
- Qualification ID: `P5-NONOFFICIAL-I17E-QUALIFICATION`
- Evidence branch: `phase5-kaggle-nonofficial-adapter-qualification`
- Artifact folder: `phase5_i17e_kaggle_qualification_bundle/`
- Official trial: `false`
- Counts for Phase 5: `false`
- Publication evidence: `false`
- Synthetic fixture: `true`

## Runtime Evidence

- Platform: `Linux-6.12.90+-x86_64-with-glibc2.35`
- Python: `3.12.13`
- GPU: `2 x Tesla T4`
- CUDA reported by `nvidia-smi`: `13.0`
- PyTorch: `2.10.0+cu128`
- PyTorch CUDA: `12.8`
- Transformers: `5.0.0`
- bitsandbytes: `not installed`

## Model Slots

| Slot | Exact model ID | Tokenizer | Backend | Status |
| --- | --- | --- | --- | --- |
| M1 | `Qwen/Qwen2.5-7B-Instruct` | `Qwen/Qwen2.5-7B-Instruct` | `real` | `passed` |
| M2 | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | `real` | `passed` |
| M3 | `mistralai/Mistral-7B-Instruct-v0.3` | `mistralai/Mistral-7B-Instruct-v0.3` | `real` | `passed` |
| M4 | `microsoft/Phi-3.5-mini-instruct` | `microsoft/Phi-3.5-mini-instruct` | `real` | `passed` |

## Durability And Sync

- PREPARED/DISPATCHED durability: `recorded`
- Interrupt after DISPATCHED: `preserved_orphan`
- Replacement attempt: `P5-NONOFFICIAL-I17E-QUALIFICATION-M1-SYNTHETIC-ATTEMPT-REPLACEMENT`
- Accepted target uniqueness: `passed`
- Checkpoint resume next pending: `passed`
- Close seal: `passed`
- Stop model and FastMCP: `passed`
- Credential purge: `passed`
- Remote SHA verification: `pending on Kaggle push`

## Residual Caveats

- The artifacts remain non-official and must not enter official Phase 5 accepted evidence.
- `revision_digest` is `unspecified` for all four model slots.
- `bitsandbytes` import failed in the Kaggle runtime.
- `generation_evidence` records a successful Torch backend import check, not a full decoded model response transcript.
