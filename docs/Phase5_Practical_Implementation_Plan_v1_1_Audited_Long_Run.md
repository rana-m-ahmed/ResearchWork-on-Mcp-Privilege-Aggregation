# Phase 5 Practical Implementation Plan — Version 1.0.0

## Codex 5.5 Agentic Development, GitHub Governance, Kaggle Execution, Checkpointing, and Validation Blueprint

**Project:** Empirical Evaluation of Privilege Aggregation Vulnerabilities in Edge-Deployed Open-Weight Agents via the Model Context Protocol (MCP)  
**Parent Specification:** `Phase5_Revised_Execution_Plan_v3_2.md`  
**Document Type:** Practical software-engineering and execution implementation plan  
**Document Version:** 1.1.0  
**Implementation Agent:** Codex using `gpt-5.5`  
**Authoritative Repository:** GitHub  
**Official Experimental Substrate:** Kaggle native container  
**Nested Docker:** Prohibited  
**Scientific Design Authority:** Phase 0–4.5 frozen artifacts only  
**Status:** Implementation blueprint; official trials remain blocked until all readiness gates in this document pass

---

# 0. Executive Decision

## 0.1 Verdict on the Proposed Workflow

The proposed workflow is viable with one mandatory control:

```text
Codex builds and validates Phase 5 infrastructure in the GitHub repository
→ a thin Kaggle notebook clones the exact authorized repository state
→ the notebook invokes one unified Phase 5 CLI
→ official rows execute inside a sealed Kaggle runtime
→ the batch is finalized, validated, and hash-bound
→ the official seal is closed
→ only then is a separate Git synchronization step allowed
→ finalized checkpoint artifacts are committed and pushed through an unsealed synchronization barrier
→ credentials are purged and source/frozen hashes are reverified
→ the same unified notebook may either re-seal and continue with the next contiguous batches or terminate near its safety horizon
→ a later Kaggle session resumes only when the current session cannot safely finish the remaining model campaign
```

The Kaggle notebook must **not** push while official model/MCP execution remains sealed. A push is permitted only at a synchronization barrier after the active attempt and all completed batches have been finalized, the seal is closed, and trial-facing MCP/model processes are stopped. After synchronization, the write credential must be purged, the exact source and frozen hashes must be reverified, a new seal epoch must be created, and only then may the same unified notebook continue. No source pull, merge, rebase, dependency change, or scientific-artifact change is permitted between seal epochs.

This design preserves:

- the Phase 5 native-container boundary;
- GitHub as the authoritative checkpoint and audit repository;
- the no-copy-drift and frozen-source rules;
- write-ahead attempt preservation;
- resumption after Kaggle interruption;
- separation of official evidence generation from network synchronization;
- prohibition on hidden source changes during official collection.

## 0.2 Implementation Principles

1. **Thin notebook, thick repository:** The notebook contains orchestration calls only. No scientific logic lives exclusively in notebook cells.
2. **One unified CLI:** Every local test and Kaggle execution uses the same versioned entry point.
3. **Frozen inputs are consumed, never recreated:** Phase 5 code verifies and loads the Phase 4 package.
4. **Source and evidence are separated:** Kaggle may write only to allowlisted evidence/checkpoint paths.
5. **Every Codex change is test-gated:** No implementation task is complete without automated validation and an implementation report.
6. **Every official dispatch is write-ahead logged:** A kernel crash cannot erase the fact that an attempt began.
7. **A valid model outcome is never rerun for convenience:** Only infrastructure/reset-invalid attempts are replaced.
8. **No outcome peeking:** Operational dashboards expose counts and health, not attack results.
9. **No execution across an open sync boundary:** Git synchronization is allowed only while unsealed. Continuing in the same Kaggle notebook requires credential purge, source/freeze re-verification, a new seal epoch, and a new operational segment record.
10. **Phase 5 does not alter science:** Any missing frozen setting is a hard stop.

---

# 1. Scope and Authority

## 1.1 What This Plan Implements

This plan implements the engineering required to:

- ingest and verify Phase 4 and Phase 4.5 artifacts;
- create the Phase 5 repository structure;
- expose one reliable command-line interface;
- run the FastMCP process and model backend inside Kaggle;
- execute the frozen multi-turn state machine;
- enforce the 4,096-token limit on every turn;
- preserve raw prompt, response, tool, reset, and hardware evidence;
- materialize only the frozen Phase 5 schema;
- run the frozen grader and TID calculator;
- preserve invalid, orphaned, and replacement attempts;
- finalize bounded batches;
- checkpoint compact progress to GitHub safely;
- resume from GitHub without duplicate accepted trials;
- complete the three frozen queues;
- generate the 1,530-row random QA sample and targeted census;
- produce the Phase 6 handoff.

## 1.2 What This Plan Must Not Implement

Codex must not:

- create or rebalance the trial matrix;
- rewrite a payload, task, prompt, tool schema, or metadata surface;
- change model identities or quantization;
- invent missing loop limits or parser rules;
- replace the frozen trial schema;
- change the eight-class taxonomy;
- change the ASR denominator;
- run inferential analysis;
- add output repair or constrained decoding;
- introduce nested Docker;
- allow the official trial subprocess to access GitHub credentials;
- push source-code changes from an official Kaggle evidence session;
- continue official execution while synchronization is active or without a complete post-sync re-verification and re-seal.

## 1.3 Source-of-Truth Order

When implementation details conflict, use this order:

```text
1. Phase 4 cryptographic lock and frozen artifacts
2. Phase 4.5 completed GO package and runtime evidence
3. Phase 5 Revised Execution Plan v3.2.0
4. This practical implementation plan
5. Codex task prompts and implementation notes
```

Codex must stop rather than resolve an upstream ambiguity by assumption.

---

# 2. Target End-to-End Architecture

```text
┌─────────────────────────────────────────────────────────────────┐
│ LOCAL / CODEX DEVELOPMENT                                       │
│                                                                 │
│ Codex 5.5 → task branch → implementation → tests → audit report │
│                         ↓                                       │
│                    pull request / merge                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ GITHUB — AUTHORITATIVE SOURCE AND CHECKPOINT REPOSITORY          │
│                                                                 │
│ frozen Phase 4/4.5 inputs                                       │
│ Phase 5 source code                                              │
│ notebook and unified CLI                                        │
│ compact accepted JSONL/checkpoints/manifests                     │
│ attempt lineage and validation reports                          │
│ content-addressed indexes for large evidence                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ exact clone and checkout
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ KAGGLE PREPARATION MODE                                          │
│                                                                 │
│ clone → verify commit → install pinned deps → attach models      │
│ Gate 0 → canary → create run/batch → seal                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ no Git write token; no network sync
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ KAGGLE OFFICIAL SEALED MODE                                      │
│                                                                 │
│ unified CLI → FastMCP → model → evidence writer → grader         │
│ per-turn token checks → reset → schema validation → checkpoint   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ finalize batch and close seal
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│ KAGGLE POST-SEAL SYNC MODE                                       │
│                                                                 │
│ validate allowlist → retrieve write token → fetch remote head    │
│ commit finalized compact artifacts → push → verify remote SHA    │
│ remove token material → reverify source/freeze → either re-seal or terminate                        │
└─────────────────────────┬───────────────────────────────────────┘
                          │ continue under a new seal epoch if time remains
                          │ otherwise a later session reclones the model branch
                          ▼
                 RESUME NEXT CONTIGUOUS BATCH
```

---

# 3. Codex 5.5 Agentic Engineering Protocol

## 3.1 Codex Operating Model

Use Codex with `gpt-5.5` for all implementation and audit tasks.

The agent is not given one enormous “build all Phase 5” prompt. Work is divided into bounded task packets with explicit inputs, permitted paths, tests, and exit criteria.

Each task follows:

