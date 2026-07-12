# M1 Shared-Engine Kaggle Proof Remediation

## Scope

This change replaces the prior one-batch campaign proof with a dedicated, bounded, non-official M1 proof command. It does not execute official trials and does not modify Phase 4 or Phase 4.5.

## Corrected failures

- Reconciled the proof dataset authority to `P5-DV-1.0.1-A7C91E42` and removed the executable campaign fallback to `1.0.2`.
- Added two hash-bound synthetic fixtures: a non-tool terminal path and one genuine FastMCP tool call followed by model-driven continuation.
- Aligned parsing with the frozen single-call prompt contract while rejecting mixed or multiple-call forms under the frozen policy.
- Routed tool execution through the validated FastMCP server and captured discovery plus request/response evidence.
- Added model input/generated token IDs and decoded output receipts.
- Made immutable model preparation explicit before dispatch, validated required CUDA placement, and captured the final Hugging Face device map.
- Replaced grader and TID placeholders with the frozen grader and logical-ID TID implementations.
- Completed required event ordering through reset, grading, materialization, and finalization.
- Added a controlled `DISPATCHED`-without-`FINALIZED` orphan, recovery planning, replacement linkage, and append-oriented lineage.
- Isolated proof evidence under `phase5/proof_runs/<run-token>` and retained all non-official flags and zero official counters.
- Rewired the notebook to invoke `python -m phase5 run-m1-proof`; it no longer selects or dispatches campaign queue rows.
- Prevented notebook evidence synchronization to `main` and required any configured evidence branch to exist remotely.

## Validation boundary

Local tests validate orchestration, contracts, failures, notebook syntax, genuine FastMCP dispatch, and evidence requirements. The immutable M1 weight load and real `model.generate()` remain intentionally executable only in the Kaggle dual-T4 environment.

Verification completed with `compileall` passing and all 246 Phase 5 tests passing.

## Kaggle follow-up

The first bounded proof run finalized the terminal replacement but stopped at S5 for the tool fixture. Root cause was the prompt renderer checking substituted output for any `}}` sequence, which incorrectly classified the closing braces in the fixture's nested JSON tool call as an unresolved template placeholder. Placeholder authority is now validated against the template before substitution, preserving literal JSON values while still rejecting missing template placeholders. The nested-JSON regression is covered directly; the complete suite now passes 247 tests.

A subsequent Kaggle run reached generation but triggered the frozen malformed-output policy. Synthetic fixture wording now requires the complete response to be exactly the governed JSON object, without Markdown or surrounding text. Failures now identify the attempt, termination state, and safe parser classification directly; the notebook also writes `m1_proof_failure_diagnostics.json` and packages partial evidence before terminating, so Kaggle Save Version teardown cannot erase the only diagnostic record.
