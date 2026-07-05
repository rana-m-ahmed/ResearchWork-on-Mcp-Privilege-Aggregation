# Phase 4.5 Kaggle Execution Substrate Note

## Purpose

This note documents the approved execution-substrate adaptation for Phase 4.5.

## Core Commitments

- GitHub is the source of truth.
- Local execution validates repository and pipeline behavior.
- Kaggle is the model-heavy execution platform for smoke checks.
- All Kaggle outputs must return to GitHub.
- This is an approved execution-substrate adaptation, not silent methodology drift.
- Phase 4.5 remains non-official and cannot produce publishable security results.

## Operational Meaning

- Local GitHub work is responsible for scaffolding, validation, hashes, and reports.
- Kaggle work is responsible for smoke execution only.
- No Kaggle artifact becomes official Phase 5 evidence by default.
- No Phase 4.5 result may be described as an ASR, exploit-rate, or defense-effectiveness finding.

## Do Not Commit

- Model weights.
- Caches.
- `.env` files.
- Credentials.
- Local absolute paths.
- Official trial rows.
- `official_trial: true`.
- `counts_for_phase5: true`.