```text
inspect
→ state assumptions
→ produce implementation plan for the task
→ implement only the assigned scope
→ run tests
→ run static validation
→ generate task report
→ inspect diff
→ commit
→ stop
```

## 3.2 Repository-Level Codex Instructions

Codex must first create and obey:

```text
AGENTS.md
phase5/AGENTS.md
phase5/kaggle/AGENTS.md
phase5/runtime/AGENTS.md
phase5/scripts/AGENTS.md
phase5/tests/AGENTS.md
```

The root `AGENTS.md` must state:

- upstream scientific artifacts are read-only;
- no changes inside frozen Phase 4/4.5 directories;
- no invented defaults for absent frozen settings;
- no hidden output repair;
- no trial-matrix generation;
- no inferential analysis in Phase 5;
- every new behavior requires tests;
- official evidence paths are append-oriented and never silently rewritten;
- Git commands such as force push, hard reset, filter-branch, and history rewrite are forbidden;
- no secret may be printed or committed;
- source changes and evidence generation may not be mixed in one official Kaggle commit;
- all implementation reports belong under `phase5/implementation/reports/`.

Specialized `AGENTS.md` files narrow instructions for their subtree.

## 3.3 Reusable Codex Skill

Create:

```text
.codex/skills/phase5-verified-implementation/SKILL.md
```

The skill must encode the repeatable task workflow:

1. read parent specification;
2. identify frozen inputs;
3. list paths that may change;
4. implement;
5. run the required unit/integration tests;
6. run protocol-lint checks;
7. produce a verification report;
8. refuse to commit on failure.

## 3.4 Task Packet Contract

Every task file under:

```text
phase5/implementation/tasks/
```

must contain:

```yaml
task_id:
title:
parent_requirements:
allowed_paths:
forbidden_paths:
inputs:
deliverables:
required_tests:
required_fault_tests:
acceptance_criteria:
commit_message:
dependencies:
```

## 3.5 Builder–Auditor Cycle

Each implementation task requires two logically separate Codex passes.

### Builder Pass

- implements only the assigned task;
- writes or updates tests;
- runs tests;
- produces a report.

### Auditor Pass

The auditor receives the parent specification and task report but is instructed to:

- inspect the actual diff and code;
- rerun tests independently;
- search for silent assumptions;
- verify error handling and fail-closed behavior;
- check frozen-path immutability;
- issue `PASS`, `CONDITIONAL PASS`, or `FAIL`.

A failed audit returns to a remediation task. The builder's self-report is never the sole evidence of completion.

## 3.6 Codex Permissions

For normal implementation:

```text
sandbox: workspace-write
approval policy: on-request or stricter
network: only when explicitly required for dependency documentation
```

Do not use unrestricted bypass modes as the standard workflow.

For independent audits, prefer read-only access except where tests need temporary output directories.

## 3.7 Codex Commit Rules

Codex may commit only when:

- all assigned tests pass;
- protocol lint passes;
- the task report exists;
- the diff contains no secret;
- no frozen path changed;
- no unrelated file changed.

Commit format:

```text
phase5(<task-id>): <imperative summary>

Implements:
- ...

Validation:
- <commands and result>

Frozen artifacts modified: no
```

---

# 4. GitHub Repository Governance

## 4.1 Branch Classes

### Protected Source Branch

Use the existing repository default branch as the authoritative merged source branch.

Recommended implementation branch:

```text
phase5/implementation-v1
```

All source changes are merged through reviewed pull requests.

### Official Evidence Branches

Resolve exact branch names from the Phase 4/4.5 branch freeze. If no separate frozen names exist, use:

```text
phase5-model-1
phase5-model-2
phase5-model-3
phase5-model-4
phase5-evidence-consolidation
```

Each model branch accepts generated evidence only for its mapped model.

### No Dynamic Branch Naming During Official Runs

The notebook receives the expected branch from frozen configuration. It may not create a new arbitrary branch because a push failed.

## 4.2 Release Tags

Create immutable annotated tags after each readiness milestone:

```text
phase5-infra-alpha
phase5-infra-locally-verified
phase5-kaggle-nonofficial-verified
phase5-official-source-v1
phase5-dataset-<dataset-version>-complete
```

The official source tag must point to the exact source commit used by Gate 0.

## 4.3 Branch Protection

Configure where available:

- no force push;
- no branch deletion;
- pull-request review for source branches;
- required CI status checks;
- evidence branch pushes allowed only for the checkpoint identity;
- source directories protected against Kaggle checkpoint commits;
- signed commits optional, but hash verification remains mandatory.

## 4.4 CI Workflows

Codex must create:

```text
.github/workflows/phase5-source-ci.yml
.github/workflows/phase5-freeze-guard.yml
.github/workflows/phase5-evidence-integrity.yml
```

### `phase5-source-ci.yml`

Runs on source pull requests:

- formatting and lint;
- type checks;
- unit tests;
- integration tests that do not load real models;
- schema tests;
- grader golden-vector tests;
- state-machine tests;
- checkpoint/resume tests;
- secret scan;
- forbidden-analysis lint.

### `phase5-freeze-guard.yml`

Fails if a pull request changes frozen Phase 4/4.5 artifacts without an explicitly authorized upstream amendment marker.

### `phase5-evidence-integrity.yml`

Runs on model/evidence branch pushes:

- validates committed checkpoint manifest;
- validates accepted rows against frozen schema;
- verifies references included in the checkpoint;
- checks no source path changed;
- checks no duplicate accepted target appears;
- checks D1 invariant;
- checks utility null semantics;
- does not compute or display ASR.

## 4.5 Checkpoint Push Allowlist

The Kaggle sync command may stage only paths such as:

```text
phase5/runs/<model>/
phase5/attempts/
phase5/manifests/run_manifests/
phase5/manifests/batch_manifests/
phase5/validation/batch_validation_reports/
phase5/checkpoints/
phase5/reports/<model>-operational-progress.*
phase5/external_artifacts/
```

It must not stage:

```text
phase5/runtime/
phase5/scripts/
phase5/configs/
phase5/kaggle/
phase5/tests/
phase4/
phase4_5/
AGENTS.md
.github/
requirements*.*
pyproject.toml
```

A staged path outside the allowlist aborts synchronization.

## 4.6 GitHub Authentication Design

Use separate credentials:

```text
GITHUB_READ_TOKEN_PHASE5   — only if the repository is private
GITHUB_WRITE_TOKEN_PHASE5  — fine-grained, repository-scoped, contents write
```

Store credentials only in Kaggle Secrets.

Rules:

- token value is never placed in a notebook cell;
- token is never inserted permanently into `.git/config`;
- token is retrieved only after official seal closure;
- token is passed through an ephemeral environment/askpass mechanism;
- shell tracing is disabled;
- token environment variables are deleted after push;
- temporary credential helpers are removed;
- logs redact URLs and headers;
- token has an expiration date and repository-only scope.

## 4.7 Safe Push Transaction

The repository sync script performs:

```text
1. assert official seal is CLOSED
2. assert no trial subprocess is running
3. validate finalized batch
4. validate staged-path allowlist
5. verify source hash equals official source hash
6. retrieve write token
7. git fetch origin <evidence-branch>
8. compare remote HEAD with expected_remote_head from run manifest
9. abort on unexpected divergence
10. stage only allowlisted files
11. create deterministic checkpoint commit
12. push without force
13. read remote branch SHA
14. verify remote SHA equals local commit SHA
15. write sync receipt
16. remove credential material and credential helper
17. mark sync barrier CLOSED
18. reverify official source hash, frozen artifacts, runtime config, and remote checkpoint head
19. either:
    a. create a new seal epoch and resume the next contiguous frozen batch; or
    b. finalize the Kaggle session when the safety horizon is near
```

Forbidden:

```text
git push --force
git reset --hard against remote divergence
git pull --rebase during official checkpoint sync
automatic merge conflict resolution
source-code staging
continuing official trials while credentials or synchronization state remain active
pulling or merging source changes between seal epochs
```

