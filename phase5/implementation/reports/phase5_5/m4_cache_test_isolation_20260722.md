# M4 Cache Environment Test Isolation

Date: 2026-07-22
Model slot: M4

The M4 runner now enables `PHASE5_M4_ENABLE_KV_CACHE=1` process-wide before
the Phase 5.5 gate-0 test suite. A pre-existing unit test asserted the
adapter's default no-cache behavior without clearing that environment
variable, so the Kaggle suite failed even though the runner configuration was
correct.

The test now removes the variable with `monkeypatch` before asserting the
default behavior. The explicit opt-in test remains unchanged, preserving
coverage for both default and optimized M4 paths.

Verification:

`python -m pytest phase5/tests phase5_5/tests -q -p no:cacheprovider --basetemp .pytest-temp`

Result: `319 passed`.
