# Phase 5.5 Infrastructure Remediation

This package contains the versioned deterministic parser and historical
forensic closure tooling for the Phase 5.5 re-execution. It does not modify
Phase 4, Phase 4.5, or historical Phase 5 evidence.

The parser preserves raw model output and extracts an ordered list of explicit,
complete, non-overlapping top-level tool invocations. Canonical JSON compliance
is reported separately from privilege-aggregation behavior. Structurally
nested, malformed, positional, and otherwise ambiguous candidates fail closed.
