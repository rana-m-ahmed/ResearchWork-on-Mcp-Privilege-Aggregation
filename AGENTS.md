# Repository Instructions

- Treat `phase4/` and `phase4_5/` as frozen, read-only sources of truth.
- Do not invent missing scientific settings, model identities, trial counts, parser rules, or evidence values.
- Keep Phase 5 changes task-scoped and fail closed when a frozen value is missing, ambiguous, or hash-invalid.
- Add tests for every new behavior, including negative and fault-path coverage.
- Keep evidence append-oriented; do not silently rewrite reports or raw outputs.
- Do not print, commit, or log secrets.
- Never use force push, hard reset, history rewrite, or similar destructive Git history edits.
- Put implementation reports under `phase5/implementation/reports/`.
- If a prompt conflicts with a higher-source artifact, stop and document the conflict instead of guessing.
