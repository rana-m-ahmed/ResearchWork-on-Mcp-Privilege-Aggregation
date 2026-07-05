# Phase 4.5 Evidence Integrity Manifest

## Phase 4 Frozen Artifacts
- `phase4/configs/phase5_schema_freeze.json` - VERIFIED (b26ae0025cca7a64a5578af7f63afdd30498116d2b7b7a0ef9fb558b8b8a05ed)
- `phase4/configs/model_set_freeze.yaml` - VERIFIED (686c112ebfc8e7790098b26454504edd385ee6a21ab41d636949afb7f1a05d0d)
- `phase4/configs/payload_reference_map.json` - VERIFIED (0bcd7301edcfc372bf66723391c05a0af6ec4f5ee0da981304552a31056c7b37)
- `phase4/configs/statistical_plan.yaml` - VERIFIED (aad0afdd8f395ecdd4853e737782c487e3b3207730e3496c9e7b4d1ddb558a07)
- `phase4/configs/defense_config_freeze.yaml` - VERIFIED (5934137bd5e741b1ce700879691040d215648b409316c3cf09bc559b098d47a8)
- `phase4/frozen_bundle/phase5_execution_manifest.json` - VERIFIED (150a91281d92571b31e45d9e1797f76f107ddcf8a0565d7ef1bd853c0f147b64)
- `phase4/frozen_bundle/cryptographic_lock_manifest.json` - VERIFIED (0f23876bbbe48425bc4420c805cbb0271704494cc62fa902c9a76e48b10dfbaf)
- `phase4/frozen_bundle/master_hash_ledger.csv` - VERIFIED (d4a7794ee23797659c69de5db99ed35a69026819c46ee306b06474bdedd7d11b)
- `phase4/frozen_bundle/trial_order_core.csv` - VERIFIED (322369477f4a2d080092995bd7fd800bc2107cb506eb530f156fdbc31a4a7208)
- `phase4/frozen_bundle/trial_order_defense.csv` - VERIFIED (cd483dcece127f48ff911239dfc1ee68c2696aaaec384a495c617d76cb53d182)
- `phase4/reports/phase4_go_no_go_decision.md` - VERIFIED (ef870f38be8f156afc671f0c02d92c7e51899d03187f21233bd8e4ff47b29256)

## Phase 4.5 Scaffold
- `phase4_5/README.md` - VERIFIED
- `docs/phase45_kaggle_execution_substrate_note.md` - VERIFIED
- `phase4_5/configs/phase45_local_dryrun.yaml` - VERIFIED
- `phase4_5/configs/phase45_kaggle_smoke.yaml` - VERIFIED
- `phase4_5/configs/phase45_selected_model.yaml` - VERIFIED
- `phase4_5/configs/phase45_schema_mapping.yaml` - VERIFIED
- `phase4_5/configs/phase45_status_enum.yaml` - VERIFIED
- `phase4_5/configs/phase45_environment_lock.yaml` - VERIFIED
- `phase4_5/configs/phase45_checkpoint_resume.yaml` - VERIFIED
- `phase4_5/kaggle/requirements.lock.txt` - VERIFIED
- `phase4_5/kaggle/phase45_kaggle_executor.py` - VERIFIED

## Schema Mapping
- `phase4_5/validation/phase45_schema_mapping_report.md` - VERIFIED (Output confirmed zero unmapped fields).

## Matrices
- `phase4_5/matrices/phase45_local_dryrun_matrix.csv` - VERIFIED (24 rows, no official flags).
- `phase4_5/matrices/phase45_kaggle_smoke_matrix.csv` - VERIFIED (8 rows, covers D3, D5, POISON_TD, POISON_CA, multiple attack families).
- `phase4_5/matrices/phase45_remaining_model_loader_smoke_kaggle.csv` - VERIFIED (Contains M1, M2, M3, M4).

## Local Evidence
- `phase4_5/dryrun_results/local/trials.jsonl` - VERIFIED (Local deferment to scaffold only documented in final Go/No-Go. Scaffold schema passed).

## Kaggle Smoke Evidence
- `phase4_5/dryrun_results/kaggle_smoke/trials.jsonl` - VERIFIED (No official rows. Schema validated).
- `phase4_5/dryrun_results/kaggle_smoke/raw_prompts.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/raw_outputs.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/tool_transcripts.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/hardware_metrics.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/reset_checks.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/failures.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/invalid_trials.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/rerun_links.jsonl` - VERIFIED
- `phase4_5/dryrun_results/kaggle_smoke/run_manifest.json` - VERIFIED

## Kaggle Model-Loader Evidence
- `phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_trials.jsonl` - VERIFIED (Shows M1, M2, M3, M4).
- `phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_hardware_metrics.jsonl` - VERIFIED (Contains peak VRAM and load time).
- `phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_outputs.jsonl` - VERIFIED

## Environment Evidence
- `phase4_5/configs/phase45_environment_lock.yaml` - VERIFIED
- `phase4_5/kaggle/requirements.lock.txt` - VERIFIED

## Runtime/Quota Evidence
- `phase4_5/validation/phase45_kaggle_quota_feasibility_report.md` - VERIFIED (Calculated ~10.5 hours for core Phase 5 based on 6.81s mean inference).

## Checkpoint/Resume Evidence
- `phase4_5/configs/phase45_checkpoint_resume.yaml` - VERIFIED

## Statistics/Lint Evidence
- `phase4_5/validation/phase45_statistics_smoke_report.md` - VERIFIED (Passed, no official claims).
- `phase4_5/validation/phase45_forbidden_claims_report.md` - VERIFIED (Passed, 0 violations).

## Final Decision Evidence
- `phase4_5/validation/phase45_final_go_no_go.md` - VERIFIED (Verdict: READY_FOR_EXTERNAL_AUDIT).

## External Audit Evidence
- Pending creation by this agent execution.
