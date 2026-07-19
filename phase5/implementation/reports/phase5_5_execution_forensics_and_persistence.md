# Phase 5.5 Execution Forensics and Persistence Remediation

## Historical Findings

The preserved remote evidence was audited before remediation. M2 run
`P5RUN-P5-DV-1.0.2-A7C91E42-M2-20260718-0A3C9E18` contains 750 attempt
directories and 135 checkpoint records. M4 run
`P5RUN-P5-DV-1.0.2-A7C91E42-M4-20260718-E19BD69F` contains the same counts.
Their checkpoint sequence is consistent with the six-trial barrier interval.

The attempt event logs end in `FINALIZED`, but the preserved
`attempt_manifest.json` files retain `attempt_status: DISPATCHED`. This is a
historical record-consistency defect. The raw manifests and evidence are
forensic inputs and are not rewritten by this remediation. Any publication
analysis must reconcile final event state against the additive lineage and
closure records rather than treating the stale manifest field as a new run
failure.

At the time of audit, M1 and M3 contained qualification artifacts but no
official attempt evidence. Their runners did not install the durable
checkpoint callback, so an interrupted session could lose all unpushed work.
The M2/M4 checkpoint publisher and final publisher also used an authentication
header format rejected by GitHub's HTTPS Git endpoint. This explains the
checkpoint/publication failures after otherwise healthy model execution.

## Remediation

All four model branches now share:

- checkpoint publication after every six completed trials and at batch tail;
- completed-target resume filtering, including previously finalized invalid
  attempts, so interruption does not duplicate work;
- canonical evidence-path and remote-head validation;
- path-list Git staging to avoid operating-system argument-length failures;
- GitHub Basic authentication using `x-access-token:<token>` for checkpoint and
  final publication;
- remote-head reconciliation after every push;
- a bounded, real-backend pretrial mode that cannot set official, publication,
  or Phase 5 counting flags.

The pretrial executes one complete frozen 50-row batch per slot, streams model
and heartbeat output, and writes a local hashed evidence archive. It does not
publish to the official evidence branch. It is a qualification gate for the
runtime and persistence path, not scientific evidence.

## Operational Boundary

Historical M2/M4 outputs remain preserved exactly as published. A successful
new run requires the pretrial archive, a visible `GITHUB_PUBLICATION_AUTH_READY`
message, successful checkpoint receipts, and a final publication receipt. A
Kaggle interruption after the last receipt resumes from the next uncompleted
target; a session with no receipt is not considered resumable official work.
