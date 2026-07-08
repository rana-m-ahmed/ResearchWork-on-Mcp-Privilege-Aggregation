# Future Non-Official Kaggle Validation Commands

Use these commands only in the later independent audit path.
They are not an authorization to run official Kaggle trials.

1. `python -m phase5 gate0 --strict --root . --report-dir phase5/validation`
1. `python -m phase5 plan-kaggle-runs --timing-report phase4_5/validation/phase45_kaggle_quota_feasibility_report.md --safe-session-hours 7.5 --output phase5/validation/kaggle_run_plan.json`
1. `python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 1 --output phase5/validation/session_seal_report.json`
1. `python -m phase5 run-campaign --model-slot <MODEL_SLOT> --run-id <RUN_ID> --utcdate <YYYYMMDD> --until-safety-horizon --batch-manifest phase5/manifests/batch_partition_manifest.json --run-plan phase5/validation/kaggle_run_plan.json --output phase5/validation/campaign_run_report.json`
1. `python -m phase5 session-close-seal --run-id <RUN_ID> --output phase5/validation/session_close_seal_report.json`
1. `python -m phase5 sync-github --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --manifest <SYNC_MANIFEST_PATH> --allowlist phase5/configs/sync_allowlist.yaml --receipt <SYNC_RECEIPT_PATH>`
1. `python -m phase5 session-reverify --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --receipt <SYNC_RECEIPT_PATH> --output phase5/validation/session_reverify_report.json`
1. `python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 2 --output phase5/validation/session_seal_report.json`
