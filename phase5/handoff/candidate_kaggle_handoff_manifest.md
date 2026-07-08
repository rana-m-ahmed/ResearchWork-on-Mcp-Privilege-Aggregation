# Candidate Kaggle Handoff Manifest

- Candidate status: `READY_FOR_INDEPENDENT_PRE_KAGGLE_AUDIT`
- Official ready: `false`
- Generated UTC: `2026-07-08T15:43:30.3108894Z`
- Source commit: `d9cdb073aa343824823c4eb9e8d8db2bbb5c0071`
- Source manifest: `phase5/handoff/candidate_source_manifest.json`
- Common-source hash: `280cf05bcdcb459b589dc1f036d7cffd51ca58406f53a975bb1e3271fff95cb3`

## Required Kaggle Secret Names

- `GITHUB_READ_TOKEN_PHASE5`
- `GITHUB_WRITE_TOKEN_PHASE5`

## Frozen Evidence Consumed

- `phase5/validation/gate0_authorization_report.json` `38284f6526da36eebca20ba9d1ff2c8c45351acdadbd20b61b6865f55d670c97`
- `phase5/validation/kaggle_run_plan.json` `edbaf655fb8e771d757bffcf2e62884ab3ab88c9e1a3ca019ec33bae0898e549`
- `phase5/implementation/reports/P16_local_qualification_report.json` `1339fd8625259efbb823ad92d0c2cec5ba2a911f5229562f1fd9e2389b2efd15`

## Future Non-Official Validation Commands

- `python -m phase5 gate0 --strict --root . --report-dir phase5/validation`
- `python -m phase5 plan-kaggle-runs --timing-report phase4_5/validation/phase45_kaggle_quota_feasibility_report.md --safe-session-hours 7.5 --output phase5/validation/kaggle_run_plan.json`
- `python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 1 --output phase5/validation/session_seal_report.json`
- `python -m phase5 run-campaign --model-slot <MODEL_SLOT> --run-id <RUN_ID> --utcdate <YYYYMMDD> --until-safety-horizon --batch-manifest phase5/manifests/batch_partition_manifest.json --run-plan phase5/validation/kaggle_run_plan.json --output phase5/validation/campaign_run_report.json`
- `python -m phase5 session-close-seal --run-id <RUN_ID> --output phase5/validation/session_close_seal_report.json`
- `python -m phase5 sync-github --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --manifest <SYNC_MANIFEST_PATH> --allowlist phase5/configs/sync_allowlist.yaml --receipt <SYNC_RECEIPT_PATH>`
- `python -m phase5 session-reverify --repo /kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation --receipt <SYNC_RECEIPT_PATH> --output phase5/validation/session_reverify_report.json`
- `python -m phase5 session-seal --run-id <RUN_ID> --seal-epoch 2 --output phase5/validation/session_seal_report.json`

## Unresolved Risks

- `kaggle-not-run`: open, info severity, deferred to the future audit.
- `m4-loader-smoke-failure`: open, medium severity, inherited from the frozen run-plan evidence.

## Guardrails

- Do not reclassify this package as official-ready.
- Do not run Kaggle from this task.
- Keep final authorization deferred to P18.