## 4.8 Commit Message for Checkpoints

```text
phase5-checkpoint(<model>): <dataset> <run-id> <batch-id>

Workload: <core|defense|utility>
Frozen rows: <start>..<end>
Accepted finalized: <n>
Invalid attempts preserved: <n>
Orphan attempts preserved: <n>
Batch manifest: <sha256>
Source commit: <sha>
```

No outcome counts by taxonomy appear in checkpoint messages.

---

# 5. Final Repository Structure

```text
.
├── AGENTS.md
├── .codex/
│   └── skills/
│       └── phase5-verified-implementation/
│           └── SKILL.md
├── .github/
│   └── workflows/
│       ├── phase5-source-ci.yml
│       ├── phase5-freeze-guard.yml
│       └── phase5-evidence-integrity.yml
├── phase4/                         # read-only frozen source
├── phase4_5/                       # read-only completed GO evidence
├── phase5/
│   ├── AGENTS.md
│   ├── README.md
│   ├── cli.py
│   ├── __main__.py
│   ├── configs/
│   │   ├── dataset_version.yaml
│   │   ├── runtime_operational_config.yaml
│   │   ├── upstream_artifact_registry.json
│   │   ├── per_model_runtime_assignment.yaml
│   │   ├── sync_allowlist.yaml
│   │   └── qa_sampling_plan.json
│   ├── domain/
│   │   ├── identifiers.py
│   │   ├── models.py
│   │   ├── enums.py
│   │   ├── errors.py
│   │   └── invariants.py
│   ├── gate0/
│   │   ├── verifier.py
│   │   ├── artifact_registry.py
│   │   ├── hash_verifier.py
│   │   ├── queue_verifier.py
│   │   └── verdict_parser.py
│   ├── runtime/
│   │   ├── AGENTS.md
│   │   ├── session.py
│   │   ├── seal.py
│   │   ├── mcp_server_launcher.py
│   │   ├── reset_controller.py
│   │   ├── prompt_compiler.py
│   │   ├── token_budget.py
│   │   ├── model_backend.py
│   │   ├── agent_loop.py
│   │   ├── parser_adapter.py
│   │   ├── tool_dispatch.py
│   │   └── resource_monitor.py
│   ├── evidence/
│   │   ├── event_writer.py
│   │   ├── artifact_writer.py
│   │   ├── lineage_store.py
│   │   ├── trial_materializer.py
│   │   ├── manifest_builder.py
│   │   └── reference_verifier.py
│   ├── grading/
│   │   ├── frozen_grader_adapter.py
│   │   ├── grader_evidence.py
│   │   └── tid_adapter.py
│   ├── queues/
│   │   ├── frozen_queue_loader.py
│   │   ├── batch_partitioner.py
│   │   ├── pending_resolver.py
│   │   └── completeness.py
│   ├── sync/
│   │   ├── github_checkpoint.py
│   │   ├── credential_scope.py
│   │   ├── path_allowlist.py
│   │   └── sync_receipt.py
│   ├── kaggle/
│   │   ├── AGENTS.md
│   │   ├── phase5_runner.ipynb
│   │   ├── bootstrap.py
│   │   ├── run_session.py
│   │   ├── finalize_session.py
│   │   └── sync_and_terminate.py
│   ├── scripts/
│   │   ├── AGENTS.md
│   │   └── compatibility_wrappers.py
│   ├── audit/
│   │   ├── qa_sampler.py
│   │   ├── targeted_census.py
│   │   └── review_registry.py
│   ├── validation/
│   │   ├── protocol_lint.py
│   │   ├── schema_validation.py
│   │   ├── batch_validation.py
│   │   ├── phase_validation.py
│   │   └── forbidden_analysis_lint.py
│   ├── tests/
│   │   ├── AGENTS.md
│   │   ├── unit/
│   │   ├── integration/
│   │   ├── golden/
│   │   ├── fault_injection/
│   │   └── fixtures/
│   ├── implementation/
│   │   ├── tasks/
│   │   ├── prompts/
│   │   ├── reports/
│   │   └── audits/
│   ├── attempts/
│   ├── runs/
│   ├── checkpoints/
│   ├── manifests/
│   ├── external_artifacts/
│   ├── reports/
│   └── handoff/
└── pyproject.toml
```

Existing repository naming may be adapted, but responsibilities must remain separated.

---

# 6. Unified Phase 5 CLI

## 6.1 Single Entry Point

All local and Kaggle behavior must be reachable through:

```bash
python -m phase5 <command>
```

The notebook must not call internal Python functions directly except through this public CLI or a single tested API wrapper.

## 6.2 Required Commands

```bash
python -m phase5 gate0 --strict

python -m phase5 verify-runtime \
  --model-slot M1 \
  --report phase5/validation/session_preflight_reports/<run>.json

python -m phase5 prepare-dataset \
  --dataset-config phase5/configs/dataset_version.yaml

python -m phase5 partition-batches \
  --manifest phase5/manifests/batch_partition_manifest.json

python -m phase5 session-open \
  --model-slot M1 \
  --batch-id <batch-id>

python -m phase5 session-seal \
  --run-id <run-id>

python -m phase5 run-batch \
  --run-id <run-id> \
  --batch-id <batch-id>

python -m phase5 finalize-batch \
  --run-id <run-id> \
  --batch-id <batch-id>

python -m phase5 session-close-seal \
  --run-id <run-id>

python -m phase5 checkpoint-status \
  --model-slot M1

python -m phase5 sync-github \
  --run-id <run-id> \
  --batch-id <batch-id> \
  --branch <frozen-evidence-branch>

python -m phase5 resume-plan \
  --model-slot M1

python -m phase5 validate-batch \
  --batch-id <batch-id> \
  --strict

python -m phase5 validate-phase \
  --strict

python -m phase5 generate-qa-sample

python -m phase5 build-phase6-handoff
```

## 6.3 Command Safety Invariants

- `run-batch` requires `SEALED`.
- `sync-github` requires `CLOSED_AFTER_FINALIZATION`.
- `sync-github` changes session state to `UNSEALED_SYNCED`.
- `run-batch` refuses in `UNSEALED_SYNCED`.
- `session-reverify` is required after every sync and must prove the source/frozen hashes are unchanged.
- `session-seal` may transition `REVERIFIED_AFTER_SYNC` to a new `SEALED` epoch.
- if re-verification fails, the session terminates and no further official row is dispatched.
- `session-seal` refuses if a Git write credential exists in the process environment.
- `sync-github` refuses if a model backend or MCP trial process is running.
- every command writes a machine-readable report;
- every non-zero exit has a stable error code.

## 6.4 Stable Exit Codes

Example categories:

```text
0   success
10  Gate 0 failure
20  frozen artifact/hash failure
30  runtime mismatch
40  token/protocol defect
50  infrastructure-invalid attempt
60  reset failure
70  schema/invariant failure
80  synchronization safety failure
90  dataset contamination/quarantine
```

Exact mappings must be documented and tested.

---

# 7. Kaggle Notebook Design

## 7.1 Notebook Rule

`phase5/kaggle/phase5_runner.ipynb` is a user interface, not an implementation.

It must contain:

- markdown instructions;
- parameter cells;
- calls to repository scripts;
- concise operational status;
- no duplicated grader, parser, prompt, queue, or schema logic.

## 7.2 Notebook Parameter Cell

Required user-set values:

```python
REPO_URL = "..."
SOURCE_TAG_OR_COMMIT = "..."
MODEL_SLOT = "M1"
EVIDENCE_BRANCH = "..."
RUN_UNTIL_SAFETY_HORIZON = True
OPTIONAL_MAX_BATCHES = None
REMOTE_CHECKPOINT_EVERY_ACCEPTED = 500
SYNC_AFTER_CHECKPOINT_BARRIER = True
```

