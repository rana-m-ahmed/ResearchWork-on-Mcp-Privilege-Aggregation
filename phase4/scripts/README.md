# Phase 4 Scripts

## Purpose
Houses all executable Python utilities responsible for auditing, extracting, locking, and validating the repository state.

## Determinism Rule
All scripts must derive outputs exclusively from committed upstream artifacts. No script may fabricate placeholder values, silently substitute defaults, infer missing evidence, or generate synthetic metadata. When required evidence is unavailable, the script must explicitly report DEPENDENCY_MISSING or NOT_MEASURABLE with justification.

## Script Catalog

### `verify_phase4_prerequisites.py`
- **Inputs**: Phase 3 reports, configs, and task corpus.
- **Outputs**: `phase4/validation/phase4_preflight_audit.md`
- **Dependencies**: Upstream Phase 3 artifacts must exist, have size > 0, and valid schemas.
- **Failure conditions**: Fails loudly (`DEPENDENCY_MISSING`) if any prerequisite is missing, empty, unreadable, or fails hash verification.

### `verify_phase4_freeze.py`
- **Inputs**: Phase 4 validation reports, configurations, cryptographic manifest, and trial order.
- **Outputs**: Multiple final audit reports (e.g., `phase4_protocol_freeze_report.md`).
- **Dependencies**: All Phase 4 outputs must exist, have size > 0, and valid schemas.
- **Failure conditions**: Fails loudly (`DEPENDENCY_MISSING`) if any of the final outputs are missing or invalid. Never reports PASS if dependencies are missing.

### `generate_trial_ordering.py`
- **Inputs**: Phase 1 payload ledger, Phase 3 task corpus, `model_set_freeze.yaml`.
- **Outputs**: `phase4/frozen_bundle/trial_order_core.csv`, `trial_ordering_report.md`.
- **Dependencies**: Must have valid Phase 1 payloads, dynamically extractable Phase 3 densities, and explicitly frozen models.
- **Failure conditions**: Fails (`DEPENDENCY_MISSING`) if upstream artifacts are missing. Fails if models list is empty, density extraction fails, or unique trial counts do not match CSV rows.

### `generate_phase5_manifest.py`
- **Inputs**: Hash outputs from `phase1/ledger/payload_provenance_ledger.json`, Phase 3 source freeze manifest, Phase 4 cryptographic lock manifest, Git metadata.
- **Outputs**: `phase4/frozen_bundle/phase5_execution_manifest.json`
- **Dependencies**: Requires upstream manifests and ledgers to generate hashes and counts.
- **Failure conditions**: Does not fail if metadata is missing; instead explicit nulls are recorded (e.g., `execution_uuid: null`). Fails if unable to serialize JSON.

### `validate_payload_references.py`
- **Inputs**: Canonical `phase1/ledger/payload_provenance_ledger.json`.
- **Outputs**: `phase4/configs/payload_reference_map.json`, `payload_reference_validation_report.md`.
- **Dependencies**: Phase 1 ledger must exist and be valid JSON.
- **Failure conditions**: Fails (`DEPENDENCY_MISSING` / `FAIL`) if ledger is missing, unreadable, or contains no valid payloads. 

### `verify_token_budget_phase4.py`
- **Inputs**: Actual Phase 3 execution artifacts.
- **Outputs**: `phase4/validation/token_budget_reverification_report.md`.
- **Dependencies**: None.
- **Failure conditions**: Reports `NOT_MEASURABLE` strictly if authoritative token metrics are genuinely absent. Does not use fallback scraping.

### `compile_cryptographic_lock_manifest.py`
- **Inputs**: Phase 4 configuration files and frozen bundle (excluding itself).
- **Outputs**: `phase4/frozen_bundle/master_hash_ledger.csv`, `phase4/frozen_bundle/cryptographic_lock_manifest.json`.
- **Dependencies**: Target directories must exist.
- **Failure conditions**: Fails if no target files are found to hash.

## Consumed By
The master test runner `execute_phase4.py` or equivalent test runner.

## Validation Process
Every script must strictly utilize argparse, return non-zero exit codes on failure, and produce a Markdown evidence report. Scripts will not be modified post-freeze. They act as the static gatekeeper for Phase 5.
