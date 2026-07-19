# Phase 5.5 Real-Backend Pretrial Binding Audit

## Scope

The bounded pretrial is a diagnostic qualification run, not official scientific evidence. It uses the real model backend and the v3 MCP treatment contract while remaining excluded from Phase 5 counts, publication evidence, and ASR results.

## Frozen Bounds

- one model slot per notebook;
- one frozen treatment batch;
- three real-backend trials;
- dataset `P5-DV-1.1.0-TREATMENT-V3`;
- parser `phase5.5-parser-v3-mcp-schema`;
- treatment batch manifest `batch_partition_manifest_v3_treatment.json`;
- treatment run plan `kaggle_run_plan_v3_treatment.json`;
- evidence is written outside the checkout and packaged with per-file SHA-256 hashes.

## Pass Conditions

The notebook must compile, the selected branch and exact model identity must match, the v3 source freeze must be an ancestor of the checkout, CUDA and dependencies must pass, the synthetic canary must pass, and the pretrial report must reconcile one processed batch with `resume_required=true`. The pretrial manifest must report `official_trial=false`, `counts_for_phase5=false`, and `publication_evidence=false`.

Pretrial output can reveal model, parser, schema, reset, or infrastructure defects. It cannot authorize official dispatch or be merged as scientific evidence.

