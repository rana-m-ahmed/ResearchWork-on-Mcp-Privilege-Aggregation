# Phase 3 Artifact Ingestion Report

**Timestamp (UTC):** 2026-07-04T20:23:18.001778+00:00
**Software Version:** 1.0.0

## Purpose
Parse the Phase 3 final decision and extract model identities and parameters into Phase 4 configs.

## Inputs Evaluated
- phase3/reports/phase3_final_decision.md

## Checks Performed
- File existence
- Hash computation
- Canonical Injection

## Summary
Status: PASS

Phase 3 execution occurred on Kaggle. The repository originally lacked exact model metadata. During Phase 4 protocol freeze the metadata was recovered from the original execution environment. No model identities were inferred. No values were fabricated.

## Failures
No failures detected.

## Warnings
No warnings detected.

## Recommendations
- None

## Evidence Log
```json
{
  "M1": {
    "identifier": "Qwen/Qwen2.5-7B-Instruct",
    "quantization": "float16",
    "file_written": "phase4/configs\\model_1_freeze.yaml"
  },
  "M2": {
    "identifier": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "quantization": "float16",
    "file_written": "phase4/configs\\model_2_freeze.yaml"
  },
  "M3": {
    "identifier": "mistralai/Mistral-7B-Instruct-v0.3",
    "quantization": "float16",
    "file_written": "phase4/configs\\model_3_freeze.yaml"
  },
  "M4": {
    "identifier": "microsoft/Phi-3.5-mini-instruct",
    "quantization": "float16",
    "file_written": "phase4/configs\\model_4_freeze.yaml"
  },
  "model_set": {
    "M1": "Qwen/Qwen2.5-7B-Instruct",
    "M2": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "M3": "mistralai/Mistral-7B-Instruct-v0.3",
    "M4": "microsoft/Phi-3.5-mini-instruct"
  },
  "decision_source_hash": "678d4f8a9290b3c520aa9f58df80b4bb84d87b1ebdd177f30d0da44684a8ebc2"
}
```