The notebook resolves model identity and runtime configuration from frozen files, not from editable notebook strings.

## 7.3 Notebook Cell Order

### Cell 1 — Environment Identity

Display:

- Kaggle runtime identity;
- Python/CUDA/GPU;
- notebook commit/template hash;
- UTC time.

No secret retrieval.

### Cell 2 — Clone and Checkout

- clone the repository;
- checkout the expected evidence branch or create a local tracking checkout from the authorized base;
- verify exact official source tag/commit;
- verify common-source hash;
- abort on dirty or divergent source.

For a private repository, use the read-only token only.

### Cell 3 — Preparation Mode

- install exact pinned dependencies if the Phase 4.5 runtime permits;
- verify installed lock digest;
- attach/locate frozen model assets;
- run Gate 0;
- run runtime verification;
- run non-official canary;
- build resume plan.

### Cell 4 — Build Model Campaign Plan

- read the frozen partition manifest;
- calculate all pending contiguous batches for the selected model;
- read Phase 4.5 measured timing and invalid-attempt rates;
- calculate the safe session capacity;
- select as many contiguous batches as fit before the safety horizon;
- show only operational metadata and projected completion time;
- do not display taxonomy outcomes.

### Cell 5 — Open and Seal the First Epoch

- create one Kaggle `run_id`;
- create `seal_epoch=1`;
- start MCP/backend;
- verify reset;
- verify no Git write token in the trial-process environment;
- activate the approved sealed network policy;
- seal.

### Cell 6 — Execute the Unified Model Campaign

Call only:

```bash
python -m phase5 run-campaign   --run-id <run-id>   --model-slot <model>   --until-safety-horizon
```

The unified command loops through many already-frozen contiguous batches. It finalizes and hash-validates every batch internally. It never recreates, reshuffles, or merges the three scientific queues.

### Cell 7 — Optional Remote Checkpoint Barrier

When the predeclared accepted-trial threshold, finalized-batch threshold, or time threshold is reached:

- finish the active attempt;
- finalize every completed batch;
- reset and stop MCP/model trial processes;
- close the current seal epoch;
- retrieve the write credential;
- push only finalized allowlisted checkpoint artifacts;
- verify the remote commit;
- purge all credential state;
- reverify source commit, common-source hash, frozen hashes, runtime config, and checkpoint head;
- increment `seal_epoch`;
- re-start and revalidate MCP/model processes;
- re-seal and return to Cell 6 if the safety horizon still permits.

The checkpoint threshold is operational and frozen before official dispatch. It must not depend on observed outcomes.

### Cell 8 — Final Session Closure and Last Sync

- stop accepting new trials at the safety horizon;
- finish or preserve the active attempt correctly;
- finalize all completed batches;
- reset and stop trial processes;
- close the seal;
- perform the final allowlisted GitHub synchronization;
- verify the remote SHA;
- purge credentials;
- finalize the run manifest.

### Cell 9 — Campaign/Resume Report

Display:

- run ID and seal epochs;
- model slot;
- finalized batch range;
- accepted finalized count;
- invalid/orphan counts;
- local and remote commits;
- manifest hashes;
- remaining pending batches;
- whether the model campaign completed or needs another Kaggle session.

## 7.4 Kaggle Session Granularity

The default official granularity is:

```text
one long unified model campaign per Kaggle session
```

A batch is an integrity and recovery unit, not a Kaggle-session unit. The runner should process as many contiguous frozen batches as fit before the measured safety horizon.

Preferred hierarchy:

```text
Target: 1 Kaggle session per model
Fallback: multiple sessions per model only when measured runtime exceeds the safe session window
Never: 1 Kaggle session per small batch
```

If the frozen operational batch size is 50 rows, Phase 5 contains 204 batch units, but it must not create 204 Kaggle sessions. Each model has 2,550 accepted targets and, at 50 rows per batch, 51 batch units. The unified runner should attempt to process all 51 batches for that model in one session when the timing probe proves that it fits.

## 7.5 Kaggle Output Strategy

At session finalization:

- compact logs/manifests are prepared for Git;
- large raw evidence is compressed into content-addressed archives;
- archive hash/index is committed;
- archive itself is retained in the approved large-artifact location;
- no artifact is considered saved until its local archive and hash index pass verification.

---

# 8. Implementation Work Breakdown

Each sub-phase is a separate Codex task group with its own branch checkpoint and audit.

---

## I0 — Repository Reality Audit and Input Reconciliation

### Objective

Establish the actual repository state before writing Phase 5 code.

### Codex Actions

- inventory Phase 4 and Phase 4.5 artifacts;
- map real paths to the paths named in the execution plan;
- inspect the frozen schema;
- inspect model-set freeze;
- inspect trial-order files and counts;
- inspect execution manifest for loop controls;
- inspect completed Phase 4.5 runtime, reset, schema, and checkpoint evidence;
- identify existing reusable code from Phase 4.5;
- produce a gap map.

### Deliverables

```text
phase5/implementation/reports/I0_repository_reality_audit.md
phase5/configs/upstream_artifact_registry.json
phase5/implementation/reports/I0_path_reconciliation.json
```

### Validation

- every required upstream artifact mapped;
- no duplicate or ambiguous authoritative file;
- queue totals independently recalculated;
- required state-machine settings located;
- no code written beyond registry/report scaffolding.

### Exit Gate

```text
I0 VERDICT: GO / BLOCKED_UPSTREAM_ARTIFACT_GAP
```

No later implementation starts on a blocked verdict.

---

## I1 — Codex Governance and Repository Scaffold

### Objective

Create the agentic-development controls and directory skeleton.

### Codex Actions

- create all `AGENTS.md` files;
- create reusable Codex skill;
- create task packet schema;
- create implementation report template;
- create repository directories;
- configure Python package and test runner;
- create freeze-guard and secret-scan hooks.

### Tests

- Codex instruction discovery test/documented check;
- path-freeze lint test;
- secret-pattern lint test;
- package import smoke test.

### Exit Gate

- CI runs;
- frozen paths are protected;
- source package imports;
- task template is usable.

---

## I2 — Domain Types, Configuration Loading, and Protocol Invariants

### Objective

Build strongly validated internal representations without redefining frozen science.

### Components

```text
phase5/domain/
phase5/configs/
```

### Codex Actions

- implement typed IDs and enums;
- implement immutable configuration loaders;
- implement exact field-name checks;
- implement D1 exploit-class invariant;
- implement utility null-semantic invariant;
- implement accepted-attempt uniqueness;
- implement session-state enum;
- implement stable error classes and exit codes.

### Tests

- valid/invalid IDs;
- prohibited field aliases;
- D1 violation;
- utility payload-hash violation;
- duplicate accepted target;
- unknown enum;
- missing frozen field fails closed.

### Exit Gate

100% invariant test pass.

---

## I3 — Gate 0 and Frozen Artifact Registry

### Objective

Implement strict entry authorization.

### Components

```text
phase5/gate0/
python -m phase5 gate0 --strict
```

### Codex Actions

- parse Phase 4 and Phase 4.5 verdicts;
- verify cryptographic lock;
- verify schema/grader/TID/model hashes;
- verify source commit;
- verify real queue counts/cells;
- verify Phase 4.5 runtime design;
- generate JSON and Markdown reports;
- distinguish warnings from blockers.

### Fault Tests

- one-byte artifact mutation;
- missing GO file;
- false GO wording;
- duplicate trial row;
- queue count mismatch;
- unknown model digest;
- schema hash mismatch;
- dirty checkout;
- wrong Kaggle runtime flag.

### Exit Gate

All negative fixtures fail for the correct reason; canonical fixture passes.

---

## I4 — Frozen Queue Loader, Batch Partition, and Resume Resolver

### Objective

Load exact rows and create immutable operational batches without reordering.

### Codex Actions

