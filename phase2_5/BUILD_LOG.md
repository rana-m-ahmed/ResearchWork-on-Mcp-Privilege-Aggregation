# Phase 2.5 Build and Diagnosis Log

## Sub-Phase A — Environment & Manifest Repair
* Timestamp: 2026-06-29T13:25:00+05:00
* Exact commands run:
  * `mkdir -Force ...`
  * `python env_snapshot.py`
  * `python hash_manifests.py`
  * `python phase2_5\scripts\verify_codebase.py`
* Exact files written/modified:
  * `phase2_5/reproducibility/environment_snapshot.json`
  * `phase2_5/inputs/schema_hashes/schema_hash_manifest.json`
  * `phase2_5/scripts/script_manifest.json`
  * `phase2_5/scripts/verify_codebase.py`
* Self-check result:
  * PASS. `verify_codebase.py` returned exit code 0.

## Step 0: Infrastructure Blocker Diagnosis
- **Observation:** Original pipeline timed out hitting Ollama natively. 
- **Diagnosis:** `ollama version 0.30.11` does not support the `/api/tokenize` endpoint (returns HTTP 404). Attempts to use `/api/generate` with `num_predict: 1` successfully return `prompt_eval_count`, but cold-loading weights on this Tier 3 CPU host takes ~100 seconds per call.
- **Root Cause of Fallback:** Because the native call timed out or 404'd, prior executions silently fell back to `transformers.AutoTokenizer` for both native and library pathways to fake a pass.
- **Resolution:** Formally amended the native pathway to use `/api/generate` with `num_predict: 1`. Pre-warmed the model with a dummy request and raised timeouts to `180s`.

## Step 1: Discrepancy Decomposition
- **Observation:** Condition C1 showed a discrepancy > 10 tokens between Track A (Legacy) and Track B (Library-Fallback).
- **Component Breakdown:** 
  - Track A: Sys(25), Sch(39), Cap(10), Pay(37), Task(22) = Sum(133), Reported Total(128).
  - Track B: Sys(16), Sch(30), Cap(1), Pay(28), Task(13) = Sum(88), Reported Total(113).
- **Diagnosis:** The gap (9 tokens exactly per component) is systemic. Track A's math is internally contradictory (Sum 133 vs Total 128), proving it is wholesale hallucinated. Furthermore, Track A's filename was `c1_d5_m1_tier3_ra.json` for a C1/D1 run due to a script naming bug.
- **Resolution:** Track A data is completely tainted and will be purged and regenerated legitimately via the fixed native pathway. Filename anomaly fixed in `run_phase25.py` and `run_track_b.py`.
