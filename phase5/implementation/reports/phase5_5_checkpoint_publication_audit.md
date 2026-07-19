# Phase 5.5 M2/M4 checkpoint publication audit

## Finding

The official M2 and M4 runners checkpoint every six completed trials. The checkpoint publisher previously passed every changed evidence path as an individual Git argument and accepted non-canonical evidence paths by prefix comparison.

## Remediation

- Status parsing is NUL-delimited and rename-aware.
- Git pathspecs are supplied through NUL-delimited stdin, avoiding OS argument limits.
- Checkpoint paths reject absolute paths, traversal components, and symlink escapes outside `phase5_5/evidence`.
- Negative path-validation tests are included.

## Verification

M2 and M4 Phase 5.5 suites pass with security lint, forbidden-analysis lint, frozen-path guard, and diff checks. The configured GitHub checkpoint cadence remains six completed trials per checkpoint, followed by final publication and receipt synchronization.
