# Phase 5 Runtime Instructions

- Runtime helpers must stay narrow and deterministic.
- Do not invent scientific defaults, backend behavior, or trial semantics in runtime code.
- Keep runtime helpers free of network access and nested Docker assumptions.
- Mention loopback-only behavior explicitly when runtime helpers touch process or socket setup.
- Prefer explicit failures when a required runtime input is missing or ambiguous.
