# Phase 2 Audit Checklist

**Phase:** phase2_infra | **Non-experimental:** true

## Infrastructure Gates

- [x] Repository skeleton created
- [x] Docker safety baseline passed (`scripts/check_docker_safety.sh`)
- [x] Non-root user in Dockerfiles
- [x] No `--privileged` in compose
- [x] No `network_mode: host` in compose
- [x] Read-only filesystem where feasible
- [x] `/tmp/mcp_trial` container-only scratch
- [x] `/output_logs` narrow host mount only

## MCP Server Gates

- [x] FastMCP server uses actual MCP SDK
- [x] Tools registered through FastMCP mechanism
- [x] Discovery exposes only intended tools per density
- [x] `reset` absent from MCP discovery
- [x] `sampling` absent from MCP discovery
- [x] `createMessage` absent from MCP discovery
- [x] Admin/debug tools absent from discovery
- [x] Reset dispatch rejected with unknown-tool error

## Mock Tool Gates

- [x] All 5 tools implemented with mock data only
- [x] No real filesystem access in tools
- [x] No network calls in tools
- [x] No shell execution in tools
- [x] No real credentials in tools
- [x] Deterministic outputs for fixed inputs
- [x] No branching on metadata condition

## Schema Gates

- [x] 9 schema variants created (3 densities x 3 conditions)
- [x] All schemas have `logical_tool_id` and `exposed_tool_name`
- [x] `exposed_tool_name == logical_tool_id` (tool-name poisoning disabled)
- [x] Clean/poisoned diffs are metadata-only
- [x] Schema hashes recorded in `reproducibility/schema_hash_ledger.csv`
- [x] Schema hash consistency verified

## Reset Gates

- [x] Reset clears outbox, event log, trial ID, extra state
- [x] Reset does not switch schema variant
- [x] No state leakage across resets
- [x] Reset not visible in MCP discovery
- [x] Reset dispatch rejected

## Orchestrator Gates

- [x] Mode guard: only `smoke_test` allowed
- [x] Rejects `pilot`, `core`, `official_experiment`
- [x] Unknown/admin/reset tool calls rejected
- [x] JSONL rows include `phase2_infra` and `non_experimental: true`
- [x] SHA-256 computed after JSONL write
- [x] No forbidden labels in logs (ASR, TID, attack_success, etc.)

## Smoke Test Gates

- [x] Scripted smoke test covers D1-CLEAN, D3-CLEAN, D5-CLEAN
- [ ] LLM benign smoke test attempted (requires local model endpoint)
- [x] Adversarial-channel placeholder smoke test uses `is_placeholder_payload: true`
- [x] No ASR/TID/exploit claims in any log

## Scope Gates

- [x] Phase 2 confirmed as infrastructure-only
- [x] No publishable security results
- [x] Phase 2 LLM rows not counted toward Phase 3
- [x] Mode A is default backend
- [x] Mode B documented as exception only
