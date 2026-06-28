# Phase 3: Benign Competence Evaluation

This directory contains the Phase 3 scaffold for the MCP privilege aggregation research project.

## Non-Negotiable Phase Boundary
Phase 3 is benign competence only.
Do not implement or report:
- Attack Success Rate
- Tool Invocation Deviation under adversarial pressure
- Critical Exploit counts
- five-state adversarial taxonomy
- attack success
- vulnerability claims
- robustness claims
- defense claims

Every official Phase 3 trial must include the following metadata:
```json
{
  "phase": "phase3_competence",
  "security_evaluation": false,
  "benign_competence_only": true,
  "adversarial_payload_present": false,
  "phase1_payload_hash": null,
  "payload_condition": "NONE_PHASE3_BENIGN"
}
```

## Scientific Question
> Can each of four local open-weight models perform clean, benign MCP tool use reliably across D1, D3, and D5 tool-density contexts and CLEAN_SURFACE, TD_SURFACE, and CA_SURFACE metadata layouts before adversarial protocol freeze?

## Trial Matrix
Target: 50 valid accepted trials per cell, 9 cells per model, 4 models = 1,800 valid accepted official trials total.
Plus 10 warmups per model (official_trial = false, warmup = true).

TODO_BEFORE_OFFICIAL_RUN: Complete any remaining environment specifics in the matrix CSVs.
