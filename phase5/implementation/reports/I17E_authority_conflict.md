# I17E Authority Conflict

## Status

`BLOCKED_BEFORE_IMPLEMENTATION`

## Requested Scope

The attached I17E specification requires a real official Phase 5 execution
adapter, official `run-batch` and `run-campaign` dispatch, and an operational
official Kaggle notebook. It explicitly prohibits executing official trials.

## Conflicting Repository Authority

The applicable `phase5/AGENTS.md` states:

> Do not add official trial logic, inferential analysis, output repair, or
> nested Docker support here.

The repository-root `AGENTS.md` also requires stopping and documenting a
conflict instead of guessing when a prompt conflicts with a higher-source
artifact.

The requested adapter and official CLI dispatch are official trial logic, so
implementation cannot proceed while both instructions remain active.

## Resolution Required

An authorized repository-governance change must explicitly permit the bounded
I17E implementation under named Phase 5 paths while retaining these limits:

- no official trial execution during implementation or qualification;
- no edits to `phase4/` or `phase4_5/`;
- no changes to frozen scientific settings or artifact values;
- deterministic fake-backend qualification only;
- fail-closed official dispatch and evidence isolation;
- no v3 tag or evidence-branch advancement before external Kaggle qualification
  and independent readiness approval.

After that authority is committed on the implementation base, I17E can resume
in the isolated `phase5/real-official-execution` worktree.

## Repository State

- Isolated worktree: `D:/phase5-real-official-execution`
- Branch: `phase5/real-official-execution`
- Base: `origin/main` at `b48144157d167669511332df4884542f951c1bdc`
- Runtime source changes: none
- Official trials executed: none
- Official tags created: none
- Evidence branches changed: none
