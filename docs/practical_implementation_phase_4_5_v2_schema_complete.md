# Practical Implementation Plan — Phase 4.5 Hybrid Local + Kaggle Execution

**Project:** Empirical Evaluation of Privilege Aggregation Vulnerabilities in Edge-Deployed Open-Weight Agents via the Model Context Protocol  
**Document Type:** Revised Practical Phase 4.5 Implementation Guide  
**Version:** 2.0 — Schema-Complete Hybrid Revision  
**Document Status:** Execution-Ready Practical Plan after External Review Reconciliation  
**Phase:** 4.5  
**Execution Design:** Hybrid — GitHub + Local Dry-Run + Kaggle Smoke Test  
**Primary Goal:** Validate the Phase 5 execution pipeline before official adversarial evaluation  
**Important Boundary:** Phase 4.5 is not Phase 5 and does not produce publishable security results  

---

## 0. Revision Integration Note

This Version 2.0 revises the earlier practical Phase 4.5 plan after external consistency review.

The review identified one blocking defect and several reconciliation issues. This version fixes them as follows:

1. **Full frozen-schema mapping is now mandatory.**  
   Phase 4.5 no longer maps only a small subset of renamed fields. `phase45_schema_mapping.yaml` must enumerate every required field in `phase4/configs/phase5_schema_freeze.json`.

2. **Kaggle smoke coverage is expanded.**  
   Kaggle smoke now touches D3, D5, POISON_TD, and POISON_CA so that high-density prompt footprint and both metadata surfaces are actually tested on the final execution platform.

3. **Kaggle-side remaining-model loader checks are added.**  
   Local remaining-model smoke is useful but insufficient if Phase 5 runs on Kaggle. Each frozen model must have at least a Kaggle load/initialization smoke result before Phase 5.

4. **Kaggle quota feasibility is added.**  
   Phase 4.5 must estimate total Phase 5 runtime and produce a checkpoint/resume strategy before declaring readiness.

5. **Original Phase 4.5 branch/scaffold policy is explicitly superseded where necessary.**  
   This practical hybrid plan intentionally expands the original scaffold to support Kaggle execution. The expansion is documented rather than silent.

6. **Canonical verdict/status vocabulary is defined.**  
   Scripts must parse one fixed enum set. Informal or conflicting status labels are prohibited.

7. **Rerun mechanics are restored.**  
   Invalid trials must be preserved and rerun under new IDs that reference the original invalid trial.

8. **Dependency pinning is required before Kaggle execution.**  
   Recording dependency versions after execution is not enough. The environment must be pinned before smoke testing and Phase 5.

---

## 1. Authority and Supersession Statement

This practical plan is an implementation-layer extension of the formal Phase 4.5 specification.

For hybrid execution, this document **supersedes only the original Phase 4.5 specification sections that define branch naming and scaffold layout**, because the original local-only scaffold is insufficient for Kaggle-based Phase 5 execution.

Specifically, this document supersedes:

```text
Original Phase 4.5 Section 5 branch/scaffold policy
```

The following remain authoritative unless explicitly refined here:

```text
Phase 0 threat model and exclusions
Phase 1 payload provenance and hash governance
Phase 2/2.5 infrastructure and token-budget constraints
Phase 3 benign competence baseline evidence
Phase 4 protocol freeze artifacts
Phase 4 frozen Phase 5 schema
Phase 4 statistical plan
Phase 4 payload reference map
Phase 4 model set freeze
Original Phase 4.5 non-official dry-run boundary
Original Phase 4.5 rerun/preservation discipline
```

This means:

```text
Hybrid scaffolding is allowed.
Kaggle execution support is allowed.
Phase 4.5 remains non-official.
Phase 5 schema remains frozen and cannot be redefined by Phase 4.5.
```

---

## 2. Executive Summary

Phase 4.5 is a **hybrid execution checkpoint** between Phase 4 protocol freeze and Phase 5 official adversarial evaluation.

The project uses three environments:

```text
GitHub = source of truth, frozen protocol, scripts, configs, matrices, logs, audit trail
Local machine = Phase 4.5A local dry-run and repository validation
Kaggle = Phase 4.5B smoke test and later Phase 5 official model execution
```

The purpose of Phase 4.5 is not to measure vulnerability, ASR, defense effectiveness, or final model behavior.

The purpose is to prove that:

```text
The frozen Phase 5 pipeline can actually run,
produce valid logs,
load frozen payloads,
respect the frozen schema,
reset state correctly,
survive Kaggle execution,
estimate Phase 5 runtime feasibility,
and export reproducible evidence.
```

The correct flow is:

```text
Phase 4 freeze in GitHub
↓
GitHub Phase 4.5 scaffold
↓
Local Phase 4.5A dry-run / validation
↓
Commit local evidence to GitHub
↓
Kaggle Phase 4.5B smoke test
↓
Kaggle remaining-model loader smoke
↓
Export Kaggle evidence back to GitHub
↓
Quota and checkpoint/resume feasibility report
↓
External audit
↓
Phase 5 official Kaggle evaluation
```

Phase 5 may begin only after Phase 4.5A, Phase 4.5B, Kaggle model-load checks, schema validation, quota feasibility, and external audit all pass.

---

## 3. Core Methodological Principle

Phase 4.5 is an **engineering validation phase**, not a research-result phase.

Every Phase 4.5 trial row must clearly state:

```json
{
  "phase": "phase4_5",
  "dry_run": true,
  "official_trial": false,
  "counts_for_phase5": false,
  "publication_evidence": false
}
```

