# Phase 5 Instructions

- Limit Phase 5 edits to Phase 5 scaffold files, the Phase 5 task packets, the Phase 5 reports, and the Phase 5 CI/workflow scaffolding.
- Keep Phase 5 code importable from the repository root.
- Do not add official trial logic, inferential analysis, output repair, or nested Docker support here.
- Use fail-closed guard helpers for frozen-path, evidence, and lint checks.
- Add tests alongside any new Phase 5 behavior.
- Preserve append-only report history under `phase5/implementation/reports/`.

## Bounded I17E Official-Execution Adapter Authorization

Repository-owner authorization has been granted under task I17E to implement
and test the official-capable Phase 5 execution adapter and canonical Kaggle
runner. This authorization permits connecting frozen queue rows to the existing
model backend, agent loop, FastMCP, reset and isolation controls, append-only
attempt evidence, frozen grader and TID implementation, frozen trial
materializer, lineage, batch finalization, checkpoint/sync/resume/seal handling,
and deterministic fake-backend or synthetic non-official qualification.

The implementation must consume frozen scientific artifacts exactly as
provided. It must not redesign or regenerate scientific inputs.

### Still Prohibited

- Dispatching any official Phase 5 queue row or real official model campaign.
- Creating official accepted-trial evidence or writing real trial output to an
  official evidence branch.
- Advancing official model branches for collected evidence.
- Running vulnerability, defense, or utility experiments or inspecting
  scientific outcomes.
- Changing frozen models, revisions, digests, prompts, payloads, tasks, tool or
  trial schemas, grader or TID rules, trial counts, randomization, batch order,
  or statistical plans.
- Creating or moving an official source tag before qualification and an
  independent readiness audit pass.
- Representing synthetic, fake-backend, dry-run, or planning output as official
  evidence.

### Mandatory Execution Boundary

- Official-capable code must fail closed unless every official authorization
  condition is satisfied.
- Planning or synthetic processors must never be the default processor in
  official mode.
- No adapter may mark a row accepted unless the real execution pipeline has
  completed and every acceptance invariant passes.
- Development and qualification output must set `official_trial = false`,
  `counts_for_phase5 = false`, `publication_evidence = false`, and
  `synthetic_fixture = true` where applicable.
- This source-modification authorization expires when the v3 official source
  freeze is created.
