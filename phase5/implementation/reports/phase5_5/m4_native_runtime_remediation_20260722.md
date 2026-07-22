# M4 Native Runtime Remediation

## Decision

M4 is migrated from the repository-provided Phi remote model code to the
Transformers 5.0.0 native `Phi3ForCausalLM` implementation. The model ID,
Hugging Face revision, float16 setting, tokenizer, prompt, parser, trial rows,
and grading rules remain unchanged.

## Evidence Basis

The frozen model config at revision
`2fe192450127e6a83f7441aef6e3ca586c338b77` advertises remote code produced
for Transformers 4.43.3. The frozen Phase 5 backend is Transformers 5.0.0.
The remote path required several compatibility shims and produced repeated
token loops under both cached and uncached generation. Historical Phase 5 M4
evidence independently records 250/250 inference timeouts at S10.

## Implementation

- M4 model loading sets `trust_remote_code=false` and uses the native Phi3
  implementation bundled with the frozen Transformers backend.
- Runtime loading fails closed unless the loaded class module begins with
  `transformers.models.phi3.`.
- Load plans and generation receipts record `model_code_path` and
  `model_class_module`.
- The M4 canary now requires a deterministic parser-valid invocation of
  `read_internal_notes` with the exact synthetic canary arguments.
- Cached mode remains preferred; uncached mode is selected only after passing
  the same semantic and deterministic gate.
- Failure of both modes writes a non-passing diagnostic receipt and blocks all
  pretrial or official dispatch.

## Scope Protection

The native-code selection is conditional on the exact Phi-3.5 model identity.
M1-M3 retain their existing repository-default model-loading behavior. No
Phase 4, Phase 4.5, historical Phase 5 evidence, parser rule, or scientific
input is modified.

## Verification Boundary

Local tests verify model-path selection, rejection of repository remote code,
semantic parser compatibility, cache-mode invariants, generated notebook
binding, and failure paths. A real Kaggle M4 pretrial remains required to prove
that the native float16 model produces the canonical canary and usable trial
outputs on dual T4 hardware.

Full local verification: `327 passed` across `phase5/tests` and
`phase5_5/tests`.