No Phase 4.5 output may be used as:

```text
official Phase 5 evidence
publishable ASR
vulnerability evidence
defense-effectiveness evidence
model robustness evidence
final exploit-rate evidence
```

Phase 4.5 answers:

```text
Is the pipeline technically ready for official Phase 5 execution on Kaggle?
```

It does not answer:

```text
Are MCP agents vulnerable?
What is the true ASR?
Does the defense work?
Which model is safest?
```

---

## 4. Environment Responsibilities

### 4.1 GitHub Responsibility

GitHub is the **source of truth**.

GitHub must contain:

```text
Phase 4 frozen artifacts
Phase 4.5 scaffold
configs
schemas
full schema mapping
dry-run matrices
execution scripts
Kaggle notebook/script
pinned environment specs
local dry-run logs or local deferment evidence
Kaggle smoke-test logs
Kaggle remaining-model loader logs
validation reports
runtime feasibility report
checkpoint/resume strategy
hash manifests
audit reports
final GO / REVISE / NO-GO decision
```

GitHub must not merely contain empty folders and summary claims.  
It must preserve raw evidence.

### 4.2 Local Machine Responsibility

The local machine is used for **Phase 4.5A local validation and dry-run**.

Local execution validates:

```text
repository structure
Phase 4 artifact availability
full schema mapping
payload-reference loading
prompt compilation
trial logging
reset logic
outcome taxonomy
statistics smoke mode
forbidden-claims linting
```

If the local machine can run one frozen model, it should run the small local dry-run.  
If the local machine cannot run a model reliably, it must not fake results. It should mark model execution as deferred to Kaggle.

### 4.3 Kaggle Responsibility

Kaggle is the model-heavy execution platform.

Kaggle is used for:

```text
Phase 4.5B representative smoke test
Kaggle-side loader checks for all frozen models
Phase 5 runtime feasibility measurement
later Phase 5 official adversarial evaluation
```

Kaggle must use the exact GitHub commit being audited or tested.

Kaggle must export all evidence back to GitHub.

Kaggle is not the source of truth.  
GitHub remains the source of truth.

---

## 5. Canonical Branching Strategy

The original local-only Phase 4.5 branch name is replaced by the following hybrid branch because the plan now includes Kaggle execution artifacts:

```bash
git checkout -b phase4_5-dryrun-hybrid
```

This branch must be created from the Phase 4 freeze commit.

Create a branch-start report:

```text
phase4_5/validation/phase45_branch_start_report.md
```

It must record:

```text
branch_name
source_branch
source_commit
phase4_freeze_commit
operator
date_utc
reason_for_hybrid_branch
confirmation_that_phase4_frozen_artifacts_are_not_modified
```

After Phase 4.5 passes, tag the commit:

```bash
git tag phase45-passed-kaggle-smoke
git push origin phase45-passed-kaggle-smoke
```

Phase 5 should begin on a new branch:

```bash
git checkout -b phase5-official-kaggle-evaluation
```

Do not run Phase 5 official experiments on the same uncontrolled working branch used for Phase 4.5 debugging.

---

## 6. Canonical Status and Verdict Vocabulary

Scripts must parse one fixed enum set.

### 6.1 Final Verdict Enum

The only allowed final Phase 4.5 verdicts are:

```text
GO_TO_PHASE5
REVISE_PHASE45
NO_GO
```

### 6.2 Internal Status Labels

The only allowed internal status labels are:

```text
PHASE4_FREEZE_VERIFIED
PHASE45_SCAFFOLD_COMPLETE
LOCAL_PREFLIGHT_PASS
LOCAL_DRYRUN_PASS
LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE
KAGGLE_SMOKE_PREPARED
KAGGLE_SMOKE_PASS
KAGGLE_MODEL_LOAD_SMOKE_PASS
KAGGLE_QUOTA_FEASIBILITY_PASS
SCHEMA_VALIDATION_PASS
PAYLOAD_VALIDATION_PASS
TOKEN_BUDGET_VALIDATION_PASS
RESET_VALIDATION_PASS
STATISTICS_SMOKE_PASS
FORBIDDEN_CLAIMS_LINT_PASS
EXTERNAL_AUDIT_GO
GO_TO_PHASE5
REVISE_PHASE45
NO_GO
```

### 6.3 Disallowed Status Labels

Do not use:

```text
GO_TO_PHASE5_AFTER_KAGGLE_SMOKE_PASS
PHASE 4.5 VERDICT: GO TO PHASE 5
REVISE PHASE 4 AND RE-RUN PHASE 4.5
REVISE_PHASE4_BEFORE_PHASE45
looks good
probably fine
ready enough
passed maybe
conditional go maybe
```

If Phase 4 itself is incomplete, the Phase 4.5 final verdict is still:

```text
REVISE_PHASE45
```

with reason:

```text
Phase 4 freeze artifacts incomplete.
```

---

## 7. Phase 4 Freeze Preconditions

Before Phase 4.5 begins, verify that Phase 4 is actually complete.

Required Phase 4 artifacts:

