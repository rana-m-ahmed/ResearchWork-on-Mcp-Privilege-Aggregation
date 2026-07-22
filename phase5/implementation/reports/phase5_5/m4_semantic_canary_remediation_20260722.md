# M4 Semantic Canary Remediation

## Finding

The M4 pretrial evidence was hash-valid and lifecycle-complete, but all three
attempts ended in `NO_INVOCATION_FOUND`. The raw generations were repeated
token strings (`EPEPE...` in the latest run and `laitlait...` in an earlier
run), both reaching the 512-token limit with KV cache enabled. The previous
canary checked only that two cached generations were identical. Therefore,
deterministic unusable output could pass the runtime gate.

## Remediation

The M4 canary now requires both:

1. exact cached determinism, including token-ID equality and KV-cache evidence;
2. the exact semantic response `READY` to its frozen canary prompt.

The generated M4 pretrial notebook runs this canary before dispatching its
three-trial diagnostic batch. A failed canary writes no scientific evidence
and stops with an explicit runtime error. The official M4 runner already uses
the same canary script, so the strengthened semantic condition propagates to
official authorization as well.

When the cached path fails the semantic check, the canary releases that model
instance and validates a fresh uncached instance. If the uncached path passes,
the receipt records `runtime_mode=uncached` and the runner propagates that mode
to the campaign subprocess. If both paths fail, execution remains blocked.

M1-M3 notebook generation and runtime behavior are unchanged.

## Verification

- Semantic canary tests reject empty output and the observed `EPEPEPEPE` and
  `laitlaitlait` degeneracy patterns.
- Full Phase 5 and Phase 5.5 test suite: `323 passed`.
- The generated M4 pretrial and official notebooks contain the semantic gate
  and propagate the canary-selected cache mode.

## Release Decision

This closes the acceptance-gate loophole, but it does not make the current M4
runtime ready for official execution. The observed M4 backend must first pass
the strengthened canary on Kaggle. Until then, M4 remains blocked; the parser
must continue to fail closed on missing invocations.