- implement queue adapters for all three frozen files;
- validate row-level hashes/references;
- preserve queue separation;
- partition only contiguous ranges;
- build deterministic batch IDs;
- hash partition manifest;
- calculate pending/accepted/orphan status;
- implement resume plan.

### Tests

- no concatenation;
- no reorder;
- same inputs produce same partition;
- changed batch size after freeze is rejected;
- accepted trial not selected again;
- orphan target selected with new attempt index;
- divergent checkpoint histories fail.

### Exit Gate

Partition manifest exactly reconciles all frozen rows.

---

## I5 — Write-Ahead Event Store, Raw Artifacts, and Lineage

### Objective

Make every dispatch durable and recoverable.

### Codex Actions

- implement append-only JSONL event writer;
- flush and `fsync`;
- implement artifact hashing;
- implement per-attempt directory;
- implement lineage CSV/transaction-safe store;
- implement orphan discovery;
- implement idempotent finalization;
- implement crash-safe temporary-to-final rename.

### Fault Tests

Inject process termination:

- after `PREPARED`;
- after `DISPATCHED`;
- after model output;
- after tool event;
- after reset;
- before final row;
- during manifest write.

### Required Results

- dispatched but unfinished attempt becomes orphan;
- no event is overwritten;
- no accepted row duplicates;
- replacement gets a new attempt ID;
- partially written manifests are detected.

---

## I6 — FastMCP Process, Workspace Isolation, and Reset Controller

### Objective

Implement the Kaggle-native process boundary and reset invariants.

### Codex Actions

- reuse the Phase 4.5-validated FastMCP launcher;
- bind only to loopback;
- create per-attempt workspace;
- copy read-only fixtures;
- restrict writes to approved mock/evidence roots;
- implement internal reset control;
- verify reset absent from discovery;
- verify reset is non-dispatchable;
- implement server-restart fallback;
- capture pre/post snapshots.

### Tests

- port binding check;
- discovery does not expose reset;
- direct MCP reset call is rejected;
- sentinel state clears;
- source fixtures remain unchanged;
- one attempt cannot read another workspace;
- server crash and restart;
- repeated reset failure quarantines session.

### Exit Gate

Full reset suite passes repeatedly under stress.

---

## I7 — Prompt Compiler and Per-Turn Token Budget

### Objective

Compile exact frozen contexts and enforce token limits on every turn.

### Codex Actions

- load frozen system/task/schema/surface/payload artifacts;
- preserve bytes and encoding;
- compile exact model-specific serialization;
- record component counts;
- use exact frozen tokenizer;
- enforce 3,584 input and 512 output reserve;
- classify overflow according to the execution plan;
- prohibit truncation and summarization.

### Tests

- golden prompt byte/hash fixtures;
- initial over-budget defect;
- expected tool result overflow;
- model-loop overflow;
- no history deletion;
- tokenizer mismatch;
- payload whitespace preservation;
- utility null payload behavior.

### Exit Gate

Golden compiled-prompt hashes match Phase 4.5 reference cases.

---

## I8 — Model Backend Adapter and Multi-Turn Agent Loop

### Objective

Implement the exact frozen state machine.

### Codex Actions

- load per-model backend settings;
- verify model/tokenizer/quantization;
- implement session isolation;
- implement turn and tool limits from frozen manifest;
- parse without repair;
- dispatch tools in frozen order;
- reinsert exact tool-result serialization;
- implement all stop conditions;
- classify backend/infrastructure exceptions distinctly;
- emit events for every transition.

### Tests

- deterministic fake backend paths;
- terminal answer;
- one and multiple tool calls;
- malformed call;
- hallucinated tool;
- repeated loop;
- max turns;
- per-turn timeout;
- tool timeout;
- whole-trial timeout;
- backend crash;
- model-attributable overflow;
- no KV/session reuse.

### Exit Gate

State-transition coverage is complete and no untested terminal path remains.

---

## I9 — Frozen Grader, TID Adapter, and Trial Materialization

### Objective

Wire the already frozen grader and schema without reinterpretation.

### Codex Actions

- import/adapter-wrap frozen grader;
- verify grader hash;
- execute all frozen vectors;
- create structured predicate evidence;
- calculate TID on logical IDs;
- materialize exact frozen schema;
- resolve all evidence references;
- validate exactly one primary outcome;
- validate acceptance flags.

### Tests

- all frozen positive/negative vectors;
- D1 impossibility;
- single-tool hijack;
- multi-tool attack success;
- critical source-to-sink;
- reset/infrastructure precedence;
- utility row;
- TID multiple accepted sequences;
- TID range;
- prohibited aliases;
- missing evidence reference.

### Exit Gate

100% golden-vector and schema test pass.

---

## I10 — Batch Finalization, Manifests, and Phase-Safe Checkpoints

### Objective

Finalize evidence atomically before synchronization.

### Codex Actions

- validate every attempt in the batch;
- build accepted-row JSONL;
- reconcile cell counts;
- build batch manifest;
- build run manifest;
- build external-artifact index;
- validate hashes;
- close official seal;
- mark batch `FINALIZED_NOT_SYNCED`.

### Fault Tests

- missing raw artifact;
- hash mismatch;
- duplicate accepted row;
- unresolved orphan;
- incomplete attempt;
- partial archive;
- manifest write interruption.

### Exit Gate

No batch reaches `FINALIZED_NOT_SYNCED` unless all validation passes.

---

## I11 — Safe GitHub Checkpoint Synchronizer

### Objective

Implement the user's periodic repository-saving workflow without violating sealed execution.

### Codex Actions

- implement sync state guard;
- implement path allowlist;
- verify no trial processes;
- retrieve write token only in sync command;
- use ephemeral credential helper;
- fetch and compare expected remote head;
- stage allowlisted files;
- commit deterministic metadata;
- push without force;
- verify remote SHA;
- write sync receipt;
- remove credential state;
- mark the synchronization barrier complete and either reverify/re-seal or finalize the session.

### Fault Tests

- sync attempted while sealed;
- write token present before seal;
- source path staged;
- unexpected remote divergence;
- expired/invalid token;
- push rejected;
- remote SHA mismatch;
- token accidentally present in log;
- attempted official continuation after sync without credential purge, full re-verification, and a new seal epoch.

### Exit Gate

Every unsafe scenario fails closed without corrupting local evidence.

---

## I12 — Thin Kaggle Notebook and Session Wrapper

### Objective

Create the notebook entirely from repository-backed commands.

### Codex Actions

- generate notebook cells in the required order;
- add parameter validation;
- prevent manual editing of scientific parameters;
- call the unified CLI;
- display only operational status;
- implement sync-barrier, re-verification, and seal-epoch behavior;
- write operator guide.

### Deliverables

```text
phase5/kaggle/phase5_runner.ipynb
phase5/kaggle/README.md
phase5/kaggle/operator_runbook.md
```

### Validation

- notebook executes from top to bottom against fake backend;
- notebook can resume after simulated interruption;
- notebook contains no grader/prompt/scientific logic;
- no output-peeking table is displayed;
- secret is never rendered;
- continuation after sync is blocked until credential purge, full re-verification, and a new seal epoch pass.

---

## I13 — Local End-to-End Simulation

### Objective

Validate the complete pipeline without official models or official Phase 5 evidence.

### Test Matrix

Use a deterministic fake backend to exercise:

- benign terminal success;
- benign task failure;
- single unauthorized tool;
- incomplete multi-tool path;
- completed attack path;
- critical source-to-sink path;
- malformed output;
- model loop;
- infrastructure crash;
- reset failure;
- orphan/replacement;
- Git sync rejection and success.

### Required Outputs

```text
phase5/implementation/reports/I13_local_e2e_report.md
phase5/implementation/reports/I13_fault_injection_matrix.csv
```

### Exit Gate

All state, evidence, rerun, schema, and sync paths pass locally.

---

## I14 — Kaggle Non-Official Infrastructure Verification

### Objective