```text
phase4/configs/model_set_freeze.yaml
phase4/configs/payload_reference_map.json
phase4/configs/phase5_schema_freeze.json
phase4/configs/statistical_plan.yaml
phase4/configs/defense_config_freeze.yaml

phase4/validation/phase3_artifact_ingestion_report.md
phase4/validation/model_identity_freeze_report.md
phase4/validation/payload_reference_validation_report.md
phase4/validation/token_budget_reverification_report.md
phase4/validation/branch_synchronization_report.md
phase4/validation/final_phase4_verification_report.md

phase4/frozen_bundle/cryptographic_lock_manifest.json
phase4/frozen_bundle/master_hash_ledger.csv
phase4/frozen_bundle/trial_order_core.csv
phase4/frozen_bundle/trial_order_defense.csv
phase4/frozen_bundle/phase5_execution_manifest.json

phase4/reports/phase4_go_no_go_decision.md
```

If any of these are missing, Phase 4.5 must not be treated as valid.

Correct verdict:

```text
REVISE_PHASE45
```

Reason:

```text
Phase 4 freeze incomplete.
```

Do not fabricate Phase 4 artifacts inside Phase 4.5.

---

## 8. GitHub Scaffold for Phase 4.5

Create this structure:

```text
phase4_5/
  README.md

  configs/
    phase45_local_dryrun.yaml
    phase45_kaggle_smoke.yaml
    phase45_selected_model.yaml
    phase45_schema_mapping.yaml
    phase45_status_enum.yaml
    phase45_environment_lock.yaml
    phase45_checkpoint_resume.yaml

  matrices/
    phase45_local_dryrun_matrix.csv
    phase45_kaggle_smoke_matrix.csv
    phase45_remaining_model_loader_smoke_local.csv
    phase45_remaining_model_loader_smoke_kaggle.csv

  scripts/
    verify_phase45_preflight.py
    validate_phase45_schema_mapping.py
    build_phase45_local_matrix.py
    build_phase45_kaggle_matrix.py
    run_phase45_local_dryrun.py
    run_phase45_kaggle_smoke.py
    validate_phase45_logs.py
    smoke_test_phase45_statistics.py
    estimate_phase5_kaggle_runtime.py
    summarize_phase45.py
    lint_phase45_forbidden_claims.py

  kaggle/
    phase45_kaggle_runner.ipynb
    phase45_kaggle_runner.py
    requirements.lock.txt
    kaggle_runtime_setup.md
    README.md

  dryrun_results/
    local/
      trials.jsonl
      raw_prompts.jsonl
      raw_outputs.jsonl
      tool_transcripts.jsonl
      reset_checks.jsonl
      hardware_metrics.jsonl
      failures.jsonl
      invalid_trials.jsonl
      rerun_links.jsonl
      run_manifest.json
      run_hashes.json

    kaggle_smoke/
      trials.jsonl
      raw_prompts.jsonl
      raw_outputs.jsonl
      tool_transcripts.jsonl
      reset_checks.jsonl
      hardware_metrics.jsonl
      failures.jsonl
      invalid_trials.jsonl
      rerun_links.jsonl
      kaggle_environment_report.md
      kaggle_dataset_manifest.md
      kaggle_execution_commit.txt
      run_manifest.json
      run_hashes.json

    kaggle_model_loader_smoke/
      model_loader_trials.jsonl
      model_loader_outputs.jsonl
      model_loader_hardware_metrics.jsonl
      model_loader_report.md

  validation/
    phase45_branch_start_report.md
    phase45_preflight_report.md
    phase45_schema_mapping_report.md
    phase45_local_dryrun_report.md
    phase45_remaining_model_loader_smoke_report.md
    phase45_kaggle_smoke_preparation_report.md
    phase45_kaggle_smoke_report.md
    phase45_kaggle_model_loader_smoke_report.md
    phase45_kaggle_quota_feasibility_report.md
    phase45_checkpoint_resume_report.md
    phase45_log_schema_report.md
    phase45_reset_report.md
    phase45_grading_report.md
    phase45_statistics_smoke_report.md
    phase45_forbidden_claims_report.md
    phase45_final_go_no_go.md

  reports/
    phase45_summary.md

  logs/
    phase45_execution_notes.md

  run_manifests/
    local_run_manifest.json
    kaggle_smoke_run_manifest.json
```

Also create:

```text
docs/phase45_kaggle_execution_substrate_note.md
```

This document must explain:

```text
The project uses a hybrid execution design.
GitHub remains the source of truth.
Local execution validates repository/pipeline behavior.
Kaggle is the model-heavy execution environment.
All Kaggle outputs must return to GitHub.
This is an approved execution-substrate adaptation, not silent methodology drift.
```

Initial scaffold commit:

```bash
git add phase4_5/ docs/phase45_kaggle_execution_substrate_note.md
git commit -m "phase45: scaffold hybrid local and kaggle dry-run workflow"
```

---

## 9. Full Frozen-Schema Mapping Requirement

This is the most important Phase 4.5 rule.

Phase 4.5 must not invent a new logging schema.

All Phase 4.5 trial rows must validate against:

```text
phase4/configs/phase5_schema_freeze.json
```

The file:

```text
phase4_5/configs/phase45_schema_mapping.yaml
```

must enumerate **every field** required by `phase5_schema_freeze.json`.

A 3-field rename map is insufficient and invalid.

### 9.1 Mapping File Structure

`phase45_schema_mapping.yaml` must include one mapping entry per frozen schema field.

Each entry must specify:

```yaml
field_name:
  required: true_or_false
  phase5_type: string|number|integer|boolean|object|array|null
  source_category: phase4_payload_reference|phase4_model_freeze|phase4_schema|phase45_runtime|phase45_grader|phase45_reset|phase45_hardware|phase45_hashing|constant|nullable
  source_field: path.or.description
  transformation: pass_through|rename|enum_normalize|hash_lookup|runtime_generated|computed|constant|nullable
  dry_run_allowed: true_or_false
  official_phase5_required: true_or_false
  validation_rule: description
```

