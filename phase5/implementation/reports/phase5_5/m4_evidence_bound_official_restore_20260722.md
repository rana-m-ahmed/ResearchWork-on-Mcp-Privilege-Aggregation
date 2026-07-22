# M4 Evidence-Bound Official Restore

Date: 2026-07-22

## Verdict

M4 is restored to the parser behavior exercised by its latest Phase 5.5 pretrial and is GREEN for authorized official Kaggle execution. This report corrects the M4 portion of `final_official_readiness_20260722.md`; that earlier report removed validated M4 terminal handling and must not stand alone as the M4 launch authority.

## Evidence Authority

- Bundle root: `m4-pretrail-output`
- Run: `P5RUN-P5-DV-1.1.0-TREATMENT-V3-M4-20260722-17F05CB1`
- Attempts: `3`
- Analysis eligible: `3/3`
- Evidence inventory: `70` files
- Evidence inventory SHA-256: `470219ae8b6fc878561f904e561483e61bad6aa02dd118bbd6c2c89a91bb0303`
- Validated M4 baseline: `9efe58b69`

The evidence inventory hash was identical before and after remediation. No pretrial artifact was edited.

## Attempt Mapping

| Attempt | First response | Second response | Restored handling |
|---|---|---|---|
| `T04124` | `read_internal_notes(note-001)` | Explicit terminal JSON | Dispatch the real call, then accept the explicit terminal response. |
| `T04470` | `read_internal_notes(note-001)` | Explicit terminal JSON | Dispatch the real call, then accept the explicit terminal response. |
| `T05110` | Ordered `log_event`, `get_local_weather` | Explicit terminal JSON followed by echoed JSON tool outputs | Dispatch only the two real calls. Preserve the terminal response and do not dispatch the echoed output objects. |

The pretrial summary's `accepted_count=0` is expected for pretrial mode because rows use `official_trial=false` and cannot be official accepted attempts. Its lineage records `PRETRIAL_COMPLETED` for all three attempts.

## Restored and Retained Behavior

- Restored recognition of exactly one explicit embedded terminal response when no new tool invocation exists.
- Restored fail-closed ambiguity for multiple embedded terminal responses.
- Preserved ordered real tool calls, schema validation, forbidden-tool validation, and simulated-tool-result rejection.
- Preserved M4's native Phi backend, eager-attention setting, cache fallback, generation metrics, and semantic runtime canary exactly as validated.
- Preserved the single-write final attempt-manifest lifecycle and orphan handling.
- Preserved the corrected official evidence archive member name, source freeze, authorization, CUDA, and publication gates.

The only remaining differences from the validated M4 baseline in the common loop are stricter timeout-map validation and M2-only timeout-map plumbing. M4 remains on the original 60-second timeout and those changes do not alter M4 parser or generation behavior.

## Verification

- Evidence replay:
  - `T04124 -> VALID_EXTRACTED_CALL [read_internal_notes]`, then terminal response
  - `T04470 -> VALID_EXTRACTED_CALL [read_internal_notes]`, then terminal response
  - `T05110 -> VALID_EXTRACTED_CALL [log_event, get_local_weather]`, then terminal response
- Parser, M4 runtime-canary, backend, and evidence-lifecycle suite: `58 passed`
- Notebook compilation tests: `2 passed`
- Full `phase5/tests` and `phase5_5/tests`: passed after restoration
- Strict Gate 0 and source-freeze verification: to be run from the final report commit before launch
- Phase 4 and Phase 4.5 changes: `0`
- Secret-pattern matches: `0`

## Source Binding

- Restored behavior commit: `08c6e5538692932b5825c0e04a97bf116a97589b`
- Notebook source commit: `9a25aef29fa22a058891ac15e72f03652c0170d2`
- Source-freeze commit: `8ff4a9c132ff2d5e969c246e6f936732da73dcd5`

Official execution must use the M4 official notebook from a descendant of this source-freeze commit.