Confirm the actual Kaggle environment before official dispatch.

This is engineering validation only and must be marked non-official.

### Sequence

1. clone the candidate official source commit;
2. verify runtime and dependency pins;
3. load each frozen model;
4. verify tokenizer/backend/digest;
5. run non-official synthetic canary;
6. test FastMCP loopback/reset;
7. test per-turn tokenization;
8. test write-ahead durability;
9. simulate notebook interruption and resume;
10. finalize a synthetic batch;
11. close seal;
12. sync synthetic checkpoint to a non-official test branch;
13. verify remote SHA;
14. terminate session.

### Exit Gate

```text
KAGGLE IMPLEMENTATION VERDICT: GO FOR FINAL READINESS AUDIT
```

Synthetic artifacts must never enter official branches or counts.

---

## I15 — Independent Phase 5 Implementation Readiness Audit

### Objective

Audit implementation against every requirement of Phase 5 v3.2 before official evidence.

### Auditor Must Verify

- source commit and tag;
- frozen-artifact mapping;
- Gate 0;
- queue counts;
- state machine;
- per-turn token budget;
- reset controls;
- raw evidence;
- schema/grader/TID;
- rerun semantics;
- orphan preservation;
- Git synchronization separation;
- token handling;
- no outcome peeking;
- notebook thinness;
- CI and branch guards;
- Kaggle non-official evidence.

### Verdicts

```text
GO TO OFFICIAL PHASE 5
TARGETED REVISE AND RE-AUDIT
RETURN TO PHASE 4/4.5
NO-GO
```

Official trials require explicit `GO TO OFFICIAL PHASE 5`.

---

## I16 — Official Source Freeze

### Objective

Create the exact immutable source used for official execution.

### Actions

- merge all approved implementation changes;
- run full CI;
- generate common-source hash;
- update upstream registry;
- generate official source manifest;
- create annotated tag `phase5-official-source-v1`;
- record tag and commit in dataset-version config;
- prohibit further source edits for that dataset version.

Any later source change follows the contamination rules.

---

## I17 — Official Kaggle Execution

### Per-Session Procedure

1. start fresh Kaggle session;
2. clone evidence branch;
3. verify official source tag/commit;
4. verify checkpoint remote head;
5. run Gate 0;
6. verify model/runtime;
7. determine next frozen pending batch;
8. run canary;
9. open and seal session;
10. execute unified `run-batch`;
11. finalize and validate;
12. close seal;
13. retrieve write token;
14. push finalized checkpoint;
15. verify remote SHA;
16. terminate session.

### Queue Order

Follow the exact frozen execution/batch order. Do not choose conditions based on observed results.

### Completion Target

```text
core:    5,400 accepted valid
defense: 2,400 accepted valid
utility: 2,400 accepted valid
total:  10,200 accepted valid
```

---

## I18 — Final QA, Validation, and Phase 6 Handoff

### Actions

- lock accepted dataset;
- generate exact 1,530-row stratified random sample;
- generate targeted census;
- conduct review/adjudication;
- verify all run/batch/master manifests;
- verify all accepted counts;
- verify all invalid/orphan lineage;
- generate model completion reports;
- generate final Phase 5 verification;
- generate Phase 5 decision;
- build Phase 6 handoff manifest;
- tag the completed dataset.

---


# 8A. Kaggle Run-Count Planning and Unified Campaign Sizing

## 8A.1 Fixed Trial Allocation

The frozen Phase 5 total is:

```text
10,200 accepted valid trials
4 models
2,550 accepted valid trials per model

Per model:
core adversarial:    1,350
defense adversarial:   600
clean utility:         600
total:               2,550
```

If the operational batch size is 50 accepted rows, this produces:

```text
51 batch units per model
204 batch units overall
```

These are checkpoint/integrity units, not Kaggle-session counts.

## 8A.2 Exact Run-Count Formula

The implementation must read the Phase 4.5 timing report and calculate model-specific requirements.

For model `m` and workload/cell group `g`:

```text
T_m = Σ_g [ N_mg × t95_mg / (1 - r_invalid_mg) ] + fixed_model_overhead_m
```

where:

- `N_mg` is the frozen accepted target;
- `t95_mg` is the measured Phase 4.5 end-to-end P95 time per attempt, including model turns, tool calls, reset, grading, evidence writes, and batch-amortized finalization;
- `r_invalid_mg` is the measured infrastructure/reset-invalid fraction;
- `fixed_model_overhead_m` includes model loading and session preflight.

Let:

```text
H_safe = configured safe execution hours in one Kaggle session
```

Then:

```text
sessions_m = ceil(T_m / H_safe)
total_official_kaggle_sessions = Σ_m sessions_m
```

`H_safe` must be imported from validated runtime configuration. For planning against a nine-hour platform maximum, a conservative default is 7.5 hours of trial execution, leaving time for setup, model loading, finalization, and synchronization.

## 8A.3 Scenario Table

Using 2,550 trials per model and a 7.5-hour safe execution window:

| Effective end-to-end seconds per accepted trial | Approx. hours per model | Kaggle sessions per model | Total official sessions |
|---:|---:|---:|---:|
| 5 | 3.54 | 1 | 4 |
| 8 | 5.67 | 1 | 4 |
| 10 | 7.08 | 1 | 4 |
| 12 | 8.50 | 2 | 8 |
| 20 | 14.17 | 2 | 8 |
| 30 | 21.25 | 3 | 12 |
| 60 | 42.50 | 6 | 24 |

One session per model is feasible only when effective end-to-end trial time is approximately 10.6 seconds or less under a 7.5-hour safe window.

## 8A.4 Required Planning Script

Codex must implement:

```bash
python -m phase5 plan-kaggle-runs \
  --timing-report <phase45-timing-report> \
  --safe-session-hours <validated-value> \
  --output phase5/validation/kaggle_run_plan.json
```

The report must include:

```text
per-model and per-workload P50/P95 trial times
model-load/preflight overhead
observed invalid-attempt rate
safe session capacity
batches per session
projected sessions per model
projected total sessions
projected weekly GPU hours
checkpoint barrier interval
sensitivity analysis
```

The run plan is operational only. It cannot change queue ordering, accepted targets, model allocation, or scientific cells.

## 8A.5 Recommended Long-Run Policy

Use:

```text
one unified script invocation per Kaggle notebook session
one model loaded per session
many contiguous finalized batches per session
local durable checkpoint after every event and batch
remote Git checkpoint every 500 accepted trials or 90 minutes, whichever occurs first
final remote checkpoint before the safety horizon
```

The exact remote-checkpoint threshold must be frozen before official execution and may be reduced if Phase 4.5 interruption testing shows unacceptable loss risk. It must not be changed in response to observed model outcomes.


# 9. Test Architecture

## 9.1 Unit Tests

Cover:

- identifiers;
- hashes;
- verdict parsing;
- immutable config;
- queue row adapters;
- batch ID grammar;
- event serialization;
- token limits;
- grader adapters;
- TID;
- path allowlist;
- session-state guards.

## 9.2 Golden Tests

Use frozen or non-official reference fixtures for:

- compiled prompt bytes;
- schema rows;
- grader predicates;
- tool-result serialization;
- batch manifests;
- run manifests;
- sync receipts.

Golden fixtures must be hash-bound and reviewed.

## 9.3 Integration Tests

Test:

- Gate 0 to finalized fake trial;
- FastMCP launch/reset;
- multi-turn fake model;
- evidence and row materialization;
- batch validation;
- resume planning;
- Git sync against a temporary bare repository.

## 9.4 Fault-Injection Tests

Required injected faults:

```text
kernel/process termination
backend crash
OOM simulation
MCP crash
tool timeout
model timeout
whole-trial timeout
reset sentinel survival
event-log partial write
artifact corruption
manifest corruption
disk-full simulation
remote branch divergence
expired Git token
push rejection
schema mismatch
wrong model digest
wrong tokenizer
initial token overflow
history overflow
```

