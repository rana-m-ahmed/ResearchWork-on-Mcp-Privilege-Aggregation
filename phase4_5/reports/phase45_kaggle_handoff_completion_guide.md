# Phase 4.5 Kaggle Handoff Completion Guide

## A. What has already been completed locally
- Branch: `phase4_5-dryrun-hybrid`
- Commit Hash: `26fceb07944e903889b4c394054cde73881af864`
- Phase 4 freeze verification status: `VERIFIED`
- Scaffold status: `VERIFIED`
- Schema mapping status: `VERIFIED`
- Matrix status: `VERIFIED` (Local and Kaggle matrices generated)
- Local dry-run status: `LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE` (Deferred honestly with schema validation)
- Validation reports generated: Preflight, schema mapping, statistics smoke, forbidden-claims lint, log schema, kaggle prep, etc.
- Dependency lock status: `VERIFIED` (requirements locked)
- Checkpoint/resume status: `VERIFIED`
- Kaggle runner readiness: `VERIFIED`

## B. What remains for Kaggle
1. pull the exact GitHub branch;
2. record the exact commit hash;
3. run:
   ```text
   phase4_5/kaggle/phase45_kaggle_runner.ipynb
   ```
4. install or verify dependencies using:
   ```text
   phase4_5/kaggle/requirements.lock.txt
   phase4_5/configs/phase45_environment_lock.yaml
   ```
5. run all-model Kaggle loader smoke;
6. run expanded Kaggle smoke matrix;
7. ensure D3, D5, POISON_TD, and POISON_CA are covered;
8. ensure all rows remain non-official;
9. export raw logs;
10. export hardware metrics;
11. export reset logs;
12. export invalid-trial and rerun logs;
13. export run hashes and manifests;
14. export Kaggle environment report;
15. export Kaggle execution commit file.

## C. Exact output locations Kaggle partner must return
```text
phase4_5/dryrun_results/kaggle_smoke/trials.jsonl
phase4_5/dryrun_results/kaggle_smoke/raw_prompts.jsonl
phase4_5/dryrun_results/kaggle_smoke/raw_outputs.jsonl
phase4_5/dryrun_results/kaggle_smoke/tool_transcripts.jsonl
phase4_5/dryrun_results/kaggle_smoke/reset_checks.jsonl
phase4_5/dryrun_results/kaggle_smoke/hardware_metrics.jsonl
phase4_5/dryrun_results/kaggle_smoke/failures.jsonl
phase4_5/dryrun_results/kaggle_smoke/invalid_trials.jsonl
phase4_5/dryrun_results/kaggle_smoke/rerun_links.jsonl
phase4_5/dryrun_results/kaggle_smoke/kaggle_environment_report.md
phase4_5/dryrun_results/kaggle_smoke/kaggle_dataset_manifest.md
phase4_5/dryrun_results/kaggle_smoke/kaggle_execution_commit.txt
phase4_5/dryrun_results/kaggle_smoke/run_manifest.json
phase4_5/dryrun_results/kaggle_smoke/run_hashes.json

phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_trials.jsonl
phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_outputs.jsonl
phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_hardware_metrics.jsonl
phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_report.md
```

## D. Commands to run after Kaggle outputs are returned
```bash
python phase4_5/scripts/validate_phase45_schema_mapping.py
python phase4_5/scripts/validate_phase45_logs.py --input phase4_5/dryrun_results/kaggle_smoke/trials.jsonl --report phase4_5/validation/phase45_kaggle_log_schema_report.md
python phase4_5/scripts/smoke_test_phase45_statistics.py
python phase4_5/scripts/lint_phase45_forbidden_claims.py
python phase4_5/scripts/estimate_phase5_kaggle_runtime.py
python phase4_5/scripts/summarize_phase45.py
```

## E. Conditions required before Phase 5
- Phase 4 freeze artifacts valid;
- full schema mapping passes;
- local validation passes or honest deferment is documented;
- Kaggle smoke executed;
- Kaggle smoke covers D3, D5, POISON_TD, POISON_CA;
- Kaggle all-model loader smoke passes;
- Kaggle outputs returned to GitHub;
- Kaggle execution commit recorded;
- logs validate against `phase5_schema_freeze.json`;
- payload references validate;
- token budget validates;
- reset validation passes;
- statistics smoke passes;
- quota feasibility report exists from real Kaggle timings;
- checkpoint/resume strategy exists;
- forbidden-claims lint passes;
- external audit gives `GO_TO_PHASE5`;
- no official Phase 5 rows exist in Phase 4.5.

## F. Correct next branch/tag procedure
Only after Kaggle and external audit pass:
```bash
git tag phase45-passed-kaggle-smoke
git push origin phase45-passed-kaggle-smoke
git checkout -b phase5-official-kaggle-evaluation
```
