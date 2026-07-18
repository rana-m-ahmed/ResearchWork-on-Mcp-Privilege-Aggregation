# Phase 5.5 M4 Performance Remediation

## Finding

The repaired M4 backend intentionally disabled the Phi-3.5 KV cache because
the frozen Hugging Face revision required a DynamicCache compatibility shim.
That avoided the earlier runtime failure but made autoregressive generation
recompute the full prefix for every output token. This is the primary safe,
code-level throughput bottleneck identified in the current branch.

## Optimization

The M4 branch now has an explicit `PHASE5_M4_ENABLE_KV_CACHE=1` fast path. It
keeps eager attention and the existing DynamicCache compatibility shim, and
records the selected cache mode in both the load plan and generation receipt.
The default outside the official runner remains uncached, so accidental use
cannot silently change other modes.

The M4 notebook also enables Hugging Face safetensor parallel loading with
four workers for model startup only. Other model slots retain the previous
loading controls.

Each M4 generation now records CUDA-synchronized elapsed time, generated-token
throughput, and per-device allocated/reserved memory. This is diagnostic
telemetry only, but it makes under-utilization and regressions observable in
the preserved generation receipt and live Kaggle logs.

The optimized canary additionally records the resolved Hugging Face device map
and cached-generation memory metrics, so a successful CUDA check cannot be
mistaken for proof that the required dual-GPU placement was actually used.

The first Kaggle optimized canary exposed a missing
`DynamicCache.to_legacy_cache()` method after successful weight materialization.
The shim now supports both Transformers 5 `layers` caches and the older
`key_cache`/`value_cache` representation, with regression coverage for the
legacy conversion path. The failure was confined to the canary; no official
trial was dispatched.

Before official dispatch, the M4 notebook runs a non-scientific runtime canary:
it loads the exact frozen revision, generates the same fixed prompt with cache
enabled and disabled, and requires exact decoded-output equality plus explicit
receipt confirmation for both modes. Any loading, cache, or output mismatch
stops the run before official trials.

## Safety boundary

No frozen queue, prompt, schema, parser, grader, model revision, trial order,
or acceptance rule is changed. The canary output is diagnostic only and is
never counted as a trial or publication evidence. The existing checkpoint
publisher remains active, so an interrupted optimized run resumes from the
last remote lineage checkpoint.

## Validation

The change adds explicit cache-mode and notebook wiring tests. Required
validation is the complete Phase 5 and Phase 5.5 test suites, Python compile
validation, notebook-cell compilation, and a real Kaggle M4 canary pass before
official dispatch.