## 9.5 Property/Invariance Tests

Examples:

- a finalized target has at most one accepted attempt;
- all dispatched attempts are discoverable;
- reruns always have greater attempt index;
- batch partition preserves queue order;
- TID is always in range;
- D1 never finalizes as exploit class;
- utility rows always have null payload hashes;
- source hash does not change during evidence commits;
- synchronization is impossible in sealed state;
- execution is impossible during sync state and before post-sync re-verification/re-seal.

## 9.6 Security Tests

- secret scan;
- log redaction;
- token not written to config;
- reset not exposed;
- loopback-only listener;
- source write protection;
- path traversal rejection;
- archive extraction safety;
- no real network sink;
- no shell injection through IDs/config values.

---

# 10. Validation Layers

## Layer 1 — Static Validation

- formatting;
- lint;
- types;
- dependency lock;
- secret scan;
- forbidden path changes;
- forbidden analysis code.

## Layer 2 — Unit and Golden Validation

- all modules;
- all grader vectors;
- all schema fixtures;
- all invariant fixtures.

## Layer 3 — Local Integration

- fake backend;
- local MCP;
- crash/resume;
- local bare-Git checkpoint.

## Layer 4 — Kaggle Non-Official Validation

- actual runtime;
- actual model loading;
- actual notebook;
- actual reset;
- actual checkpoint sync to test branch.

## Layer 5 — Independent Readiness Audit

- requirement-by-requirement audit;
- no self-certification.

## Layer 6 — Per-Session Official Preflight

- Gate 0;
- source/runtime/model;
- reset;
- schema/grader;
- checkpoint head.

## Layer 7 — Per-Batch Finalization

- rows;
- evidence;
- lineage;
- hashes;
- counts;
- manifest.

## Layer 8 — GitHub CI After Checkpoint Push

- no source changes;
- checkpoint integrity;
- schema/invariants;
- no outcome analysis.

## Layer 9 — End-of-Phase Validation

- all 10,200 accepted targets;
- QA;
- master manifest;
- Phase 6 handoff.

---

# 11. Checkpoint Data Contract

Each pushed checkpoint directory must contain:

```text
checkpoint.json
batch_manifest.json
run_manifest.json
accepted_rows.jsonl
attempt_events_index.json
attempt_lineage_delta.csv
orphan_registry_delta.jsonl
invalid_attempt_index.jsonl
evidence_hash_index.jsonl
external_archive_index.json
batch_validation_report.json
sync_receipt.json
```

`checkpoint.json` minimum fields:

```json
{
  "dataset_version": "string",
  "model_slot": "M1",
  "workload": "core|defense|utility",
  "run_id": "string",
  "batch_id": "string",
  "source_commit": "sha",
  "phase4_lock_hash": "sha256",
  "phase45_go_hash": "sha256",
  "expected_remote_head_before_push": "sha",
  "accepted_finalized_count": 0,
  "invalid_attempt_count": 0,
  "orphan_attempt_count": 0,
  "batch_manifest_sha256": "sha256",
  "evidence_index_sha256": "sha256",
  "session_seal_closed": true,
  "no_more_official_execution_in_session": true
}
```

No condition-level outcome summary is included.

---

# 12. Resume and Concurrency Policy

## 12.1 One Writer per Model Branch

Only one Kaggle session may write to a model evidence branch at a time.

Use a branch lease file:

```text
phase5/checkpoints/<model>/LEASE.json
```

The lease contains:

- run ID;
- expected branch head;
- acquisition UTC;
- expiration UTC;
- batch ID.

The lease is committed before a long official campaign only through a safe unsealed control step. Simpler initial operation should avoid concurrent sessions entirely.

## 12.2 Resume Source

A post-sync seal epoch or later Kaggle session trusts only:

- remote evidence branch;
- verified checkpoint manifests;
- accepted-row indexes;
- attempt lineage;
- orphan registry;
- frozen partition manifest.

Notebook cell state is never authoritative.

## 12.3 Divergence

If remote branch HEAD differs from the expected checkpoint:

- do not merge automatically;
- do not rebase automatically;
- generate divergence report;
- stop;
- resolve manually outside official execution;
- rerun preflight after resolution.

---

# 13. Large Evidence Preservation

GitHub is not the only byte store for large raw evidence.

## 13.1 GitHub Stores

- compact accepted rows;
- attempt event indexes;
- lineage;
- hashes;
- manifests;
- validation reports;
- archive indexes;
- sync receipts.

## 13.2 External/Content-Addressed Store Holds

- compressed raw prompt/output directories;
- full tool transcripts when large;
- hardware telemetry archives;
- large per-attempt evidence bundles.

Approved storage must follow the Phase 5 execution plan.

## 13.3 Archive Naming

```text
P5ARCH-<dataset>-<model>-<run>-<batch>-<sha16>.tar.zst
```

The archive index contains URI/location, size, SHA-256, included attempt IDs, and retrieval status.

No accepted checkpoint is considered complete if the archive index references an unavailable or unhashed archive.

---

# 14. Operational Dashboard

Allowed display:

```text
model slot
run/batch ID
pending/finalized counts
accepted-valid count
invalid infrastructure count
orphan count
reset-failure count
schema/hash status
maximum observed token count
runtime/resource status
disk usage
time-to-safety-horizon
checkpoint/sync status
```

Prohibited display:

```text
outcome distribution
ASR
Critical Exploit count by condition
model ranking
surface comparison
defense comparison
D3/D5 comparison
p-values
confidence intervals
```

The dashboard queries operational indexes, not outcome analytics.

---

# 15. Implementation Acceptance Matrix Against Phase 5 v3.2

| Execution-Plan Requirement | Implementation Component | Validation |
|---|---|---|
| Gate 0 strict authorization | `phase5/gate0/` | mutation and missing-artifact tests |
| Three separate frozen queues | `phase5/queues/` | order/count reconciliation |
| D1 negative control | domain invariant + grader tests | hard-stop fixture |
| Frozen endpoint/denominator | frozen row materializer only | no Phase 5 inferential code |
| No copy drift | artifact registry/hash verifier | byte mutation tests |
| Dataset/attempt IDs | `domain/identifiers.py` | collision/property tests |
| Kaggle native container | notebook/runtime wrapper | Kaggle preflight report |
| No nested Docker | protocol lint | source scan and runtime check |
| Reset hidden/non-dispatchable | reset controller | discovery and dispatch tests |
| Frozen hardware/backend | runtime verifier | mismatch fixtures |
| Exact queues and order | queue loader | deterministic partition tests |
| Frozen multi-turn loop | `runtime/agent_loop.py` | transition coverage |
| Token check every turn | `runtime/token_budget.py` | overflow fixtures |
| Write-ahead logging | `evidence/event_writer.py` | crash injection |
| Raw evidence | artifact writer | reference/hash tests |
| Frozen schema | materializer/validator | 100% golden schema tests |
| Eight-class taxonomy | frozen grader adapter | full vector suite |
| Logical-ID TID | TID adapter | range and alias tests |
| Rerun governance | lineage/pending resolver | invalid-vs-valid tests |
| Contamination policy | session/dataset registry | quarantine tests |
| Checkpoint/resume | batch/run manifest | interruption simulation |
| No outcome peeking | dashboard + lint | forbidden field scan |
| QA exact 1,530 | QA sampler | deterministic allocation test |
| Hash-bound manifests | manifest builder | recomputation tests |
| Safe Git sync | sync package | sealed-state/divergence tests |
| Source branch drift guard | CI and allowlist | forbidden staging test |
| Completion gates | phase validator | canonical complete fixture |
| Phase 6 handoff | handoff builder | manifest resolution test |

---

# 16. Codex Prompt Template for Each Implementation Task

Store this template in:

```text
phase5/implementation/prompts/task_execution_template.md
```

