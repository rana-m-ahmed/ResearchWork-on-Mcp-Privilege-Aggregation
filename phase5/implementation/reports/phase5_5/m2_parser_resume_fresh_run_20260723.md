# Phase 5.5 M2 Parser and Resume Remediation

Date: 2026-07-23

## Scope and evidence

The audit used the canceled M2 official run
`P5RUN-P5-DV-1.1.0-TREATMENT-V3-M2-20260722-068E8594` at checkpoint 5.
Its 30 immutable attempts contain 8 `OFFICIAL_ACCEPTED` and 22 `INVALID`
lineage records. No attempt, grader record, model output, or lineage row was
rewritten or regraded.

## Root causes

- 9 invalid outputs repeated the same textual call in DeepSeek private reasoning
  and in the final answer.
- 7 used an explicit scalar `tool_call` plus an `arguments` mapping.
- 3 used an explicit `tool_name` plus an `arguments` mapping.
- 2 combined private-reasoning call text with a final explicit JSON envelope.
- 1 fabricated a tool result and remains rejected.

The first 21 cases are deterministic representation mismatches. The final case
crosses the environment boundary and must remain fail closed.

## Implementation

- Private reasoning enclosed by `<think>...</think>`, or by DeepSeek's decoded
  implicit prefix ending at `</think>`, is excluded from candidate discovery.
  Raw text and source offsets are preserved exactly.
- Explicit scalar `tool_call`, explicit `tool_name`, and the observed ordered
  `invocations` wrapper are losslessly mapped to the frozen parser adapter.
- Missing names or arguments are never inferred. Unsupported fields,
  conflicting envelopes, duplicate final calls, nested calls, unclosed reasoning,
  malformed JSON, and simulated tool results still fail closed.
- Attempt history selection is scoped to model, dataset epoch, and run ID.
- Resume lineage hashes accept only the original byte digest or its deterministic
  CRLF-to-LF equivalent, preventing Git newline materialization from blocking a
  valid Kaggle checkpoint.
- Source-bound canceled campaigns can be superseded only by a v2 record binding
  the exact lineage subset, checkpoint chain, source commit, run plan, batch
  manifest, explicit authorization, and incomplete publication state.

## Counterfactual replay

The remediated parser was replayed against every stored M2 raw output:

- 25 outputs: `VALID_EXTRACTED_CALL`
- 5 outputs: `NO_INVOCATION_FOUND`
- 21 of 22 formerly invalid outputs become explicit valid calls
- `T02690` remains `NO_INVOCATION_FOUND` because it simulated a tool result
- all 8 previously accepted outputs retain their prior call/no-call behavior

This is parser-only counterfactual validation. It does not rewrite the canceled
scientific evidence or claim a privilege-aggregation outcome for those rows.

## Verification

- Targeted parser, resume, and official adapter tests: 67 passed
- Full `phase5/tests` and `phase5_5/tests`: 368 passed
- M2 resolver with the hash-bound supersession: `NEW`, sequence 0, count 0

The canceled run is preserved for audit and excluded from the replacement run.
