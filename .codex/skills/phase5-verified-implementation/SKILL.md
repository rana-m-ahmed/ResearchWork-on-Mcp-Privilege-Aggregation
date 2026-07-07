---
name: phase5-verified-implementation
description: Phase 5 governance workflow for bounded implementation, tests, report generation, diff review, and commit readiness.
---

# Phase 5 Verified Implementation Skill

Use this skill for bounded Phase 5 implementation tasks.

## Workflow

1. Read the parent specification and applicable `AGENTS.md` files.
2. Identify frozen inputs and verify their real paths.
3. List the exact paths that may change.
4. Implement only the assigned task scope.
5. Add or update positive, negative, invariant, and fault-path tests.
6. Run the required unit, integration, and protocol checks.
7. Produce the task implementation report and any required machine-readable companion.
8. Review the final diff for scope drift and secrets.
9. Commit only if every acceptance criterion passes.
10. Stop after the task. Do not roll into the next one.

## Guardrails

- Never modify Phase 4 or Phase 4.5 frozen artifacts.
- Never invent missing frozen values or hidden defaults.
- Never use output repair, constrained decoding, or inferential analysis to paper over validation gaps.
- Never mix official evidence generation with source changes in the same commit when a task requires separation.
- Never use force push, hard reset, history rewrite, or secret exposure.

## Output Standard

Every completed task should leave behind:

- a task packet;
- an implementation report;
- any required audit template or audit report;
- test output;
- diff review notes;
- a commit SHA when authorized.
