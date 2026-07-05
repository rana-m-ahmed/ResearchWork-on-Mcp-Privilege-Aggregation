# Phase 4.5 Checkpoint Resume Report

## Summary

- Internal status: `PHASE45_SCAFFOLD_COMPLETE`
- Verdict: `PASS`

## Configured Resume Controls

- Trial shard size: `6`
- Checkpoint frequency: every `6` trials
- Partial log location: `phase4_5/dryrun_results/local/partial_trials.jsonl`
- Completed-trial detection: `trial_id` plus row completion marker in the run manifest
- Duplicate trial ID prevention: reject duplicate `trial_id` values unless a rerun suffix is created
- Interrupted-session resume behavior: continue from the next incomplete shard and preserve manifest references
- Invalid-trial rerun policy: assign a new `trial_id` and write a rerun link for the original row reference
- Rerun link format: `phase4_5/dryrun_results/local/reruns/{trial_id}.json`
- Run hash update behavior: recompute the shard hash after each completed shard and roll it into the cumulative hash
- Per-shard manifest behavior: write one manifest per shard plus a cumulative manifest for the whole run

## Boundary

- Phase 4.5 remains non-official.
- Resume controls do not authorize Phase 5 execution.