### 9.2 Required Mapping Coverage

The mapping must cover all fields in the frozen schema, including but not limited to:

```text
trial_id
run_id
phase
dry_run
official_trial
counts_for_phase5
publication_evidence

model_slot
model_identifier
model_digest
runtime_backend
backend_version
tokenizer_identity

density
metadata_surface_condition
attack_family

payload_id
phase1_payload_hash
payload_hash
payload_reference_validated

system_prompt_hash
prompt_hash
raw_output_hash
tool_transcript_hash
source_freeze_hash
tool_call_contract_hash
metadata_surface_hash
task_corpus_hash
tool_mapping_hash

primary_outcome_class
critical_exploit
critical_exploit_path_type
attack_success
hijack_attempt
utility_success
tid_levenshtein

json_validity
parse_status
model_competence_success

reset_result
reset_before_trial_passed
reset_after_trial_passed
infrastructure_valid

latency_ms
token_counts
oom_event
daemon_restart
hardware_profile

critical_exploit_detector_executed
tid_calculation_executed
statistics_smoke_included
```

If the actual `phase5_schema_freeze.json` contains additional fields, they must also be mapped.

### 9.3 Outcome Representation Reconciliation

The frozen schema uses a layered outcome representation.

Phase 4.5 must use:

```text
primary_outcome_class
critical_exploit
critical_exploit_path_type
attack_success
hijack_attempt
utility_success
tid_levenshtein
```

Do not replace this with a single invented field such as:

```text
outcome_primary
outcome_label
```

unless the frozen schema explicitly includes those fields.

If compatibility helper fields are added for debugging, they must be clearly marked as non-authoritative and must not replace the frozen fields.

### 9.4 Required Rename Mappings

At minimum, include these mappings:

```text
payload_reference_map.metadata_condition
→ trial.metadata_surface_condition

payload_reference_map.attack_family
→ trial.attack_family

payload_reference_map.source_payload_hash
→ trial.phase1_payload_hash

payload_reference_map.adapted_payload_hash
→ trial.payload_hash
```

Trial logs must use these Phase 5-compatible names:

```text
metadata_surface_condition
attack_family
phase1_payload_hash
payload_hash
```

Do not use these as primary trial fields:

```text
metadata_condition
source_payload_hash
adapted_payload_hash
```

### 9.5 Attack-Family Enum Normalization

Attack-family enum values must use frozen Phase 5 style:

```text
DIRECT_OVERRIDE
CROSS_CAPABILITY_ESCALATION
DATA_EXFILTRATION
```

Do not use:

```text
Direct Override
Cross-Capability Escalation
Data Exfiltration
```

unless `phase5_schema_freeze.json` explicitly requires them.

### 9.6 Schema Mapping Validation

The validator:

```text
phase4_5/scripts/validate_phase45_schema_mapping.py
```

must fail if:

```text
any frozen schema field is unmapped
any trial row contains a required field with null/blank value
any enum does not match the frozen schema
any Phase 4.5-only schema is used instead of phase5_schema_freeze.json
any outcome fields are represented differently from the frozen schema
any payload hash fields use non-frozen names as primary fields
```

The report:

```text
phase4_5/validation/phase45_schema_mapping_report.md
```

must state:

```text
Frozen schema fields discovered:
Frozen schema fields mapped:
Unmapped required fields:
Unmapped optional fields:
Extra non-frozen fields:
Enum compatibility:
Outcome representation compatibility:
Verdict:
```

---

## 10. Dependency Pinning Before Kaggle Execution

Kaggle dependency versions must be pinned **before** the smoke test.

Create:

```text
phase4_5/kaggle/requirements.lock.txt
phase4_5/configs/phase45_environment_lock.yaml
```

These must specify:

```text
Python version
CUDA availability expectation
PyTorch version
transformers version if used
accelerate version if used
bitsandbytes version if used
sentencepiece version if used
protobuf version if needed
pandas/numpy versions
jsonschema/pydantic versions
any MCP/server/client dependencies
model backend package versions
```

The Kaggle notebook must install from this lock file or verify the environment matches it.

After execution, Kaggle must also record the actual environment in:

```text
phase4_5/dryrun_results/kaggle_smoke/kaggle_environment_report.md
```

If actual versions differ from the lock file, the report must mark:

```text
KAGGLE_ENVIRONMENT_DRIFT_DETECTED
```

Phase 5 cannot start until the drift is resolved or formally accepted with justification.

---

## 11. Phase 4.5A Local Dry-Run

### 11.1 Purpose

Phase 4.5A validates the local pipeline.

It checks:

```text
artifact loading
full schema compatibility
payload reference loading
prompt compilation
logging
reset logic
outcome taxonomy
statistics smoke mode
forbidden-claims linting
```

### 11.2 Local Dry-Run Matrix

Default local dry-run:

```text
1 selected frozen model
2 densities: D3, D5
2 metadata conditions: POISON_TD, POISON_CA
3 attack families:
  DIRECT_OVERRIDE
  CROSS_CAPABILITY_ESCALATION
  DATA_EXFILTRATION
6 trials per density × metadata condition
```

Total:

```text
1 × 2 × 2 × 6 = 24 local dry-run trials
```

This is not a statistical sample.  
It is a pipeline validation sample.

### 11.3 Selected Model Rule

Select one model from the frozen Phase 4 model set.

