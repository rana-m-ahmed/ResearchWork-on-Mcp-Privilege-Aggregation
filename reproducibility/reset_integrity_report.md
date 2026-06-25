# Reset Integrity Report

**Phase:** phase2_infra
**Non-experimental:** true

## Reset Scope

The internal reset mechanism clears:
- [☐] Simulated server state (runtime_state)
- [☐] /tmp/mcp_trial scratch files
- [☐] Mock caches
- [☐] Temporary files
- [☐] Local outbox
- [☐] Local event log
- [☐] Test-only state variables
- [☐] Trial identifiers

## Reset Visibility Rules

- [☐] /reset is NOT an MCP tool
- [☐] /reset does NOT appear in MCP discovery
- [☐] /reset dispatch is rejected with unknown-tool error
- [☐] /reset does NOT switch schema variant

## State Leakage Tests

- [☐] No outbox leakage across resets
- [☐] No event log leakage across resets
- [☐] No trial ID contamination
- [☐] No extra-state leakage

## Test Results
- Date:
- Operator:
- pytest output:

## Notes
-
