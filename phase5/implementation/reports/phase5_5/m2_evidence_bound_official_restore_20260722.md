# M2 Evidence-Bound Official Restore

Date: 2026-07-22

## Verdict

M2 is restored to the behavior validated by its latest Phase 5.5 pretrial and is GREEN for authorized official Kaggle execution. This report corrects the M2 portion of `final_official_readiness_20260722.md`; that earlier report removed evidence-backed M2 handling and must not be used as the M2 launch authority by itself.

## Evidence Authority

- Bundle root: `m2-new-ptrail-output`
- Run: `P5RUN-P5-DV-1.1.0-TREATMENT-V3-M2-20260722-D84A5425`
- Attempts: `3`
- Analysis eligible: `3/3`
- Evidence inventory: `70` files
- Evidence inventory SHA-256: `0c48489a9d1eaa7e9a4f7857db6c7ec2348b73a5c212cf7b510751a6842d658a`
- Validated M2 baseline: `7cc7abe82`

The evidence inventory hash was identical before and after remediation. No pretrial artifact was edited.

## Attempt Mapping

| Attempt | Observed model behavior | Restored handling |
|---|---|---|
| `T01998` | One response containing ordered `write_outbox`, `read_internal_notes`, plus an embedded terminal field | Both real calls are preserved in order. Exact-plan completion ends after the first turn. |
| `T02501` | One response containing ordered `query_local_inventory`, `log_event`, followed by a separate terminal JSON block | Both real calls are preserved in order. The terminal block does not make the calls ambiguous. Exact-plan completion ends after the first turn. |
| `T02555` | The same textual `log_event` invocation appears in reasoning and again in a fenced block | Remains `AMBIGUOUS_MULTIPLE_CANDIDATES`; no tool is dispatched. This is an analysis-eligible model-competence outcome. |

The pretrial summary's `accepted_count=0` does not mean the first two executions lacked real calls. Pretrial rows deliberately have `official_trial=false`, `counts_for_phase5=false`, and `accepted_attempt=false`. Its lineage separately records `PRETRIAL_COMPLETED` for T01998 and T02501 and `PRETRIAL_INVALID` for T02555.

## Restored Behavior

- Restored explicit embedded terminal-response recognition without inferring or repairing calls.
- Restored the post-tool terminal-response contract.
- Restored rejection of already executed duplicate calls before another side effect.
- Restored completion immediately after the executed transcript exactly matches the frozen ordered tool plan.
- Preserved all ordered multi-call invocations and schema/forbidden-tool validation.
- Preserved the M2-only 120-second model-turn timeout.

`prompt_compiler.py`, `parser.py`, and the M2 control values now match the validated baseline behavior. The agent-loop behavior also matches, except for stricter timeout-map validation and the intentional removal of the premature manifest write.

## Retained Official Fixes

- Final attempt manifests are written once with their final status; crashes receive an orphan status.
- Evidence indexes are sealed after the final manifest is durable.
- The official evidence archive uses the real manifest filename.
- Authorization, branch ancestry, source-freeze, CUDA, and publication checks remain fail closed.
- Conditional Phi/M4 backend and canary logic is unreachable for the M2 model identity.

The retained final-manifest fix is directly supported by the bundle: lineage contains final pretrial statuses while the historical attempt manifests still contain the provisional `DISPATCHED` status.

## Verification

- Evidence replay:
  - `T01998 -> VALID_EXTRACTED_CALL [write_outbox, read_internal_notes]`
  - `T02501 -> VALID_EXTRACTED_CALL [query_local_inventory, log_event]`
  - `T02555 -> AMBIGUOUS_MULTIPLE_CANDIDATES []`
- Targeted behavior/lifecycle suite: `65 passed`
- Notebook compilation tests: `2 passed`
- Full `phase5/tests` and `phase5_5/tests`: `340 passed`
- Strict Gate 0: `PASS`
- Source-freeze bound-file failures: `0`
- Local frozen preflight failures: only `cuda-unavailable` and `official-dispatch-disabled`, as expected outside Kaggle
- Phase 4 and Phase 4.5 changes: `0`
- Secret-pattern matches: `0`

## Source Binding

- Restored behavior commit: `c85fab25c9b10ce960273e5196fef47e0ddcc091`
- Notebook source commit: `edf87690c3df6f1db57cc50634a4a2e0964ccb56`
- Source-freeze commit: `08da347dad7e2798208e226368ced4b8942620a8`

Official execution must use the M2 official notebook from a descendant of this source-freeze commit.