Preferred selection:

```text
The strongest Phase 3 GO_STRONG model with the most stable parser/tool-call behavior.
```

Tie-breakers:

```text
highest Phase 3 competence success rate
lowest infrastructure failure rate
most stable tokenizer/backend
lowest runtime burden
easiest local execution
```

Record selection in:

```text
phase4_5/configs/phase45_selected_model.yaml
phase4_5/validation/phase45_preflight_report.md
```

Do not select a new model outside the Phase 4 frozen model set.

### 11.4 If Local Model Execution Is Not Possible

If the laptop cannot run the model, do not fake output.

Mark:

```text
LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE
```

Still locally validate:

```text
schemas
payload references
trial matrix construction
prompt compilation if possible
static log schema
statistics smoke on synthetic schema-valid dummy rows only if clearly marked
forbidden-claims lint
```

Any dummy or synthetic rows must be clearly marked:

```json
{
  "synthetic_schema_validation_only": true,
  "model_generated": false,
  "official_trial": false,
  "counts_for_phase5": false
}
```

Synthetic schema rows cannot replace Kaggle smoke execution.

---

## 12. Local Timing Probe

Before running the full 24-row local dry-run, perform one timing probe if local model execution is possible.

Timing probe:

```text
1 selected model
D5
POISON_CA
1 dry-run trial
official_trial: false
counts_for_phase5: false
```

D5 + POISON_CA is selected because it is the highest-footprint local condition and is most likely to expose token/context/runtime issues.

Record:

```text
wall_clock_seconds
load_time_seconds
prompt_compile_time_seconds
generation_time_seconds
tool_execution_time_seconds
grading_time_seconds
reset_time_seconds
peak_RAM
peak_VRAM_if_available
backend
device
```

If this single trial is too slow, unstable, or causes model/backend crashes, stop and document:

```text
LOCAL_DRYRUN_EXECUTION_UNSTABLE
```

Then defer model-heavy validation to Kaggle.

---

## 13. Local Dry-Run Evidence

Local dry-run outputs must be stored in:

```text
phase4_5/dryrun_results/local/
```

Required files:

```text
trials.jsonl
raw_prompts.jsonl
raw_outputs.jsonl
tool_transcripts.jsonl
reset_checks.jsonl
hardware_metrics.jsonl
failures.jsonl
invalid_trials.jsonl
rerun_links.jsonl
run_manifest.json
run_hashes.json
```

Validation reports:

```text
phase4_5/validation/phase45_local_dryrun_report.md
phase4_5/validation/phase45_log_schema_report.md
phase4_5/validation/phase45_reset_report.md
phase4_5/validation/phase45_grading_report.md
phase4_5/validation/phase45_statistics_smoke_report.md
phase4_5/validation/phase45_forbidden_claims_report.md
```

Commit local evidence:

```bash
git add phase4_5/
git commit -m "phase45: add local dry-run evidence"
```

---

## 14. Rerun and Invalid-Trial Preservation Policy

This policy applies to local dry-run, Kaggle smoke, and Phase 5.

Invalid trials must never be overwritten or deleted.

If a trial fails because of infrastructure, reset, timeout, OOM, schema write failure, model backend crash, or corrupted log write:

1. Preserve the original row in:
   ```text
   invalid_trials.jsonl
   failures.jsonl
   ```
2. Assign a new trial ID for the rerun.
3. Record a rerun link in:
   ```text
   rerun_links.jsonl
   ```
4. The rerun link must include:
   ```text
   original_trial_id
   rerun_trial_id
   failure_reason
   rerun_authorized_by
   timestamp_utc
   counts_for_phase5: false for Phase 4.5
   ```
5. Do not count the failed original row as valid.
6. Do not reuse the same trial ID.
7. Do not silently replace failed outputs.

For Phase 4.5, both failed and rerun rows remain non-official:

```json
{
  "official_trial": false,
  "counts_for_phase5": false
}
```

---

## 15. Remaining-Model Loader Smoke Check

Because Phase 5 will use multiple frozen models on Kaggle, Phase 4.5 must document whether non-selected frozen models can load.

There are two layers:

```text
Local remaining-model loader check
Kaggle remaining-model loader check
```

### 15.1 Local Remaining-Model Loader Check

For each remaining frozen model, perform one of:

```text
EXECUTED_LOCALLY_PASS
EXECUTED_LOCALLY_FAIL
NOT_EXECUTED_LOCALLY_DEFERRED_TO_KAGGLE
```

Minimal check:

```text
1 model
1 density: D3
1 condition: CLEAN or POISON_TD
1 trial only
official_trial: false
counts_for_phase5: false
```

Report location:

```text
phase4_5/validation/phase45_remaining_model_loader_smoke_report.md
```

### 15.2 Kaggle Remaining-Model Loader Check

Before Phase 5, Kaggle must verify that every frozen model can load in the Kaggle runtime.

For each frozen model:

```text
load model
record model identifier
record model digest/hash if available
record backend
record tokenizer identity
compile one minimal prompt
optionally generate one syntactically valid tool-call style output
record load time
record peak VRAM/RAM
record success/failure
```

Store outputs in:

```text
phase4_5/dryrun_results/kaggle_model_loader_smoke/
```

Required files:

```text
model_loader_trials.jsonl
model_loader_outputs.jsonl
model_loader_hardware_metrics.jsonl
model_loader_report.md
```

Validation report:

```text
phase4_5/validation/phase45_kaggle_model_loader_smoke_report.md
```

