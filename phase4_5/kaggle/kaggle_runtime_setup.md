# Kaggle Runtime Setup

## Runtime Contract

- GitHub remains the source of truth.
- Kaggle runs the model-heavy smoke workload only.
- The runner must remain aligned with the Python module in this directory.
- Kaggle outputs must be returned to GitHub for review and archiving.

## Scope

- Smoke preparation only.
- No official trial rows.
- No ASR calculations.
- No defense-effectiveness claims.
- No vulnerability claims.

## Operational Notes

- Keep the notebook thin.
- Keep manual edits out of the notebook cell logic.
- Treat any smoke artifact as non-official evidence.
