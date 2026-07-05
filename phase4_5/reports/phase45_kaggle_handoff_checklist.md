# Phase 4.5 Kaggle Handoff Checklist

1. Pull the exact GitHub branch: `phase4_5-dryrun-hybrid`.
2. Record the commit hash before running anything.
3. Run `phase4_5/kaggle/phase45_kaggle_runner.ipynb`.
4. Install from `phase4_5/kaggle/requirements.lock.txt`.
5. Verify the runtime against `phase4_5/configs/phase45_environment_lock.yaml`.
6. Run all-model Kaggle loader smoke.
7. Run the expanded Kaggle smoke matrix.
8. Export all raw logs.
9. Return outputs to GitHub under:
   - `phase4_5/dryrun_results/kaggle_smoke/`
   - `phase4_5/dryrun_results/kaggle_model_loader_smoke/`
10. Run local validators on the returned Kaggle outputs.
11. Produce the quota feasibility report.
12. Do the external audit.
13. Only then tag `phase45-passed-kaggle-smoke`.

## Boundary

- Do not create official Phase 5 results here.
- Do not report ASR, exploit rates, vulnerability confirmation, or defense effectiveness.