Phase 5 cannot start if any frozen Phase 5 model has not been load-tested on Kaggle, unless the Phase 5 model set is formally narrowed in Phase 4 and re-frozen.

---

## 16. Phase 4.5B Kaggle Smoke Test

### 16.1 Purpose

Phase 4.5B validates the actual execution platform that will be used for Phase 5.

This is necessary because local execution and Kaggle execution may differ in:

```text
dependency versions
GPU availability
tokenizer behavior
file paths
model loading
memory behavior
notebook state
package installation
output export behavior
```

A local-only Phase 4.5 cannot authorize Phase 5 on Kaggle.

### 16.2 Expanded Kaggle Smoke Matrix

The Kaggle smoke test must cover the main platform-risk axes:

```text
1 selected frozen model
2 densities: D3 and D5
2 metadata conditions: POISON_TD and POISON_CA
at least 2 attack families represented
minimum 1 dry-run trial per density × metadata condition
```

Minimum required Kaggle smoke matrix:

```text
D3 + POISON_TD + DIRECT_OVERRIDE
D3 + POISON_CA + CROSS_CAPABILITY_ESCALATION
D5 + POISON_TD + DATA_EXFILTRATION
D5 + POISON_CA + CROSS_CAPABILITY_ESCALATION or DIRECT_OVERRIDE
```

Minimum total:

```text
4 Kaggle smoke trials
```

Recommended total if compute permits:

```text
8 Kaggle smoke trials
2 per density × metadata condition
all 3 attack families represented at least once
```

Every Kaggle smoke row must be:

```json
{
  "phase": "phase4_5",
  "dry_run": true,
  "official_trial": false,
  "counts_for_phase5": false,
  "publication_evidence": false
}
```

This test validates execution, not results.

### 16.3 Kaggle Notebook Requirements

The Kaggle notebook/script must:

1. clone or load the exact GitHub commit;
2. record the GitHub commit hash;
3. install from `phase4_5/kaggle/requirements.lock.txt`;
4. verify actual environment against `phase45_environment_lock.yaml`;
5. record dependency versions;
6. load the selected frozen model;
7. record model identity and digest;
8. run Kaggle model-loader smoke for all frozen models or document failure;
9. load Phase 4 frozen configs;
10. load payload references;
11. validate full schema mapping;
12. compile prompts;
13. run the expanded Kaggle smoke matrix;
14. write raw logs;
15. run schema validation;
16. run reset validation;
17. run statistics smoke mode;
18. estimate Phase 5 runtime feasibility;
19. export all outputs;
20. produce run hashes;
21. make no Phase 5 claims.

### 16.4 Kaggle Evidence Returned to GitHub

After the Kaggle run, download outputs and place them in:

```text
phase4_5/dryrun_results/kaggle_smoke/
```

Required files:

```text
trials.jsonl
raw_prompts.jsonl
raw_outputs.jsonl
tool_transcripts.jsonl
reset_checks.jsonl
hardware_metrics.jsonl
failures.jsonl
invalid_trials.jsonl
rerun_links.jsonl
kaggle_environment_report.md
kaggle_dataset_manifest.md
kaggle_execution_commit.txt
run_manifest.json
run_hashes.json
```

Then run local validators against these Kaggle outputs.

Generate:

```text
phase4_5/validation/phase45_kaggle_smoke_report.md
phase4_5/validation/phase45_log_schema_report.md
phase4_5/validation/phase45_statistics_smoke_report.md
phase4_5/validation/phase45_final_go_no_go.md
```

Commit Kaggle evidence:

```bash
git add phase4_5/dryrun_results/kaggle_smoke/ phase4_5/dryrun_results/kaggle_model_loader_smoke/ phase4_5/validation/
git commit -m "phase45: add kaggle smoke-test and loader evidence"
```

---

## 17. Kaggle Execution Commit Discipline

Kaggle must record the exact GitHub commit used for execution.

The file:

```text
phase4_5/dryrun_results/kaggle_smoke/kaggle_execution_commit.txt
```

must contain:

```text
repository_url
branch
commit_hash
execution_date_utc
kaggle_notebook_name
kaggle_runtime_type
operator
```

The commit hash must match the GitHub commit that contains:

```text
Phase 4 freeze artifacts
Phase 4.5 scaffold
Kaggle runner
Kaggle smoke matrix
full schema mapping
dependency lock file
```

If Kaggle runs from an uncommitted or manually modified notebook, mark:

```text
KAGGLE_SMOKE_INVALID_UNTRACKED_EXECUTION
```

---

## 18. Kaggle Quota and Phase 5 Runtime Feasibility

Phase 4.5 must estimate whether Phase 5 can fit into Kaggle execution limits.

The Phase 4 frozen core workload is approximately:

```text
4 models × 3 densities × 3 metadata conditions × 150 accepted trials
= 5,400 core adversarial trials
```

Defense and utility workloads may add additional trials.

### 18.1 Required Runtime Measurements

From Kaggle smoke, compute:

```text
mean_wall_clock_seconds_per_trial
median_wall_clock_seconds_per_trial
p95_wall_clock_seconds_per_trial
mean_model_load_time
mean_reset_time
mean_prompt_compile_time
mean_generation_time
mean_grading_time
oom_rate
daemon_restart_rate
```

### 18.2 Required Runtime Projection

Create:

```text
phase4_5/validation/phase45_kaggle_quota_feasibility_report.md
```

It must estimate:

