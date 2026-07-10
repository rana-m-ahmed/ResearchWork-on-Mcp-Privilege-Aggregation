# Phase 5 Non-Official Infrastructure Validation Runbook (Kaggle)

This runbook outlines the required execution path for the Kaggle validation Notebook, aligning with P15/P16 guidelines and employing the thin-notebook architecture.

## Requirements
1. A Kaggle account.
2. A valid Hugging Face User Access Token (`HF_TOKEN`) with read access to the frozen gated models.
3. A fine-grained GitHub Personal Access Token (`GITHUB_TOKEN`) with strictly scoped content-write access to the repository.

## Pre-Execution Steps

1. Obtain the final SHA from the P18-approved handoff.
2. Create a Kaggle Notebook and import `phase5_kaggle_nonofficial_validation.ipynb`.
3. Turn on **Internet** in the notebook settings.
4. Select an appropriate GPU accelerator (e.g., **GPU P100** or **GPU T4 x2**).
5. Add Kaggle Secrets:
   - **Label:** `HF_TOKEN` -> **Value:** Your Hugging Face token.
   - **Label:** `GITHUB_TOKEN` -> **Value:** Your GitHub fine-grained token.
6. Attach both secrets to the notebook.
7. Add an Environment Variable in Kaggle (or inject it programmatically before the first cell):
   - **Variable Name:** `PHASE5_CANDIDATE_SHA`
   - **Value:** The exact 40-character commit SHA.

## Execution
1. Click **Run All**.
2. Confirm that the notebook prints the exact checked-out SHA matching your `PHASE5_CANDIDATE_SHA`.
3. It will verify dependencies, execute strict Gate 0, run framework validation assertions (`pytest`), and then use the Phase 5 repository utility to perform the D3/D5 synthetic smoke trials and sequentially test M1-M4 loading logic.
4. After finalizing all tests, it will clone a separate evidence copy of the repository and securely commit/push the validation artifacts to the `phase5-kaggle-nonofficial-evidence` branch using `GITHUB_TOKEN`.
5. The final verdict will be printed. It must be `KAGGLE IMPLEMENTATION VERDICT: GO FOR FINAL READINESS AUDIT`.

## Post-Execution
- Inspect the remote `phase5-kaggle-nonofficial-evidence` branch on GitHub to confirm artifacts synchronized correctly.
- You may also manually download the backup ZIP archive `/kaggle/working/phase5_nonofficial_validation_bundle.zip`.
- Revoke or purge the `GITHUB_TOKEN` if you created a temporary one specifically for this run.
