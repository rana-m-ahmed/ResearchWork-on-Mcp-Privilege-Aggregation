# M4 Phase 5.5 Pretrial Timeout Remediation

Date: 2026-07-22
Model slot: M4

## Finding

The M4 model loaded successfully and emitted generation telemetry, but the
pretrial reported `analysis_eligible_count=0/3`. The log showed
`kv_cache_enabled=False` and generation times of approximately 264, 268, and
519 seconds. Phase 5.5 freezes the per-model-turn timeout at 60 seconds, so
the attempts were correctly marked ineligible as model-generation timeouts.

The failure was caused by runner environment propagation, not parser logic,
model loading, flash attention, or evidence hashing. The repository already
contains a validated M4 cached-generation path and a deterministic M4 runtime
canary, but the canary's child-process environment did not propagate to the
pretrial or official campaign subprocess.

## Remediation

M4 runner generation now sets `PHASE5_M4_ENABLE_KV_CACHE=1` before launching
the campaign subprocess. This was added to both the pretrial and official
runner builders, and both generated M4 notebooks were regenerated. M1-M3 do
not set this variable and retain their existing runtime behavior.

The existing M4 cache compatibility shim and canary remain unchanged. No
timeout, parser, model identity, trial count, or frozen scientific setting was
altered.

## Verification

Targeted suite:

`python -m pytest phase5_5/tests/test_kaggle_notebook.py phase5_5/tests/test_m4_runtime_canary.py phase5/tests/test_model_backend_adapter.py -q`

Result: `21 passed`.

The M4 v3 source freeze must be bound to the remediation commit before the
next Kaggle run.
