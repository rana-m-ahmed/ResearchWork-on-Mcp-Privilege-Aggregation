# P05 Kaggle Run Plan

## Verdict

- Task: `P05`
- Status: `PASS`
- Generated UTC: `2026-07-05T12:56:48.678168Z`
- Dataset version: `P5-DV-1.0.1-A7C91E42`
- Safe session hours: `7.50`
- Safe session seconds: `27000`
- Total targets: `10200`
- Total batches: `204`
- Projected total sessions: `4`
- Projected total GPU hours: `20.36`
- Checkpoint barrier interval: `6` trials

## Timing Evidence
- Timing report: `D:/research-work/ResearchWork-on-Mcp-Privilege-Aggregation/phase4_5/validation/phase45_kaggle_quota_feasibility_report.md`
- Mean trial seconds: `6.81`
- P50 trial seconds: `6.79`
- P95 trial seconds: `7.14`
- Invalid attempt rate: `0.0000`

## Model Plans
- `M1`: targets=2550, batches=51, sessions=1, load=112.42s, status=LOAD_SUCCESS
  - phase5_adversarial_core: `1350`
  - phase5_adversarial_defense: `600`
  - phase5_utility_preservation: `600`
- `M2`: targets=2550, batches=51, sessions=1, load=114.72s, status=LOAD_SUCCESS
  - phase5_adversarial_core: `1350`
  - phase5_adversarial_defense: `600`
  - phase5_utility_preservation: `600`
- `M3`: targets=2550, batches=51, sessions=1, load=166.12s, status=LOAD_SUCCESS
  - phase5_adversarial_core: `1350`
  - phase5_adversarial_defense: `600`
  - phase5_utility_preservation: `600`
- `M4`: targets=2550, batches=51, sessions=1, load=64.33s, status=LOAD_SUCCESS
  - phase5_adversarial_core: `1350`
  - phase5_adversarial_defense: `600`
  - phase5_utility_preservation: `600`

## Sensitivity Scenarios
- `5`s/trial -> `3.54` h/model, `1` sessions/model, `4` total sessions
- `8`s/trial -> `5.67` h/model, `1` sessions/model, `4` total sessions
- `10`s/trial -> `7.08` h/model, `1` sessions/model, `4` total sessions
- `12`s/trial -> `8.50` h/model, `2` sessions/model, `8` total sessions
- `20`s/trial -> `14.17` h/model, `2` sessions/model, `8` total sessions
- `30`s/trial -> `21.25` h/model, `3` sessions/model, `12` total sessions
- `60`s/trial -> `42.50` h/model, `6` sessions/model, `24` total sessions

## Source Evidence
- Timing report: `b9c7bcb0984a7a8a703fdef6d7aa2b786b13a8970beb0e2615b0cea4cf4239b5`
- Kaggle smoke metrics: `a4695ce5194c2b29d3f01d190969c7fbe1aaf25b8b6a529dfa76b18a085c2bb4`
- Model-loader outputs: `22e899e07862df949bbcafcf3efef1d5980b7b2f1979b3c5729d979c7e6c48e6`
- Model-loader trials: `5723e739080e302b028f533aeafa960a8eec5b72c8ec9509bcd4e251868c8eb9`
- Invalid trials: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Failures: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Checkpoint/resume config: `5179194ddefda724865dd5c25dbefd1966c9b5988ebb383bf8abc162cd01cc92`
- M4 loader status reconciliation: `b3893e14ac5203f3021f128ffd4f13f49af19a745eaca74a9a4664d12fefb112`

## Findings
- none

## Batch Manifest
- `phase5/manifests/batch_partition_manifest_v2.json`
- `baa7904da1e71f867e42eaa309c808f7ab7ac338be04a8bf30dd91045e20bfe1`
