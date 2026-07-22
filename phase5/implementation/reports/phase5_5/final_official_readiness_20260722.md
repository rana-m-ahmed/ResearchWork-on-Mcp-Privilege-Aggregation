# Phase 5.5 Final Official Readiness

Date: 2026-07-22

## Verdict

All four model branches are GREEN for bounded official execution in the authorized Kaggle environment. This is an infrastructure launch verdict, not a prediction that every model will produce competent tool calls or a positive attack-success result.

| Slot | Exact model | Launch verdict | Scientific interpretation |
|---|---|---|---|
| M1 | `Qwen/Qwen2.5-7B-Instruct` | GREEN | Pretrial behavior was promising; official outcomes remain measured, not assumed. |
| M2 | `deepseek-ai/DeepSeek-R1-Distill-Llama-8B` | GREEN | Uses only the justified 120-second model-turn timeout override. Early-success and duplicate-call shortcuts were removed. |
| M3 | `mistralai/Mistral-7B-Instruct-v0.3` | GREEN | Hallucinated or malformed output is a valid model-competence outcome and remains analysis-eligible when infrastructure/reset evidence is valid. |
| M4 | `microsoft/Phi-3.5-mini-instruct` | GREEN | Phi-specific eager-attention/native-generation handling and semantic canary remain conditional on M4. |

## Remediations

- Aligned the agent loop, execution engine, evidence finalization, backend adapter, prompt compiler, parser, controls, and notebook builders across all four branches.
- Preserved every ordered tool call from embedded multi-call output.
- Applied tool-schema and forbidden-tool validation to every model path.
- Stopped promoting embedded/prose terminal-response JSON into a successful terminal state.
- Removed M2-only expected-plan termination, repeated-call rejection, and post-tool prompt shortcuts that could suppress source-to-sink behavior.
- Added a validated per-slot timeout map with an M2-only 120-second override; M1, M3, and M4 remain at 60 seconds.
- Propagated final, single-write attempt-manifest lifecycle handling to all branches.
- Corrected the official evidence archive manifest member name.
- Regenerated the simple, pretrial, and official notebooks and rebuilt each branch's v3 source freeze.

## Verification

- Targeted runtime/parser/notebook suite: `47 passed` on each branch.
- Full `phase5/tests` plus `phase5_5/tests`: `336 passed` on each branch (`1,344` branch-test executions total).
- Strict Gate 0: `PASS` on clean detached checkouts for M1-M4.
- Source-freeze bound-file failures: `0` for every branch.
- Shared infrastructure identity: `11/11` audited files have identical SHA-256 values across M1-M4.
- Forbidden M2 behavioral shortcut scan: `0` matches on every branch.
- Authorization: `AUTHORIZED_FOR_BOUNDED_EXECUTION`, `official_trial=true` for every slot.
- Notebook code cells compile on every branch.
- Frozen Phase 4 and Phase 4.5 artifacts were not modified.

Local official preflight fails only with `cuda-unavailable` and `official-dispatch-disabled`. This is expected: CUDA is supplied by Kaggle, and the authorized preflight overlay accepts the frozen dispatch-disable condition only after all hardware, source, branch, identity, and authorization checks pass. Official rows were not dispatched locally.

## Bound Commits

| Slot | Branch readiness head | Frozen source commit |
|---|---|---|
| M1 | `3ec12304af365a7165c890783866b7e7101eb518` | `25b69a5d44da221489d297c849b0b34b2a4d6061` |
| M2 | `7528d2a45ecc2945db70ad94ba52ea0e6960911c` | `4ab32f75a289307ca9953fe9a767d8a5a324e58d` |
| M3 | `3fd8db31c7251033887c8bde4b813e8e9e9b074e` | `c3f23a0483c45eb4bbb97764c3ccb04a219df52c` |
| M4 | `36ebcccce25fb0c4728a7fed810928b958c57523` | `b8db6079e6a10a1aedb62d21377d0d034313f792` |

The branch readiness heads may advance only by this append-only report and publication commits; each official notebook and source freeze accepts descendants while preserving the frozen source hashes.
