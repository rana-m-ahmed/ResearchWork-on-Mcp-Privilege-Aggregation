# Phase 5.5 Run-Unique Attempt Identity Remediation

## Finding

M1, M2, and M4 loaded successfully but failed before completing their first new lineage append. Physical evidence had already been isolated by run, but attempt IDs were still generated with the frozen batch token. Because batch tokens repeat across campaigns, fresh `A000` attempts reproduced historical IDs and the lineage store correctly rejected different content under the same ID.

## Remediation

New attempt IDs retain the frozen grammar and attempt index but use the session token from the validated campaign run ID. This makes identity unique across campaigns while preserving deterministic retries within a campaign. Global lineage uniqueness remains strict, so true same-ID conflicts still fail closed.

The source-freeze builder now resolves any supplied Git ref to its canonical 40-character commit SHA before hashing or writing the manifest. This prevents recurrence of shortened hashes or the literal `HEAD` value.

## Scientific boundary

No model behavior, parser rule, grader rule, prompt, dataset row, treatment condition, or acceptance criterion changed. The remediation affects execution/evidence identity only.

## Verification

- Focused identity, lineage, resume, publication, and source-freeze tests: `45 passed`.
- Complete `phase5/tests` and `phase5_5/tests` suite on M2: `373 passed`.
- Final diff review is limited to the shared runtime, source-freeze builder, focused tests, and this task's governance records; no secret-like values were introduced.