```text
core_phase5_trials
defense_trials_if_any
utility_trials_if_any
estimated_total_trials
estimated_total_runtime_mean
estimated_total_runtime_p95
estimated_sessions_required
expected_trials_per_session
expected_checkpoints_per_session
risk_of_timeout
risk_of_quota_exhaustion
```

### 18.3 Required Checkpoint/Resume Strategy

Create:

```text
phase4_5/configs/phase45_checkpoint_resume.yaml
phase4_5/validation/phase45_checkpoint_resume_report.md
```

The strategy must specify:

```text
trial shard size
checkpoint frequency
where partial logs are written
how completed trials are detected
how duplicate trial IDs are prevented
how interrupted sessions resume
how invalid trials are rerun under new IDs
how run hashes are updated
how per-shard manifests are committed
```

If the estimated Phase 5 workload cannot fit into one Kaggle session, that is not automatically fatal. But the checkpoint/resume strategy must be in place before Phase 5.

If feasibility cannot be estimated from the smoke test, final verdict must be:

```text
REVISE_PHASE45
```

---

## 19. What Should Not Be Committed

Do not commit:

```text
model weights
Kaggle cache
large downloaded datasets
temporary model cache folders
.env files
API keys
credentials
local absolute paths as required paths
notebook scratch outputs unrelated to the run
```

Commit evidence instead:

```text
model name
model digest/hash
backend identity
backend version
tokenizer identity
dependency versions
GitHub commit hash
raw JSONL logs
run manifests
hash manifests
validation reports
audit reports
```

---

## 20. Token Budget Validation

Phase 4.5 must respect the frozen Phase 2.5 / Phase 4 token budget:

```text
Total context ceiling: 4,096 tokens
Usable prompt budget: 3,584 tokens
Reserved output/tool-call buffer: 512 tokens
```

For local and Kaggle runs, log or report:

```text
system_prompt_tokens
schema_tokens
capability_advertisement_tokens
payload_tokens
task_tokens
history_tokens
total_prompt_tokens
budget_utilization
tokenizer_identity
backend
```

D5 + POISON_CA must be included in Kaggle smoke specifically because it is likely to have the largest prompt footprint.

If Kaggle tokenizer behavior differs from local tokenizer behavior, document the difference.

Do not silently mix tokenizers without recording it.

---

## 21. Payload Integrity

Phase 4.5 must use only payload references approved by Phase 1 and locked by Phase 4.

The chain must be:

```text
Phase 1 payload ledger
↓
Phase 4 payload_reference_map.json
↓
Phase 4.5 dry-run trial row
```

Each trial row must include:

```text
payload_id
phase1_payload_hash
payload_hash
payload_reference_validated
```

Payload rules:

```text
No rewriting
No paraphrasing
No grammar correction
No shortening
No formatting cleanup
No semantic reinterpretation
No new payload creation
```

If a payload does not validate, exclude the affected trial and report failure.

---

## 22. Reset and Isolation

Every local and Kaggle trial must validate:

```text
reset before trial
reset after trial
no leftover outbox state
no leftover cache state
no leftover event state
no leaked conversation state
no reused prompt/output
```

Required reset logs:

```text
reset_checks.jsonl
```

If reset fails, the trial is invalid and must follow the rerun-preservation policy.

If reset behavior differs between local and Kaggle, document it as a substrate difference.

---

## 23. Statistics Smoke Mode

Phase 4.5 may run statistics scripts only in smoke mode.

Allowed checks:

```text
schema parsing
official_trial filtering
counts_for_phase5 filtering
dry_run exclusion
denominator handling
outcome-label parsing
TID input parsing
Critical Exploit detector input parsing
grouping by model/density/metadata/attack_family
handling of primary_outcome_class
handling of critical_exploit boolean
handling of attack_success boolean
handling of hijack_attempt boolean
handling of utility_success boolean
handling of tid_levenshtein
```

Forbidden outputs:

```text
final ASR
final exploit rate
vulnerability confirmed
defense works
model is robust
publishable result
```

The statistics smoke report must state:

```text
No Phase 4.5 row is valid for publication or Phase 5 inference.
```

---

## 24. Forbidden-Claims Lint

Run a forbidden-claims lint over all Phase 4.5 Markdown reports and summaries.

Search for premature claims such as:

```text
final ASR
vulnerability confirmed
robustness confirmed
defense effective
MCP is vulnerable
attack success rate is
official adversarial result
publication conclusion
```

These may appear only as forbidden examples.

If they appear as claims, Phase 4.5 fails.

---

## 25. Final Phase 4.5 Decision Logic

The final decision file is:

```text
phase4_5/validation/phase45_final_go_no_go.md
```

Allowed verdicts:

```text
GO_TO_PHASE5
REVISE_PHASE45
NO_GO
```

Use `GO_TO_PHASE5` only if:

```text
Phase 4 freeze artifacts exist
Phase 4.5 scaffold exists
full frozen-schema mapping passes
local validation passed
local dry-run passed or local model execution was explicitly deferred
Kaggle smoke test executed
Kaggle smoke covers D3, D5, POISON_TD, and POISON_CA
Kaggle remaining-model loader smoke passed for all frozen models
Kaggle outputs returned to GitHub
Kaggle execution commit recorded
logs validate against phase5_schema_freeze.json
payload references validate
token budget passes
reset validation passes
statistics smoke passes
Kaggle quota feasibility report exists
checkpoint/resume strategy exists
forbidden-claims lint passes
external audit passes
no official Phase 5 rows were created
```

Use `REVISE_PHASE45` if:

