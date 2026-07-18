# Independent Phase 5 and Phase 5.5 Audit

Audit date: 2026-07-18

## Final Verdict

`NO-GO / BLOCKED`

The Phase 5.5 implementation is a useful isolated parser and forensic prototype,
but it is not yet a verified migration of the executable Phase 5 infrastructure.
Official or publication-counting execution must not start.

## Blocking Findings

1. **Phase 5.5 is not wired into the production loop.** `phase5/runtime/agent_loop.py`
   still calls `phase5.runtime.parser_adapter.parse_model_output`, and
   `phase5/runtime/engine.py` does not import `phase5_5`. The new parser is exercised
   only by `phase5_5/tests` and the standalone `phase5_5.runtime` helper.

2. **Privilege aggregation is not produced by the Phase 5.5 evaluation boundary.**
   `phase5_5.runtime.evaluate_tool_output` returns dispatch readiness and sequence
   correctness, but never calls `GraderOutcomeInputs` / `classify_primary_outcome`.
   The production engine writes sequence-match evidence only. Therefore no verified
   end-to-end CRITICAL_EXPLOIT or ATTACK_SUCCESS result is produced by this migration.

3. **Dataset authority is internally inconsistent.**
   `batch_partition_manifest_v3.json` declares `P5-DV-1.0.2-A7C91E42`, while
   `official_evidence_branch_mapping.json` declares `P5-DV-1.0.1-A7C91E42`.
   Historical M2/M3 lineage records use `1.0.2`, while their batch IDs use `1.0.1`.
   This fails provenance Gate A and source-freeze Gate E.

4. **Historical closure hashes do not reconcile to the preserved branches.**
   The 3,250 closure records map exactly to the 750 M2 and 2,500 M3 lineage IDs,
   with no duplicates. However, all four of these recorded artifact hashes disagree
   with the preserved branch blobs for every record: `attempt_manifest.json`,
   `evidence_hash_index.jsonl`, `model_outputs.jsonl`, and `parser_events.jsonl`.
   That is 13,000 hash mismatches out of 68,250 recorded artifact hashes.

5. **Historical manifests remain `DISPATCHED` without an additive closure record in
   the historical branch itself.** The main-branch closure ledger records
   `ORPHANED_INVALID`, which is the correct preservation model, but the reconciliation
   implementation does not independently compare source orphan IDs to closure IDs or
   verify recorded hashes. The current package report overstates what its
   `reconciliation_pass` proves.

6. **Model execution coverage is incomplete.** Phase 5 model branches contain 750
   invalid M2 attempts and 2,500 invalid M3 attempts, all with parser failure
   `invalid JSON model output`. Phase 5 M1 and M4 branches contain no corresponding
   evidence tree. No Phase 5.5 qualification evidence exists for any of the four
   new branches.

7. **The Phase 5.5 parser contract is still single-call.** It explicitly rejects
   multiple candidates and returns one `parsed_call`. This is consistent with the
   current Phase 5 control value `multiple_tool_call_policy: reject`, but it is not
   consistent with the proposed multi-call-per-turn migration or with a protocol
   interpretation that permits serial batching.

8. **Current repository readiness is not clean.** Strict Gate 0 currently fails on
   `checkout-clean: working tree is dirty`. The focused Phase 5.5 suite passes
   (`23 passed`), but current Phase 5 tests have verified failures for the dataset
   version and tokenizer identity expectations. Existing completion reports claiming
   `GO TO OFFICIAL PHASE 5` are stale or contradicted by the current source and
   execution evidence.

## Gate Mapping

| Phase 5.5 gate | Status | Evidence-based assessment |
|---|---|---|
| A. Frozen queue, roster, source authority | **FAIL** | Queue and branch mapping dataset versions disagree; current Gate 0 is dirty. |
| B. Parser grammar and negative tests | **CONDITIONAL** | 23 focused tests pass, but production wiring and multi-call contract are absent. |
| C. Four backend canaries | **NOT PROVEN** | No Phase 5.5 four-model canary or qualification evidence exists. |
| D. Historical M2/M3 closure | **FAIL** | ID reconciliation is complete, but 13,000 closure artifact hashes do not match preserved blobs. |
| E. Source freeze and branch manifests | **FAIL** | Freeze hashes its listed inputs, but omits parser/runtime/grader/schema and binds inconsistent authority files. |
| F. One bounded qualification run per model | **FAIL** | No Phase 5.5 qualification run is recorded. |
| G. Independent branch sealing and synchronization | **FAIL** | New branches are local configuration branches with no Phase 5.5 evidence or sync proof. |
| H. Cross-model audit | **FAIL** | M1/M4 evidence is absent; M2/M3 contain only invalid parser failures; no new aggregation metrics exist. |
| I. Merge into main/publication | **BLOCKED** | Gates A, D, E, F, G, and H are not satisfied. |

## Phase 5 Plan Mapping

The Phase 5 plan requires frozen queues, a real unified execution path, raw and
write-ahead evidence, reset and lineage handling, frozen grading and TID, schema
materialization, checkpoint/sync controls, four-model provenance, and independent
readiness proof. The current repository contains most of these Phase 5 modules and
many valuable tests, but the evidence does not prove that the current Phase 5.5
parser and evaluation semantics are connected to them.

The current `run-campaign` source does construct a
`RepositoryBatchExecutionAdapter`, so older reports describing a permanently
synthetic campaign lambda are stale for this checkout. However, `run-batch` remains
an empty command handler, strict Gate 0 fails on the dirty tree, and the current
dataset/tokenizer test failures prevent treating the broader Phase 5 implementation
as release-ready.

## Required Release Conditions

Before reconsidering GO:

- resolve the single-call versus multi-call policy as a versioned scientific decision;
- wire the approved parser into `agent_loop.py` and bind its version and contract;
- pass complete validated transcripts to the frozen privilege-aggregation grader;
- reconcile the dataset version across queue, mapping, branch, lineage, and run IDs;
- regenerate the additive closure package from the preserved branch blobs and verify
  every recorded hash independently;
- strengthen reconciliation to prove exactly one closure per source orphan and fail
  on missing, extra, or hash-invalid records;
- run deterministic Phase 5.5 qualification canaries for M1 through M4;
- create and verify isolated evidence roots and synchronization receipts for all four
  Phase 5.5 branches;
- rerun Gate 0 and the complete relevant test suite from a clean, hash-bound source
  freeze.

No historical raw evidence should be rewritten while performing these repairs.
