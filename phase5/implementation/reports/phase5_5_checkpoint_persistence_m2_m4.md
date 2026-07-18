# Phase 5.5 Checkpoint Persistence Remediation: M2 and M4

## Decision

Remote checkpoint persistence is required for M2 and M4. Historical Phase 5
campaigns reached the Kaggle safety horizon before completion: M2 completed
750 trials in about 7.60 hours and M4 completed 250 trials in about 8.48
hours. A fresh restart without durable lineage would repeat completed work.

## Controls

- The official runner publishes an append-only checkpoint after every six
  completed trials, and flushes the remaining trials at each batch boundary.
- A checkpoint records the run ID, model slot, batch and target identity,
  completed lineage count, lineage hash, parent commit, and publication time.
- Publication is allowed only from the approved Phase 5.5 model branch, when
  the local and remote parent heads match, and when all dirty paths are under
  `phase5_5/attempts/` or `phase5_5/evidence/`.
- Checkpoint commits contain evidence only. Source, manifests, notebooks, and
  reports cannot be included by the checkpoint publisher.
- The publication receipt verifies the resulting remote commit and is written
  outside the repository output directory.
- On restart, completed accepted and invalid target identities are skipped from
  the immutable lineage store. Orphaned targets remain eligible for explicit
  recovery and replacement lineage.
- The final evidence package refreshes its branch head after checkpoint
  publication, so the final manifest binds the latest evidence commit.

This bounds an unexpected interruption to at most the current checkpoint
window (six trials, or one in-flight trial), rather than losing hours of local
progress. A failed publication is fail-closed: the campaign must not be
treated as sealed until the remote receipt and lineage are reconciled.

## Scope and integrity

The change is isolated to the Phase 5.5 execution path and the M2/M4 branch
artifacts. Phase 4 and Phase 4.5 frozen sources are unchanged. Historical
outputs are not rewritten. The existing parser, grader, provenance gates,
model-slot checks, and evidence hashing remain authoritative.

## Verification

The branch test suite covers checkpoint serialization, parent-head and path
allowlisting, trial-bounded callback behavior, batch-tail flushing, and resume
skipping of already finalized targets. Full validation passed on the M2 and M4
branches after these changes.

