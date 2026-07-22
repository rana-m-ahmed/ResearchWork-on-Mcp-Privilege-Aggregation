# M2 Phase 5.5 Pretrial Timeout Remediation

## Finding

The latest M2 pretrial runner correctly reached model readiness, but its bounded
batch failed the `analysis_eligible_count == 3` gate. The shared state-machine
control used a 60 second per-model-turn timeout. M2 uses
`deepseek-ai/DeepSeek-R1-Distill-Llama-8B`, and its real-backend generation can
cross that boundary on a tool-result follow-up turn. Such an attempt is
correctly recorded as evidence-ineligible because it is a model-generation
timeout, but the timeout was an infrastructure mismatch for this model.

## Remediation

The Phase 5.5 control loader now supports an additive per-slot timeout override.
M2 is bound to 120 seconds; slots without an override retain the existing 60
second value. The override is selected from the model slot passed to the shared
execution engine, so M1, M3, and M4 behavior is unchanged.

This does not repair model output, synthesize tool calls, or convert a model
failure into acceptance. Parser failures and other invalid behavior remain
fail-closed and analysis-visible when their evidence is complete.

## Verification

- Agent-loop regression tests: `10 passed`.
- Execution-adapter regression tests: `11 passed`.
- Source-freeze and notebook binding tests: `5 passed`.
- M2 v3 source freeze bound source commit:
  `896f3dca8be13b9f87cbddef879bc1d6c5b28f33`.
- M2 branch head:
  `a009f21301e81f48e45360f33024046f919edccf`.
- Official preflight source matching passed for all four branches. Local CUDA
  availability and official dispatch authorization remain environment gates.