```text
Kaggle smoke is prepared but not executed
Kaggle model-loader smoke is incomplete
quota feasibility is missing
checkpoint/resume is missing
dependency lock is missing
schema mapping is incomplete but repairable
local validation failed for repairable reasons
```

Use `NO_GO` if:

```text
Phase 4 frozen artifacts are invalid
payloads are mutated
trial logs use a non-frozen schema
required frozen schema fields are missing
rows are marked official_trial true
rows are marked counts_for_phase5 true
raw logs are missing
Kaggle execution commit is missing
security claims are made from Phase 4.5
```

---

## 26. External Audit

After committing local and Kaggle evidence, run an independent read-only audit.

The audit must verify:

```text
Phase 4 frozen artifacts were not mutated
Phase 4.5 logs match the full Phase 5 schema
all frozen schema fields are mapped
outcome representation matches Phase 5 schema
local dry-run rows are non-official
Kaggle smoke rows are non-official
payloads trace to Phase 1 and Phase 4
Kaggle execution commit is recorded
Kaggle environment is recorded
dependency lock exists and matches runtime
raw prompts/outputs/transcripts exist
reset logs exist
Kaggle model-loader smoke covers all frozen models
Kaggle smoke covers D3, D5, POISON_TD, and POISON_CA
quota feasibility report exists
checkpoint/resume strategy exists
statistics ran only in smoke mode
no ASR or vulnerability claims were made
Phase 5 is not authorized unless Kaggle smoke passed
```

Audit verdict options:

```text
GO_TO_PHASE5
REVISE_PHASE45
NO_GO
```

Only an external `GO_TO_PHASE5` verdict authorizes official Phase 5 execution.

---

## 27. Full Practical Implementation Order

Follow this exact order:

```text
1. Create branch: phase4_5-dryrun-hybrid from the Phase 4 freeze commit.

2. Create phase45_branch_start_report.md.

3. Verify Phase 4 freeze artifacts exist.

4. Add Phase 4.5 scaffold.

5. Add docs/phase45_kaggle_execution_substrate_note.md.

6. Add canonical status enum file.

7. Add dependency lock files.

8. Build full schema mapping by reading phase5_schema_freeze.json.

9. Validate that every frozen schema field is mapped.

10. Add local dry-run matrix.

11. Add expanded Kaggle smoke matrix.

12. Add Kaggle remaining-model loader matrix.

13. Add Kaggle runner notebook and script.

14. Add checkpoint/resume config.

15. Commit scaffold.

16. Run Phase 4.5 preflight.

17. Run schema mapping validation.

18. Run local timing probe if model execution is possible.

19. Run local 24-trial dry-run if model execution is possible.

20. If local model execution is not possible, document deferment to Kaggle.

21. Generate local validation reports.

22. Commit local evidence.

23. Push branch to GitHub.

24. Open Kaggle.

25. Run phase45_kaggle_runner.ipynb from the exact GitHub commit.

26. Install dependencies from requirements.lock.txt.

27. Run Kaggle model-loader smoke for all frozen models.

28. Run expanded Kaggle smoke matrix.

29. Export Kaggle logs and reports.

30. Download Kaggle outputs.

31. Copy Kaggle outputs into phase4_5/dryrun_results/.

32. Run local validators on Kaggle outputs.

33. Generate Kaggle quota feasibility report.

34. Generate checkpoint/resume report.

35. Generate final Phase 4.5 GO / REVISE / NO-GO report.

36. Commit Kaggle evidence.

37. Run external read-only audit.

38. If audit passes, tag repo: phase45-passed-kaggle-smoke.

39. Create new Phase 5 branch.

40. Begin official Phase 5 Kaggle evaluation only after this point.
```

---

## 28. Clean Phase 4.5 Exit Criteria

Phase 4.5 is complete only when the repository contains:

```text
Phase 4.5 scaffold
branch-start report
dependency lock file
full schema mapping
full schema mapping report
local validation evidence
local dry-run evidence or documented local execution deferment
Kaggle smoke-test raw logs
Kaggle model-loader smoke results for all frozen models
Kaggle environment report
Kaggle execution commit
schema validation report
payload validation report
token-budget validation report
reset validation report
statistics smoke report
quota feasibility report
checkpoint/resume report
forbidden-claims report
final Phase 4.5 GO report
external audit GO report
```

If any of these are missing, do not start Phase 5.

---

## 29. Practical Rule of Thumb

Use this rule throughout the phase:

```text
GitHub owns truth.
Local validates logic.
Kaggle validates execution.
Schema mapping validates compatibility.
Quota planning validates feasibility.
Audit validates readiness.
Phase 5 starts only after all six agree.
```

Or even simpler:

```text
No full schema map, no GO.
No raw logs, no evidence.
No Kaggle smoke, no Phase 5.
No D5/POISON_CA Kaggle touch, no platform confidence.
No all-model Kaggle loader check, no full-model Phase 5.
No quota plan, no realistic Phase 5.
No audit, no official experiment.
```

---

## 30. Final Notes

This hybrid design is acceptable if handled carefully.

The main danger is not using Kaggle.  
The main danger is silently changing execution assumptions after Phase 4.5.

That is why this version requires:

```text
full frozen-schema mapping
local validation
representative Kaggle smoke
all-model Kaggle loader smoke
Kaggle evidence returned to GitHub
quota feasibility estimation
checkpoint/resume planning
external audit
```

Once those are complete, Phase 5 official Kaggle evaluation can begin with a clean audit trail.
