# M4 Loader Status Reconciliation

## Verdict

M4 is reconciled to `PASS` for the active official v2 operational plan. The earlier `LOAD_FAILURE` remains preserved as historical evidence and as the pre-I17R active-plan status.

## Binding

- Model slot: `M4`
- Model ID: `microsoft/Phi-3.5-mini-instruct`
- Prior status: `LOAD_FAILURE`
- Final non-official Kaggle status: `PASS`
- Active official run-plan status: `LOAD_SUCCESS`
- Executed source commit: `6e2cafe989ce60572a868b9a31dbcd0b6a1f8898`
- Executed `run_kaggle_smoke.py` SHA-256: `c708cd3c6eab21a420384025290d1a6fc2f4122a3cb644b88261e65c5e717a4d`
- Real synthetic generation: `PASS`
- Official trials executed: `0`
- Machine-readable record SHA-256: `b3893e14ac5203f3021f128ffd4f13f49af19a745eaca74a9a4664d12fefb112`

## Occurrence Classification

| Occurrence | Classification |
| --- | --- |
| `phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_trials.jsonl` | `HISTORICAL_PRE_KAGGLE_STATUS` |
| `phase5/validation/kaggle_run_plan.json` | `ACTIVE_OFFICIAL_RUN_PLAN_STATUS_BEFORE_I17R` |
| `phase5/validation/kaggle_run_plan.md` | `ACTIVE_OFFICIAL_RUN_PLAN_STATUS_BEFORE_I17R` |
| `phase5/implementation/reports/P05_implementation_report.md` | `HISTORICAL_PRE_KAGGLE_STATUS` |
| `phase5/handoff/candidate_kaggle_handoff_manifest.json` | `HISTORICAL_PRE_KAGGLE_STATUS` |

## Active Authority

The active official launch handoff uses `phase5/validation/kaggle_run_plan_v2.json`, where M4 is `LOAD_SUCCESS` based on the non-official Kaggle PASS evidence above.
