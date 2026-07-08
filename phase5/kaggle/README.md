# P15 Kaggle Handoff

This directory holds the thin Kaggle-native handoff interface for Phase 5.
The goal is to prepare a future Kaggle validation workflow without running any
official trials in this task.

What lives here:

- `phase5_runner.ipynb`: notebook shell that follows the required stage order;
- `handoff.py`: plan builders and public-CLI wrappers;
- `validation.py`: local static checks for the notebook and schema;
- `manifests/phase5_runner_parameters.schema.json`: editable-parameter schema;
- `operator_runbook.md`: operator checklist and fail-closed sequence;
- `handoff_contract.md`: scope contract and guardrails;
- `secret_names.md`: Kaggle Secret names only, never secret values.

Design rules:

- Keep the notebook thin and deterministic.
- Keep model identity and scientific settings frozen.
- Use public `python -m phase5` commands only for bootstrap, session, sync,
  and finalize flows.
- Do not run Kaggle trials from this task.

The notebook is a handoff interface, not a hidden implementation layer.