```markdown
You are implementing Task <TASK_ID> for Phase 5.

Authoritative inputs:
1. Phase 4 frozen artifacts.
2. Phase 4.5 completed GO artifacts.
3. Phase5_Revised_Execution_Plan_v3_2.md.
4. Phase5_Practical_Implementation_Plan_v1_0.md.
5. Repository AGENTS.md files.

You must:
- inspect the repository before editing;
- verify all referenced real paths;
- state any mismatch between the plan and repository;
- modify only the allowed paths in the task packet;
- never modify Phase 4 or Phase 4.5 frozen files;
- never invent a missing scientific setting;
- implement fail-closed behavior;
- add unit, integration, and fault tests required by the task;
- run all assigned validations;
- generate the task implementation report;
- inspect the final diff for unrelated changes and secrets;
- commit only after all acceptance criteria pass.

You must not:
- proceed into another task;
- regenerate scientific artifacts;
- repair model outputs;
- add inferential analysis;
- weaken a failed check to make tests pass;
- claim completion without command output and artifact evidence.

Final response:
1. files changed;
2. tests run and exact results;
3. assumptions resolved from frozen artifacts;
4. unresolved blockers;
5. commit SHA.
```

---

# 17. Codex Independent Audit Template

```markdown
Act as an independent Phase 5 implementation auditor.

Do not trust the builder's summary. Inspect the repository, diff, tests, and generated report directly.

Audit against:
- the exact task packet;
- Phase 5 Revised Execution Plan v3.2.0;
- Phase 5 Practical Implementation Plan v1.0.0;
- frozen Phase 4/4.5 artifacts;
- all applicable AGENTS.md files.

Verify:
- scientific artifacts were not modified;
- missing frozen values were not invented;
- fail-closed behavior exists;
- tests include negative and fault paths;
- implementation cannot silently overwrite attempts;
- implementation does not expose secrets;
- state and synchronization guards are enforced;
- all acceptance criteria are evidenced.

Rerun relevant tests independently.

Return:
- PASS, CONDITIONAL PASS, or FAIL;
- blocking findings;
- non-blocking findings;
- exact evidence and file references;
- required remediation.
```

---

# 18. Final Readiness Checklist

Official execution remains prohibited until all items pass:

## Repository and Governance

- [ ] I0 repository audit passes.
- [ ] All required frozen paths are mapped.
- [ ] Root and subtree `AGENTS.md` files exist.
- [ ] Codex skill and task protocol exist.
- [ ] Source CI, freeze guard, and evidence CI pass.
- [ ] Official source tag and commit are immutable.

## Runtime

- [ ] Gate 0 passes.
- [ ] All four model identities load and verify.
- [ ] Kaggle runtime matches Phase 4.5.
- [ ] No nested Docker dependency exists.
- [ ] FastMCP binds only to loopback.
- [ ] Reset is hidden and non-dispatchable.
- [ ] Reset stress suite passes.
- [ ] Multi-turn loop transition coverage passes.
- [ ] Token budget is checked on every turn.

## Evidence

- [ ] Write-ahead `fsync` test passes.
- [ ] Crash/orphan recovery passes.
- [ ] Raw evidence references resolve.
- [ ] Frozen schema validation is 100%.
- [ ] Grader vectors are 100%.
- [ ] D1 exploit invariant passes.
- [ ] Utility null semantics pass.
- [ ] TID tests pass.

## Kaggle and GitHub

- [ ] Thin notebook passes top-to-bottom.
- [ ] Non-official Kaggle canary passes.
- [ ] Checkpoint/resume passes.
- [ ] Sync cannot run while sealed.
- [ ] Execution cannot resume after sync until credentials are purged and a new seal epoch passes full re-verification.
- [ ] Token never appears in logs/config.
- [ ] Path allowlist blocks source changes.
- [ ] Remote divergence fails closed.
- [ ] Remote commit verification passes.

## Independent Audit

- [ ] Implementation readiness audit issues `GO TO OFFICIAL PHASE 5`.

---

# 19. Practical Operator Workflow

For each official Kaggle model campaign:

```text
A. Open a fresh notebook session.
B. Set only repository/source/model-slot parameters.
C. Clone the correct evidence branch.
D. Verify source tag and remote checkpoint head.
E. Run Gate 0 and runtime preflight.
F. Calculate the safe capacity from the Phase 4.5 timing evidence.
G. Resolve all contiguous pending batches that fit the safety horizon.
H. Run the non-official canary.
I. Create run ID and seal epoch 1.
J. Execute the unified campaign command across many batches.
K. Finalize each batch internally as it completes.
L. At a predeclared remote-checkpoint barrier:
   1. finish the active attempt;
   2. finalize completed batches;
   3. close the seal and stop trial processes;
   4. push allowlisted evidence;
   5. purge credentials;
   6. reverify exact source/frozen hashes;
   7. create the next seal epoch and resume.
M. Stop before the safety horizon.
N. Finalize the session and perform the last sync.
O. Start another Kaggle session only if the selected model still has pending frozen batches.
```

At no point does the operator edit a trial row, payload, prompt, model setting, outcome, or accepted count.

---

# 20. Final Implementation Decision

This implementation plan is complete only when the following final document exists:

```text
phase5/validation/final_implementation_readiness_report.md
```

with:

```text
CODEX IMPLEMENTATION COMPLETE: PASS
LOCAL END-TO-END VALIDATION: PASS
KAGGLE NON-OFFICIAL VALIDATION: PASS
GITHUB CHECKPOINT VALIDATION: PASS
INDEPENDENT IMPLEMENTATION AUDIT: PASS
AUTHORIZED SOURCE TAG:
AUTHORIZED SOURCE COMMIT:
AUTHORIZED DATASET VERSION:
FINAL VERDICT: GO TO OFFICIAL PHASE 5
```

Anything less blocks official evidence collection.

---

# Appendix A — Recommended Implementation Sequence

```text
I0  Repository reality audit
I1  Codex governance and scaffold
I2  Domain types and invariants
I3  Gate 0
I4  Queue/batch/resume
I5  Event/evidence/lineage
I6  MCP/reset/isolation
I7  Prompt/token budget
I8  Backend and agent loop
I9  Grader/TID/schema
I10 Batch finalization/manifests
I11 Safe GitHub sync
I12 Thin Kaggle notebook
I13 Local end-to-end simulation
I14 Kaggle non-official verification
I15 Independent readiness audit
I16 Official source freeze
I17 Official Kaggle execution
I18 QA and Phase 6 handoff
```

Do not combine implementation phases merely to reduce the number of Codex prompts. Each phase exists to keep changes reviewable and defects attributable.

---

# Appendix B — Minimum Per-Task Evidence

Every completed implementation task contributes:

```text
task packet
Codex builder prompt
implementation report
independent audit report
test logs
fault-test logs
diff summary
commit SHA
CI run reference
```

---

# Appendix C — Key Safety Decision

The notebook may clone, execute, finalize, checkpoint, commit, and push as the user proposed, but every synchronization barrier follows:

```text
OFFICIAL EXECUTION SEGMENT
→ FINALIZE COMPLETED BATCHES
→ SEAL CLOSURE
→ TRIAL PROCESS STOP
→ CREDENTIAL RETRIEVAL
→ ALLOWLISTED GIT COMMIT/PUSH
→ REMOTE SHA VERIFICATION
→ CREDENTIAL PURGE
→ SOURCE/FROZEN HASH RE-VERIFICATION
→ NEW SEAL EPOCH
→ NEXT CONTIGUOUS EXECUTION SEGMENT
```

It is never:

```text
execute while credentials are active
or
push and resume without re-verification/re-sealing
or
pull/merge source changes between execution segments
```

This preserves Phase 5 v3.2.0 while allowing one long unified notebook invocation to process many batches and periodically save finalized progress.

---

**End of Phase 5 Practical Implementation Plan — Version 1.1.0**
