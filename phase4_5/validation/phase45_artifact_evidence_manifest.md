# Phase 4.5 Artifact Evidence Manifest

## 1. Phase 4 Frozen Artifacts
- `phase4/configs/model_set_freeze.yaml`: `VERIFIED` (hash: `686c112ebfc8e7790098b26454504edd385ee6a21ab41d636949afb7f1a05d0d`)
- `phase4/configs/payload_reference_map.json`: `VERIFIED` (hash: `0bcd7301edcfc372bf66723391c05a0af6ec4f5ee0da981304552a31056c7b37`)
- `phase4/configs/phase5_schema_freeze.json`: `VERIFIED` (hash: `b26ae0025cca7a64a5578af7f63afdd30498116d2b7b7a0ef9fb558b8b8a05ed`)
- `phase4/configs/statistical_plan.yaml`: `VERIFIED` (hash: `aad0afdd8f395ecdd4853e737782c487e3b3207730e3496c9e7b4d1ddb558a07`)
- `phase4/configs/defense_config_freeze.yaml`: `VERIFIED` (hash: `5934137bd5e741b1ce700879691040d215648b409316c3cf09bc559b098d47a8`)
- `phase4/validation/phase3_artifact_ingestion_report.md`: `VERIFIED`
- `phase4/validation/model_identity_freeze_report.md`: `VERIFIED`
- `phase4/validation/payload_reference_validation_report.md`: `VERIFIED`
- `phase4/validation/token_budget_reverification_report.md`: `VERIFIED`
- `phase4/validation/branch_synchronization_report.md`: `VERIFIED`
- `phase4/validation/final_phase4_verification_report.md`: `VERIFIED`
- `phase4/frozen_bundle/cryptographic_lock_manifest.json`: `VERIFIED` (hash: `0f23876bbbe48425bc4420c805cbb0271704494cc62fa902c9a76e48b10dfbaf`)
- `phase4/frozen_bundle/master_hash_ledger.csv`: `VERIFIED` (hash: `d4a7794ee23797659c69de5db99ed35a69026819c46ee306b06474bdedd7d11b`)
- `phase4/frozen_bundle/trial_order_core.csv`: `VERIFIED` (hash: `322369477f4a2d080092995bd7fd800bc2107cb506eb530f156fdbc31a4a7208`)
- `phase4/frozen_bundle/trial_order_defense.csv`: `VERIFIED` (hash: `cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182`)
- `phase4/frozen_bundle/phase5_execution_manifest.json`: `VERIFIED` (hash: `150a91281d92571b31e45d9e1797f76f107ddcf8a0565d7ef1bd853c0f147b64`)
- `phase4/reports/phase4_go_no_go_decision.md`: `VERIFIED` (hash: `ef870f38be8f156afc671f0c02d92c7e51899d03187f21233bd8e4ff47b29256`)

## 2. Phase 4.5 Scaffold
- `phase4_5/`: `VERIFIED`
- `phase4_5/README.md`: `VERIFIED`
- `docs/phase45_kaggle_execution_substrate_note.md`: `VERIFIED`

## 3. Configs
- `phase4_5/configs/phase45_local_dryrun.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_kaggle_smoke.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_selected_model.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_schema_mapping.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_status_enum.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_environment_lock.yaml`: `VERIFIED`
- `phase4_5/configs/phase45_checkpoint_resume.yaml`: `VERIFIED`

## 4. Schema Mapping
- `phase4_5/scripts/validate_phase45_schema_mapping.py`: `VERIFIED`
- `phase4_5/validation/phase45_schema_mapping_report.md`: `VERIFIED`

## 5. Scripts
- `phase4_5/scripts/run_phase45_local_dryrun.py`: `VERIFIED`
- `phase4_5/scripts/smoke_test_phase45_statistics.py`: `VERIFIED`
- `phase4_5/scripts/lint_phase45_forbidden_claims.py`: `VERIFIED`
- `phase4_5/scripts/estimate_phase5_kaggle_runtime.py`: `VERIFIED`
- `phase4_5/scripts/summarize_phase45.py`: `VERIFIED`

## 6. Matrices
- `phase4_5/matrices/phase45_local_dryrun_matrix.csv`: `VERIFIED`
- `phase4_5/matrices/phase45_kaggle_smoke_matrix.csv`: `VERIFIED`
- `phase4_5/matrices/phase45_remaining_model_loader_smoke_local.csv`: `VERIFIED`
- `phase4_5/matrices/phase45_remaining_model_loader_smoke_kaggle.csv`: `VERIFIED`

## 7. Local Evidence
- `phase4_5/dryrun_results/local/trials.jsonl`: `VERIFIED`
- `phase4_5/dryrun_results/local/failures.jsonl`: `VERIFIED`
- `phase4_5/dryrun_results/local/invalid_trials.jsonl`: `VERIFIED`
- `phase4_5/dryrun_results/local/rerun_links.jsonl`: `VERIFIED`
- `phase4_5/dryrun_results/local/reset_checks.jsonl`: `VERIFIED`
- `phase4_5/dryrun_results/local/hardware_metrics.jsonl`: `VERIFIED`

## 8. Kaggle Preparation
- `phase4_5/kaggle/phase45_kaggle_runner.py`: `VERIFIED`
- `phase4_5/kaggle/phase45_kaggle_runner.ipynb`: `VERIFIED`
- `phase4_5/kaggle/requirements.lock.txt`: `VERIFIED`
- `phase4_5/kaggle/kaggle_runtime_setup.md`: `VERIFIED`

## 9. Kaggle Returned Evidence
- `phase4_5/dryrun_results/kaggle_smoke/trials.jsonl`: `PENDING_KAGGLE_EXECUTION`
- `phase4_5/dryrun_results/kaggle_smoke/raw_outputs.jsonl`: `PENDING_KAGGLE_EXECUTION`
- `phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_trials.jsonl`: `PENDING_KAGGLE_EXECUTION`

## 10. Validation Reports
- `phase4_5/validation/phase45_preflight_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_local_dryrun_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_kaggle_smoke_preparation_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_reset_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_grading_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_statistics_smoke_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_forbidden_claims_report.md`: `VERIFIED`
- `phase4_5/validation/phase45_kaggle_quota_feasibility_report.md`: `VERIFIED` (Provisional)
- `phase4_5/validation/phase45_checkpoint_resume_report.md`: `VERIFIED`

## 11. Final Decision Files
- `phase4_5/validation/phase45_final_go_no_go.md`: `VERIFIED`
- `phase4_5/reports/phase45_summary.md`: `VERIFIED`
