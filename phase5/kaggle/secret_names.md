# P15 Kaggle Secret Names

Use Kaggle Secret names only. Never embed credential values in the notebook.

Required names referenced by the handoff design:

- `GITHUB_READ_TOKEN_PHASE5`
- `GITHUB_WRITE_TOKEN_PHASE5`

Operational notes:

- The read token is for clone and checkout of private sources, if required.
- The write token is for the post-seal GitHub sync path.
- The public CLI consumes credentials only through an ephemeral runtime bridge.
- No secret value is printed, committed, or logged.
