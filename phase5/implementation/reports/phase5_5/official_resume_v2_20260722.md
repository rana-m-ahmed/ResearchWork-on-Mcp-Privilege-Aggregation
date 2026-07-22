# Phase 5.5 Official Resume V2 Implementation Report

Date: 2026-07-22

## Decision

The source-bound official resume implementation is complete and verified on all
four model branches. M2, M3, and M4 resolve to `NEW` and are ready to start an
official campaign. M1 is intentionally launch-blocked because current-dataset
official evidence already exists under the legacy v1 checkpoint contract.

This report does not authorize deleting, reclassifying, or silently superseding
the M1 evidence.

## Resume Contract

- Retain the original run ID and continue checkpoint numbering after a restart.
- Bind each checkpoint to model slot, dataset version, source commit, batch
  manifest hash, run-plan hash, full lineage hash, and contiguous sequence.
- Skip only terminal targets in the same dataset and run.
- Retry only a terminal orphan through a valid parent-attempt chain.
- Validate each attempt directory, manifest identity, hash index, grader output,
  analysis eligibility, and terminal event before resuming.
- Refuse final publication after a process failure or while
  `resume_required=true`.
- Publish completion markers under an append-only run-specific directory.
- Fail closed on legacy, ambiguous, cross-model, source-mismatched, or tampered
  current-dataset evidence.

## Branch Verification

| Slot | Verified head | Frozen source commit | Resume state | Launch decision |
|---|---|---|---|---|
| M1 | `89620a97a1f0411e723b9f5dfd8576bc5efd158b` | `0c2d49fd7ba012f525e9fda06f03ebaf416bd355` | BLOCKED | Hold |
| M2 | `d3e53f79214ba611a0d3885b46df398eaa32a21a` | `16ec1a48a72ba9e877dd3a4b88a21c1c7935a87c` | NEW | Ready |
| M3 | `8cd17e02ffebc68798f5f7bdee24a2afbbc8b561` | `e15c2a8f24a296018c97c6ffcea594ac4d8c63db` | NEW | Ready |
| M4 | `3924a0fbb81188e6e2ccdef2938db05f51bedf0c` | `14d7065f8e83ad174cdb682c29e24491fc130ed0` | NEW | Ready |

Each branch passed 25 focused resume/publication tests, 4 source-freeze and
preflight tests, and strict Gate 0 from a clean detached checkout. The complete
shared Phase 5 and Phase 5.5 suite passed with 346 tests.

## M1 Evidence Conflict

M1 contains 106 lineage rows for
`P5RUN-P5-DV-1.1.0-TREATMENT-V3-M1-20260719-CDDB8576`: 89
`OFFICIAL_ACCEPTED` and 17 `INVALID`. Its 19 checkpoints are
`phase5_5_trial_checkpoint_v1`; the latest records 106 rows but has no v2
source/plan binding. Retrofitting those bindings would invent provenance.
Therefore the resolver returns:

`SchemaInvariantError: legacy current-dataset lineage has no source-bound v2 checkpoint`

An explicit scientific decision is required before launching M1: preserve the
legacy campaign as its own source epoch and define an append-only supersession,
or separately authorize another disposition. No automatic migration is valid.

## Scope Integrity

No Phase 4 or Phase 4.5 artifact was changed. No pretrial or official evidence
was deleted, rewritten, or reclassified. The shared patch does not alter the
model parser, prompt compiler, agent loop, or backend adapter, preserving the
validated M2 and M4 model-specific behavior.
