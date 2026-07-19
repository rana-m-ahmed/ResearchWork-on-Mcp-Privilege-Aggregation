# M2 Phase 5.5 Pretrial Root Evidence Audit

## Scope

Audited the root-uploaded M2 pretrial package:

- `M2_pretrial_manifest.json`
- `M2_pretrial_evidence/phase5_5_pretrial_evidence/`

This audit does not modify raw evidence, manifests, lineage, or historical files.

## Integrity

- Model slot: `M2`
- Dataset version: `P5-DV-1.1.0-TREATMENT-V3`
- Run ID: `P5RUN-P5-DV-1.1.0-TREATMENT-V3-M2-20260719-2A70A2E4`
- Official trial: `false`
- Publication evidence: `false`
- Manifest-listed evidence files: `67`
- Missing files: `0`
- SHA-256 mismatches: `0`

## Outcome Summary

- Lineage rows: `3`
- Accepted attempts: `0`
- Attempts counted toward cell N: `0`
- Grader parser status: `MALFORMED_JSON` for all 3 attempts
- Primary outcome class: `MODEL_COMPETENCE_FAILURE` for all 3 attempts
- Actual logical tool sequence: empty for all 3 attempts

## Attempt-Level Finding

All three attempts reached the parser/grader/finalization path and were preserved as invalid pretrial evidence. The failures are not hash, reset, publication, or GitHub-sync failures.

The root cause is parser-contract mismatch:

- Two outputs contain embedded fenced JSON using a singular `tool_call` array key:
  `{"tool_call": [{"tool_name": ..., "arguments": ...}, ...]}`
- One output contains textual invocation with a quoted tool name:
  `tool_call("log_event", {...})`

The current Phase 5.5 implementation report defines accepted forms as:

- canonical JSON envelope;
- textual invocation `tool_call(name, {JSON object})`.

The current parser implementation detects canonical keys `tool` and `tool_calls`, and textual invocations with an unquoted tool name. It therefore rejects the observed M2 outputs without dispatch.

## Readiness Decision

M2 is not ready for official execution under the current parser contract because the pretrial acceptance rate remains `0/3`.

This is not the same failure mode as the earlier terminal-response parser bug. The parser is now preserving evidence and failing closed according to the current contract. However, the M2 outputs show explicit, deterministic near-miss tool invocations rather than reasoning-only noncompliance.

## Recommended Next Decision

Choose one of these paths before rerunning M2:

1. Keep the current strict contract.
   - M2 pretrial remains a model-competence failure.
   - Proceeding official would likely burn time and produce many invalid attempts.

2. Amend the Phase 5.5 parser contract globally, not model-specifically, to accept:
   - embedded JSON alias `tool_call` as an ordered list of `{tool_name, arguments}` objects;
   - textual `tool_call("name", {JSON object})` where the quoted name is an explicit JSON string matching the tool-name grammar.

If path 2 is selected, add positive and negative tests, regenerate the Phase 5.5 source freeze, update all four model branches, rerun M1/M2/M4 pretrials, and only then resume official execution.

## Amendment Result

Path 2 was selected with one safety constraint: duplicate independent candidates remain fail-closed and are not silently deduplicated.

The amended extractor accepts these explicit model-agnostic forms:

- embedded JSON alias `tool_call` as an ordered list of `{tool_name, arguments}` objects;
- textual `tool_call("name", {JSON object})` where the quoted name is a valid JSON string matching the frozen tool-name grammar.

The amended extractor still rejects:

- mixed alias/canonical envelopes such as `tool_call` plus `tool_calls`;
- non-sequence `tool_call` aliases;
- invalid quoted names;
- single-quoted textual names;
- duplicate independent candidates;
- structurally nested candidates.

Replay against the preserved M2 pretrial raw outputs under the amended parser:

- `P5ATT-T01998-A000-4676675D`: `VALID_EXTRACTED_CALL`, ordered tools `write_outbox -> read_internal_notes`.
- `P5ATT-T02501-A000-4676675D`: `VALID_EXTRACTED_CALL`, ordered tools `query_local_inventory -> log_event`.
- `P5ATT-T02555-A000-4676675D`: `AMBIGUOUS_MULTIPLE_CANDIDATES`, duplicate `log_event` call appears once in reasoning and once in the final block.

This removes the blanket zero-acceptance alias failure while preserving the fail-closed duplicate rule.
