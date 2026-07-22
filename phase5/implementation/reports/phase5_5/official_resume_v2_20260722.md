# Phase 5.5 Official Resume V2 Implementation Report

Date: 2026-07-22

## Decision

The source-bound official resume implementation is complete and verified on all
four model branches. M1, M2, M3, and M4 resolve to `NEW` with zero completed
targets and are ready to start fresh official campaigns.

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
| M1 | `7f221d18b` | `846828072` | NEW | Ready |
| M2 | `7d6509639` | `474fb214b` | NEW | Ready |
| M3 | `54c751253` | `8d8b163e0` | NEW | Ready |
| M4 | `032dfa297` | `661061136` | NEW | Ready |

Each final branch passed 33 focused resume, publication, source-freeze, and
preflight tests. The complete shared Phase 5 and Phase 5.5 suite passed with
350 tests. Strict Gate 0 passed on every branch before the additive
supersession update and is rerun on the final committed heads below.

## M1 Evidence Conflict

M1 contains 106 lineage rows for
`P5RUN-P5-DV-1.1.0-TREATMENT-V3-M1-20260719-CDDB8576`: 89
`OFFICIAL_ACCEPTED` and 17 `INVALID`. Its 19 checkpoints are
`phase5_5_trial_checkpoint_v1`; the latest records 106 rows but has no v2
source/plan binding. Retrofitting those bindings would invent provenance.
Therefore the resolver returns:

`SchemaInvariantError: legacy current-dataset lineage has no source-bound v2 checkpoint`

The user explicitly authorized a fresh M1 run on 2026-07-22. The legacy package
was not deleted. It is preserved in place and covered by an append-only
`phase5_5_campaign_supersession_v1` record that binds the canonical 106-row
subset, status counts, and SHA-256 of all 19 checkpoints. The resolver accepts
the supersession only while every bound byte and identity remains exact, and it
cannot supersede a source-bound v2 campaign. M1 therefore resolves to `NEW`
without treating any legacy row as part of the fresh official run.

## Scope Integrity

No Phase 4 or Phase 4.5 artifact was changed. No pretrial or official evidence
was deleted, rewritten, or reclassified. The shared patch does not alter the
model parser, prompt compiler, agent loop, or backend adapter, preserving the
validated M2 and M4 model-specific behavior.
