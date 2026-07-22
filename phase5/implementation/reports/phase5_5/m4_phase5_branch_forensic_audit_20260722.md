# M4 Phase 5 Evidence Forensic Audit

## Scope Boundary

This is a Phase 5.5 diagnostic report. It reads the remote `phase5-model-4`
evidence commit `7f4e49a23c2ce2430cca8fd5e75aaaf7f3fbe530` as historical
context only. No Phase 5 evidence or source artifact is copied into the
Phase 5.5 evidence branch.

## Inventory

The remote Phase 5 M4 branch contains 250 attempt directories and 5,001
evidence-related tracked files, including the lineage file. Each attempt has
the lifecycle, prompt, reset, hardware, placement, grading, and hash-index
artifacts. However, `model_outputs.jsonl` is absent for all 250 attempts,
despite being listed as a required artifact in each attempt manifest.

## Results

The Phase 5 lineage contains:

- 250/250 `INVALID` attempts;
- 250/250 `model_generation_timeout at S10: no additional parser detail`;
- 0/250 accepted attempts;
- 0/250 calls counted toward a cell;
- 0/250 raw model-output files;
- 0 finalized batches and 250 remaining attempts/batch work represented by
  five processed 50-row core batches in the campaign report.

The campaign report records a 30,531-second safety-horizon stop, zero accepted
finalized attempts, and zero official batches finalized. The sample hardware
receipt shows two Tesla T4 GPUs and the sample placement receipt shows a valid
two-GPU Phi placement. The sample prompt was 166 tokens with a 512-token output
reservation and passed the input budget check.

## Interpretation

The Phase 5 M4 run did not establish a parser or privilege-aggregation result.
It timed out during S10 model inference before a raw model response was
persisted. The hardware and placement receipts do not indicate a CUDA or model
load failure. The failure is therefore a generation-path failure or runtime
compatibility/performance failure, with evidence capture losing the raw output
because the timeout occurred before output materialization.

This is consistent with the current Phase 5.5 canary: cached generation emits
repeated `图` tokens and uncached generation emits repeated `zeichnis` tokens.
The different token loops show that KV cache changes the failure expression,
but neither mode is semantically usable. The earlier Phase 5 no-cache timeout
does not contradict the Phase 5.5 repeated output; it is the same class of
non-terminating/degenerated generation observed at different timeout and
capture boundaries.

## Non-Comparable Smoke Artifacts

The Phase 5 non-official smoke `PASS` is not M4 semantic evidence. Its loader
used `revision=main` and 4-bit NF4 quantization, while the frozen M4 authority
uses revision `2fe192450127e6a83f7441aef6e3ca586c338b77` and float16. Its
representative synthetic generation matrix was run on M1. M4 official trials
were recorded as zero.

## Decision

Phase 5 historical evidence strengthens the conclusion that M4 is blocked by
the Phi generation/runtime path, not by the Phase 5.5 parser or evidence
aggregation logic. The Phase 5.5 canary must remain fail-closed. No official
M4 execution or research interpretation is authorized until a pinned-float16
M4 path produces a valid semantic canary and persists raw output before the
trial timeout.
