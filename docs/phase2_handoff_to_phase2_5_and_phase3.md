# Phase 2 Handoff to Phase 2.5 and Phase 3

**Phase:** phase2_infra | **Non-experimental:** true

## Phase 2.5 — Token and Context Profiling

Phase 2.5 performs **authoritative** token and context-window analysis.

Phase 2 collected preliminary token fields (`tool_count`, `schema_token_count`,
`metadata_token_count`, `total_prompt_token_count`, `total_context_token_count`)
as engineering measurements only. These are **not** authoritative.

Phase 2.5 will:
- Define the official tokenization method
- Measure context growth across density levels
- Produce the authoritative token/context profiling report
- Freeze measurements before Phase 3 begins

## Phase 3 — Competence Baseline

Phase 3 starts a **fresh competence dataset**.

### Non-Reuse Rule

> No Phase 2 LLM smoke-test run may be counted toward the Phase 3 competence
> baseline, regardless of whether it is benign, successful, repeated, or
> structurally similar to a Phase 3 trial.

This means:
- Phase 2 LLM smoke-test rows are engineering artifacts only
- They must not be copied into Phase 3 baseline logs
- They must not be counted toward Phase 3 trial totals
- They must not be used to satisfy the ≥50-trial competence baseline
- They must not be used in model inclusion/exclusion decisions except as
  proof that the endpoint can connect

### Data Classification

- No Phase 2 row is pilot experimental data
- No Phase 2 row is core experimental data
- No Phase 2 row is official experiment data
- All Phase 2 rows have `phase: "phase2_infra"` and `non_experimental: true`

## Artifacts Handed Off

| Artifact | Location |
|----------|----------|
| FastMCP server | `server/mock_server.py` |
| Mock tools (5) | `server/tool_definitions/` |
| Mock data store | `server/mock_data_store.py` |
| Schema variants (9) | `schemas/` |
| Schema hash ledger | `reproducibility/schema_hash_ledger.csv` |
| Reset endpoint | `server/reset_endpoint.py` |
| Orchestrator | `client/orchestrator.py` |
| Logging writer | `client/logging_writer.py` |
| Docker configs | `docker/` |
| Test battery | `tests/` |
| Reproducibility manifest | `reproducibility/reproducibility.md` |
| Scope confirmation | `docs/phase2_scope_confirmation.md` |
| Audit checklist | `docs/phase2_audit_checklist.md` |

## Open Items for Phase 2.5/3

1. Populate `reproducibility/reproducibility.md` TBD fields with actual runtime values
2. Record Docker image digests after build
3. Complete LLM benign smoke test with local model
4. Freeze model version before Phase 3 trials
5. Import Phase 1 approved payloads (if governance is complete)
