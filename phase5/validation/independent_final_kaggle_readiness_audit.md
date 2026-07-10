# Independent Phase 1–5 Integrity and Kaggle Readiness Audit

## A. Git and Repository State
- **Current Branch:** `main`
- **Current HEAD:** `d30309d9397f7ea096ae933c371e890f06fa6aa6`
- **Remote Branch and SHA:** `origin/main` at `759f5d167429af42b63e5c973914a1f41075887a`
- **Clean Working Tree:** **FAIL**. Untracked files and modifications are present.
- **Candidate Commit Remotely Reachable:** **FAIL**. The local tree is dirty and ahead of origin/main.

## B. Governance
- **Original Phase 4 Byte-Identical:** **FAIL**. Cryptographic hash verification failed for `phase4/configs/statistical_plan.yaml` and `phase4/reports/phase4_go_no_go_decision.md`.
- **Signed/Versioned Amendment:** None verified that permits the observed hash drift.

## C. Phase 1 Provenance
- **Verification:** Cannot be verified successfully until Phase 1/Phase 4 remediation is fully completed. The required payload provenances remain unfixed per previous mandates.

## D. Phase 3 Tasks
- **Verification:** Skipped pending upstream repairs.

## E. Corrected Phase 4 Package
- **Verification:** **FAIL**. The execution manifest and package hashes do not match the upstream registry.

## F. Corrected Phase 4.5
- **Verification:** **FAIL**. `pytest` reveals schema failures related to trial row fields (`task_id`, `task_hash`) not matching expectations in Phase 5 materializer.

## G. Phase 5 Rebinding
- **Verification:** **FAIL**. Gate 0 failed immediately due to a dirty working tree.
- **Tests:** **FAIL**. `pytest` yielded 3 failures and 499 passing tests. 

## H. Tooling Safety
- **Verification:** **PASS**. `check_phase5_instructions.py`, `lint_phase5_secrets.py`, and `lint_phase5_forbidden_analysis.py` successfully passed.

## Final Findings

1. `test_registry_loads_and_resolves_verified_entries` FAILED due to hash mismatch on `Phase 4 GO report` (Expected: `97927a12b707d65985c3db66890dd1c8be28d94009b5469f8a93379878dd729a`, Actual: `5766e232af92a5d6b545f8e2f61c2fe499d9da71b7760e3f9a9fab6b8054c3e1`).
2. `test_verified_registry_hashes_match_checkout_attributes` FAILED due to hash mismatch on `phase4/configs/statistical_plan.yaml` (Expected: `96161dd17f00bd76534f3f70842775e303e926319ff59406c4ef06108df404ec`, Actual: `aad0afdd8f395ecdd4853e737782c487e3b3207730e3496c9e7b4d1ddb558a07`).
3. `test_materializer_resolves_evidence_and_preserves_exact_schema_rows` FAILED due to `SchemaInvariantError: frozen trial row field mismatch: extra=['task_id', 'task_hash']`.
4. `gate0 --strict` FAILED due to a dirty working tree (`GATE0_FAILURE: - checkout-clean: working tree is dirty`).

## Verdict

```text
FINAL KAGGLE READINESS VERDICT:
RETURN TO PHASE 1/4 REMEDIATION
```
