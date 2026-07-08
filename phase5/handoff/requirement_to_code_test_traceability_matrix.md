# P17 Requirement-to-Code/Test Traceability Matrix

| Requirement | Code / Artifact | Test / Evidence | Status |
| --- | --- | --- | --- |
| Keep the Kaggle handoff thin and public-CLI-only. | `phase5/kaggle/handoff.py`, `phase5/kaggle/validation.py`, `phase5/kaggle/phase5_runner.ipynb` | `phase5/tests/test_kaggle_handoff.py`, `phase5/implementation/reports/P15_implementation_report.md` | Covered |
| Keep notebook parameters limited to branch fields and approved operational limits. | `phase5/kaggle/manifests/phase5_runner_parameters.schema.json`, `phase5/kaggle/validation.py` | `phase5/tests/test_kaggle_handoff.py`, `phase5/implementation/reports/P15_notebook_static_validation_report.md` | Covered |
| Preserve gate, seal, sync, reverify, and reseal ordering. | `phase5/kaggle/handoff.py`, `phase5/kaggle/operator_runbook.md` | `phase5/tests/test_kaggle_handoff.py`, `phase5/implementation/reports/P16_local_qualification_report.md` | Covered |
| Expose Kaggle Secret names only, never values. | `phase5/kaggle/secret_names.md`, `phase5/kaggle/handoff.py` | `phase5/tests/test_kaggle_handoff.py`, `phase5/implementation/reports/P15_implementation_report.md` | Covered |
| Keep the candidate source bundle reproducible. | `phase5/handoff/candidate_source_manifest.json`, `phase5/handoff/candidate_source_manifest.md` | This P17 package and the recorded common-source hash | Covered |
| Keep the candidate handoff explicitly non-official. | `phase5/handoff/candidate_kaggle_handoff_manifest.json`, `phase5/handoff/unresolved_risk_registry.md` | `phase5/validation/pre_kaggle_candidate_readiness_report.md` | Covered |
| Preserve the frozen run-plan and batch-manifest linkage. | `phase5/validation/kaggle_run_plan.json`, `phase5/manifests/batch_partition_manifest.json` | `phase5/validation/gate0_authorization_report.md`, `phase5/validation/kaggle_run_plan.md` | Covered |
| Avoid Kaggle execution in the packaging task. | This P17 package | No Kaggle run was executed; see P17 report | Covered |
