# Phase 5.5 Forensic and Persistence Remediation

## Scope

This report covers the additive Phase 5.5 remediation only. Frozen Phase 4,
Phase 4.5, and historical Phase 5 raw evidence remain unchanged.

## Historical Evidence

- M2 preserved run: `P5RUN-P5-DV-1.0.2-A7C91E42-M2-20260718-0A3C9E18`.
- M4 preserved run: `P5RUN-P5-DV-1.0.2-A7C91E42-M4-20260718-E19BD69F`.
- Each preserved run contains 750 attempt directories and 135 checkpoint
  records.
- Historical attempt event logs end in `FINALIZED`, while preserved attempt
  manifests retain `attempt_status: DISPATCHED`. This is recorded as a
  historical consistency defect; no historical manifest or raw evidence is
  rewritten.
- M1 and M3 have no recoverable official evidence from the failed executions.

## Remediation

All four model branches now include:

- append-oriented checkpoint publication every six completed trials and at
  batch tail;
- completed-target resume filtering, including invalid and orphan outcomes;
- GitHub Basic authentication with remote-head verification;
- path-safe evidence staging;
- optional, non-blocking GPU diagnostics;
- isolated real-backend pretrial attempt and evidence roots;
- branch-bound model configuration and provenance checks.

The pretrial executes exactly three complete real trials from the first frozen
batch. It is non-official, does not count toward Phase 5, and does not publish
to the official evidence branch. Its `resume_required: true` result is
expected because the bounded pretrial deliberately leaves the official queue
pending.

## Acceptance Evidence

The implementation suites pass on every branch. Kaggle execution remains the
required external validation: first run the matching pretrial notebook and
inspect its hashed manifest/archive, then dispatch the official notebook only
after the preflight and publication-authentication gates pass.
