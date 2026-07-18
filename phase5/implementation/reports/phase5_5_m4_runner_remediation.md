# Phase 5.5 M4 Runner Remediation

## Scope

This additive remediation is limited to the `phase5_5-model-4` branch. It keeps
the Phase 5.5 parser, lifecycle, provenance gates, dataset, and evidence branch
unchanged. Phase 4 and Phase 4.5 artifacts remain read-only.

## Findings

The supplied M4 failure occurred before model loading because the notebook called
`nvidia-smi` as a mandatory executable. Some Kaggle environments expose CUDA
through PyTorch while not exposing that diagnostic utility. The old Phase 5 M4
history also contains a validated Phi-3.5 runtime stabilization for the frozen
Hugging Face revision: eager attention, disabled KV cache, and compatibility
methods for legacy DynamicCache calls. The current Phase 5.5 M4 branch did not
contain that model-specific stabilization.

## Changes

- `nvidia-smi` is now optional for the M4 hardware cell and campaign heartbeat.
  PyTorch CUDA availability and the required two-device gate remain mandatory.
- Phi-3.5 model loading uses eager attention and `use_cache=False`.
- Phi-3.5 generation uses `use_cache=False` and records readiness only after
  placement validation.
- A narrow DynamicCache compatibility shim is installed only for the Phi-3.5
  identifier and is covered by tests.
- Non-Phi model kwargs retain the prior cache behavior.

## Validation

- Full Phase 5 and Phase 5.5 test suites: 287 passed.
- Notebook cells compile and notebook JSON remains valid.
- The generated runner is fixed to `MODEL_SLOT = M4` and the
  `phase5_5-model-4` evidence branch.
- The runner contains the optional `nvidia-smi` fallback and mandatory torch
  CUDA device-count check.
- Historical Phase 5 branches and evidence are not used by this runner.

## Operational boundary

This validates the code, notebook, and provenance contract. It cannot guarantee
Kaggle capacity, Hugging Face availability, or the behavior of the external
model service before a real M4 canary/official run. Those remain runtime gates.
