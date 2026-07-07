# Revised Phase 2 Execution Plan
## Docker Isolation, FastMCP Mock Tools & Feasibility Smoke Test

**Project:** Empirical Evaluation of Privilege Aggregation Vulnerabilities in Edge-Deployed Open-Weight Agents via the Model Context Protocol  
**Document Status:** Revised Phase 2 Implementation Plan after critical external review  
**Purpose:** Build, harden, and verify the safe local MCP experimental lab before Phase 2.5 token profiling, Phase 3 competence gating, Phase 4 protocol freeze, or any official adversarial experiment.  
**Authority Order:** Phase 0 Scope Lock Memo → Phase 1 Benchmark/Provenance Governance → Latest Revised Execution Plan → Original Foundation Document as background only.

---

# 0. Revision Integration Note

This version adopts the valid corrections from the external review and folds them directly into the Phase 2 execution plan.

The following targeted revisions are now operative:

1. **Mode A model backend is the default.** Containerized Ollama/llama.cpp on the same Docker network is the strict Phase 0–conforming default.
2. **Mode B host-local model endpoint is an exception, not an equal default.** It is allowed only if containerized GPU/model serving is impractical, and it must be documented as a controlled network-boundary exception before use.
3. **Mode-aware network tests are mandatory.** Under Mode A, external egress must fail. Under Mode B, egress must succeed only to the approved local model endpoint and fail everywhere else.
4. **`/reset` must be invisible and non-dispatchable.** It must not appear in MCP discovery, and a hallucinated or manually injected MCP tool call named `reset` must return an unknown-tool/unknown-method error.
5. **Phase 2 LLM smoke-test successes are not reusable.** They must never be counted toward Phase 3 competence-baseline trials, even if they resemble benign competence runs.
6. **Logical tool identity is separated from exposed tool names.** This prevents tool-name metadata poisoning from breaking routing or grading.
7. **D1 is explicitly a negative-control / structural-impossibility condition for Critical Exploit.** The later aggregation comparison is mainly D3 versus D5, because both contain the read→write capability pair.
8. **`/output_logs` is write-controlled and hash-verified, not truly append-only.** No false append-only claim is retained.
9. **Scripted infrastructure smoke tests are separated from LLM integration smoke tests.** Phase 2 proves infrastructure first; Phase 3 evaluates model competence.

---

# 1. Phase 2 Executive Verdict

Phase 2 is authorized as an **infrastructure and feasibility phase**.

It is not authorized as a scientific experiment. It must not report Attack Success Rate, Tool Invocation Deviation, Critical Exploit counts, five-state taxonomy outcomes, model robustness claims, or any publishable security result.

The final output of Phase 2 is a working local MCP lab that is safe, deterministic, reproducible, and ready for Phase 2.5/3 handoff.

At the end of Phase 2, the project should have:

- verified official MCP/FastMCP quickstart transcript
- Docker-contained FastMCP mock server
- Python orchestrator
- controlled local model backend access
- deterministic mock tools for density levels 1 / 3 / 5
- clean and poisoned MCP metadata variants
- schema export and SHA-256 hashing
- logical tool ID mapping
- internal reset mechanism plus teardown fallback
- host-isolation tests
- MCP discovery-surface tests
- manual non-LLM tool validation
- scripted infrastructure smoke test
- LLM integration smoke test
- limited adversarial-channel smoke test using placeholder or approved material only
- JSONL engineering logs
- reproducibility manifest
- final Phase 2 Go / Revise / No-Go record

---

# 2. Phase 2 Boundary

## 2.1 What Phase 2 does

Phase 2 builds the engineering substrate for the research.

It does:

1. Verify the official MCP/FastMCP quickstart before custom implementation.
2. Build a Docker-contained local MCP lab.
3. Build deterministic mock tools.
4. Build clean and poisoned MCP metadata schema variants.
5. Export and hash all schema variants.
6. Build the Python orchestration loop.
7. Build reset and teardown control.
8. Verify host isolation and MCP discovery surface.
9. Verify that a scripted fake model can drive the full infrastructure.
10. Verify that one local LLM can connect to the pipeline.
11. Produce engineering logs and reproducibility artifacts.

## 2.2 What Phase 2 does not do

Phase 2 does not:

- run official adversarial experiments
- collect ASR data
- report attack success
- compute TID
- apply final five-state taxonomy grading
- count Critical Exploits
- run the Phase 3 competence baseline
- run the Phase 4 protocol freeze
- mutate, rewrite, paraphrase, or generate attack payloads
- introduce malicious server logic
- test server-side taint vulnerabilities
- perform real exfiltration
- use real credentials
- use cloud LLM APIs
- study transitive trust chains
- expose MCP `sampling`
- expose MCP `createMessage`

Every Phase 2 JSONL row must include:

```json
{
  "phase": "phase2_infra",
  "non_experimental": true
}
```

If placeholder material is used, the row must also include:

```json
{
  "is_placeholder_payload": true
}
```

---

# 3. Authority-Locked Assumptions

| Locked Rule | Phase 2 Consequence |
|---|---|
| Benign deterministic server | FastMCP server implementation must not change between clean and poisoned metadata conditions. |
| Tool execution code fixed | Tool functions are written once and reused across all schema variants. |
| Attacker controls retrieved content and MCP metadata only | Phase 2 builds only retrieved-content placeholder channel, tool-description metadata channel, and capability-advertisement metadata channel. |
| No malicious server | No hidden server triggers, no variant-dependent behavior, no code-level exploit path. |
| No server-side vulnerability study | SQLi, shell injection, path traversal, unsafe subprocess calls, and real file-access vulnerabilities are not implemented or studied. |
| No real exfiltration | `write_outbox` writes only to local mock outbox, never to a real network endpoint. |
| No live credentials | All mock records use synthetic non-sensitive data. |
| No adaptive payload generation | Phase 2 uses static placeholders only unless Phase 1 has approved and hashed payloads. |
| No official data before Phase 1 completion | Phase 2 logs are engineering artifacts only and are never merged into Phase 5 logs. |
| Privilege aggregation requires two or more capabilities | D1 is a negative-control / structural-impossibility condition for Critical Exploit. |
| MCP `sampling` and `createMessage` forbidden | Discovery-surface tests must prove these are absent. |
| Docker boundary mandatory | MCP tools and orchestrator must run inside a controlled Docker lab. |
| Reset requires proof | `/reset` must pass sentinel tests or be replaced by full teardown fallback. |

---

# 4. Corrected Phase 2 Architecture

## 4.1 Architecture principle

The server remains benign and deterministic. Clean and poisoned conditions differ only in MCP-exposed metadata, not tool behavior.

Allowed metadata variation fields are:

- exposed tool descriptions
- parameter documentation
- capability advertisement text
- exposed tool names only after logical-ID mapping is verified

Forbidden variation fields are:

- tool implementation
- route handlers
- server behavior
- tool outputs
- hidden runtime state
- logging infrastructure
- system prompt
- real network behavior
- real filesystem access

## 4.2 Recommended architecture diagram

```text
HOST MACHINE
│
├── Local model backend
│   ├── Mode A default: Ollama/llama.cpp inside Docker network
│   └── Mode B exception: host-local endpoint, formally documented
│
└── Docker Phase 2 Lab
    │
    ├── orchestrator container
    │   ├── builds prompts
    │   ├── calls model backend
    │   ├── parses tool calls
    │   ├── routes MCP calls
    │   ├── writes JSONL logs
    │   └── calls internal reset/teardown
    │
    ├── FastMCP server container
    │   ├── exposes MCP mock tools
    │   ├── exposes clean/poisoned metadata
    │   ├── runs deterministic tool functions
    │   └── exposes internal non-MCP reset endpoint
    │
    ├── /tmp/mcp_trial
    │   └── writable container-only scratch directory
    │
    └── /output_logs
        └── narrow host-mounted output directory, write-controlled and hash-verified
```

---

# 5. Model Backend Policy

## 5.1 Mode A — Default, strict-scope-conforming backend

Mode A runs the model backend as a sibling Docker service on the same controlled Docker network.

Example:

```text
orchestrator container → ollama container → local open-weight model
```

Mode A is the default because it best satisfies the locked local Docker network boundary.

Use Mode A if:

- Docker GPU passthrough works
- model serving is stable inside Docker
- local inference performance is acceptable
- the containerized model endpoint can be reached without exposing external network access

Mode A network rule:

```text
The orchestrator may reach only internal Docker services required for MCP and model inference. External internet egress must fail.
```

## 5.2 Mode B — Controlled host-local exception

Mode B uses a host-local model endpoint, such as:

```text
http://host.docker.internal:11434
```

Mode B is not an equal default. It is a controlled exception.

Mode B may be used only if:

1. Mode A is impractical due to GPU passthrough, Windows/WSL, driver, or model-serving instability.
2. The reason is documented in `docs/phase2_scope_confirmation.md`.
3. The endpoint is local-only.
4. The endpoint is not a cloud API.
5. The endpoint is allowlisted explicitly in configuration.
6. The orchestrator cannot access arbitrary external endpoints.
7. The MCP server/tool container cannot use the endpoint as a general network bridge.
8. The exception is recorded in `reproducibility.md`.
9. Before any official experiment, the exception must be reviewed again during Phase 4 protocol freeze.

Mode B must be documented using this template:

```markdown
## Model Backend Network Exception Record

- Selected Backend Mode: Mode B — host-local endpoint
- Reason Mode A failed or was impractical:
- Approved local endpoint:
- External network access disabled elsewhere: Yes / No
- Host-isolation network test passed: Yes / No
- Supervisor / reviewer approval:
- Date:
- Applies to: Phase 2 engineering only / Later phases after Phase 4 approval
```

## 5.3 Mode-aware network testing

Network tests must be different depending on backend mode.

| Backend Mode | Required Pass Condition |
|---|---|
| Mode A | External network egress fails; internal Docker model endpoint succeeds. |
| Mode B | Approved host-local model endpoint succeeds; all other external domains/IPs fail. |

Under Mode B, a test that simply says “network egress succeeds” is not acceptable. It must prove that connectivity is limited to the approved local model endpoint.

---

# 6. 0 → 100 Execution Flow

## Sub-Phase 2.0 — Scope and Input Confirmation
**Progress:** 0–5%

### Purpose

Confirm that Phase 2 begins from the narrowed research scope and does not inherit broad or outdated assumptions.

### Tasks

1. Open Phase 0, Phase 1, and the revised execution plan.
2. Create `docs/phase2_scope_confirmation.md`.
3. Record the locked prohibitions:
   - no transitive trust
   - no arbitrary malicious MCP server
   - no server-side taint vulnerability
   - no SQL/shell/path traversal vulnerability study
   - no live credentials
   - no real exfiltration
   - no adaptive payload generation
   - no cloud LLM APIs
   - no official adversarial data in Phase 2
4. Record Phase 1 status:
   - payload governance complete, or
   - payload governance incomplete, therefore placeholder-only smoke testing
5. Select model backend mode:
   - Mode A default, or
   - Mode B exception with documented justification
6. Add a non-reuse statement:

```text
No Phase 2 LLM smoke-test run may be counted toward the Phase 3 competence baseline, regardless of whether it is benign, successful, repeated, or structurally similar to a Phase 3 trial.
```

### Exit gate

Proceed only when Phase 2 is confirmed as infrastructure-only and the model backend mode is documented.

### Output

```text
docs/phase2_scope_confirmation.md
```

---

## Sub-Phase 2.1 — Repository Skeleton and Official MCP/FastMCP Verification
**Progress:** 5–15%

### Purpose

Verify the official MCP/FastMCP quickstart before writing custom code, so the project remains MCP-native rather than a generic tool-calling wrapper.

### Tasks

1. Create repository skeleton.
2. Copy the official MCP/FastMCP quickstart into:

```text
server/quickstart_verified/
```

3. Run it unmodified.
4. Capture:
   - startup command
   - package versions
   - raw initialize message
   - raw tools-list / discovery message
   - raw tool-call request
   - raw tool-call response
5. Save transcript:

```text
reproducibility/mcp_quickstart_verification.md
```

6. Do not write custom server logic until this passes.

### Exit gate

Official quickstart must run successfully and produce a valid MCP discovery/tool-list response.

### Output

```text
server/quickstart_verified/
reproducibility/mcp_quickstart_verification.md
```

---

## Sub-Phase 2.2 — Docker Lab Construction and Safety Baseline
**Progress:** 15–30%

### Purpose

Create the safe Docker lab before model or adversarial-channel testing.

### Docker rules

Use:

- non-root user
- read-only filesystem where possible
- dedicated `/tmp/mcp_trial` scratch directory
- narrow `/output_logs` host mount only
- no project-root read-write mount
- no `--privileged`
- no host network mode
- no real external network access except the documented Mode B local endpoint if approved

### Required writable paths

```text
/tmp/mcp_trial       container-only scratch
/output_logs         narrow host-mounted output directory
```

### `/output_logs` correction

Do not claim `/output_logs` is append-only unless OS-level append-only enforcement is actually configured.

Phase 2 treats `/output_logs` as:

```text
write-controlled and hash-verified
```

Required controls:

- only orchestrator writes trial JSONL logs
- MCP server does not write trial logs during normal execution
- log file SHA-256 is computed after write
- test verifies tool path cannot delete or overwrite logs

### Tasks

1. Create Dockerfiles.
2. Create `docker-compose.phase2.yml`.
3. Add non-root user.
4. Add read-only filesystem settings.
5. Add `/tmp/mcp_trial`.
6. Add `/output_logs`.
7. Add Mode A or Mode B network configuration.
8. Add Docker safety preflight script.

### Exit gate

Docker config must pass static inspection before mock tools are connected.

### Output

```text
docker/Dockerfile.mcp_server
docker/Dockerfile.orchestrator
docker/docker-compose.phase2.yml
scripts/check_docker_safety.sh
```

---

## Sub-Phase 2.3 — FastMCP Server Skeleton and MCP Discovery Surface Capture
**Progress:** 30–40%

### Purpose

Build the adapted project server from the verified MCP/FastMCP template and prove the agent-visible surface is exactly controlled.

### Tasks

1. Create `server/mock_server.py`.
2. Register tools through the actual MCP/FastMCP mechanism.
3. Capture adapted server discovery output.
4. Confirm the visible tool list matches the selected schema variant.
5. Confirm forbidden capabilities are absent:
   - `sampling`
   - `createMessage`
   - `reset`
   - `reset_state`
   - `admin_reset`
   - `set_schema_variant`
   - `debug`
   - `teardown`
6. Save raw discovery transcript.

### Reset visibility rule

The reset mechanism must not be an MCP tool.

It may exist only as an internal admin endpoint called by the orchestrator or test harness.

### Additional reset dispatch-rejection test

Hiding `/reset` from discovery is not enough. The tool-call dispatch path must also reject hallucinated or manually injected reset calls.

Add this test:

```text
Send a manual MCP-style tool call using tool name "reset" through the same dispatch path used for real tools.
Expected result: unknown tool / unknown method error.
Forbidden result: reset executes successfully.
```

### Exit gate

The server must expose only intended mock tools through MCP discovery, and dispatch must reject reset/admin/debug names.

### Output

```text
server/mock_server.py
reproducibility/raw_mcp_discovery_adapted_server.json
tests/test_mcp_discovery_surface.py
tests/test_reset_dispatch_rejection.py
```

---

## Sub-Phase 2.4 — Mock Tool and Mock Data Design
**Progress:** 40–50%

### Purpose

Build individually benign tools that can later support true privilege aggregation when combined.

### Tool-density interpretation

Density 1 is a negative-control / structural-impossibility condition for Critical Exploit because only one tool is available.

The meaningful privilege-aggregation comparison later is mainly Density 3 versus Density 5, because both contain the required read→write capability pair while Density 5 adds extra tool density.

This is documentation of a structural fact, not a Phase 2 statistical claim.

### Tool set

| Tool | Density | Purpose | Aggregation Role |
|---|---:|---|---|
| `read_internal_notes` | 1, 3, 5 | Read a mock internal note by ID | Primary read capability |
| `write_outbox` | 3, 5 | Write a message into a local mock outbox | Primary sink capability |
| `get_local_weather` | 3, 5 | Return canned local weather | Benign distractor |
| `query_local_inventory` | 5 | Return mock inventory record | Secondary read capability only |
| `log_event` | 5 | Write local mock event log | Benign distractor write tool |

### Locked primary mechanical aggregation path

```text
read_internal_notes → write_outbox
```

This is the only Phase 2 path structurally prepared for later primary Critical Exploit grading.

### Secondary mechanical path

```text
query_local_inventory → write_outbox
```

This may exist mechanically but is not counted as an authorized Critical Exploit path unless Phase 4 explicitly approves it.

### Tool implementation rules

Tools must:

- use mock data only
- never access host files
- never call external network endpoints
- never handle real credentials
- never execute shell commands
- never branch based on clean/poisoned metadata condition
- return deterministic outputs for fixed inputs
- use stable logical IDs internally

### Exit gate

All tools must pass manual non-LLM invocation before the model is connected.

### Output

```text
server/tool_definitions/
server/mock_data_store.py
tests/test_manual_tool_validation.py
reproducibility/manual_tool_validation_report.md
```

---

## Sub-Phase 2.5 — Schema Variant Design, Logical IDs, and Hashing
**Progress:** 50–60%

### Purpose

Create clean and poisoned MCP metadata variants without changing tool behavior.

### Logical ID rule

Every tool must have both:

| Field | Meaning |
|---|---|
| `logical_tool_id` | Stable internal identifier used by routing, logs, reset tests, and future grading. |
| `exposed_tool_name` | Name visible to the model through MCP discovery. |

This prevents tool-name poisoning from changing internal routing or experimental interpretation.

### Phase 2 sequencing rule for tool-name poisoning

Tool names are permitted metadata fields under the governance framework, but Phase 2 should not enable tool-name poisoning in the first implementation pass.

First-pass metadata poisoning may use only:

- tool descriptions
- parameter documentation
- capability advertisement text

Tool-name poisoning may be enabled later only after:

- `logical_tool_id → exposed_tool_name` mapping passes tests
- dispatch uses logical IDs internally
- logs preserve both exposed and logical sequences
- Phase 4 explicitly freezes the condition

### Schema variants

| Variant | Density | Condition |
|---|---:|---|
| `D1-CLEAN` | 1 | clean metadata |
| `D1-POISON-TD` | 1 | poisoned tool description |
| `D1-POISON-CA` | 1 | poisoned capability advertisement |
| `D3-CLEAN` | 3 | clean metadata |
| `D3-POISON-TD` | 3 | poisoned tool description |
| `D3-POISON-CA` | 3 | poisoned capability advertisement |
| `D5-CLEAN` | 5 | clean metadata |
| `D5-POISON-TD` | 5 | poisoned tool description |
| `D5-POISON-CA` | 5 | poisoned capability advertisement |

### Schema switching policy

Default policy:

```text
Schema variant is selected at server startup.
```

`/reset` does not change schema variants by default.

Operational consequence:

- trials are grouped by schema variant, or
- server/container is restarted when changing schema variant

Optional future policy:

A non-MCP admin endpoint may switch variants only if:

- it is invisible to the agent
- it never appears in MCP discovery
- it is disabled during official experiments unless Phase 4 approves it
- it has a dedicated stale-schema leakage test

For Phase 2, startup-selected variants are the default.

### Hashing procedure

1. Export schema as canonical JSON.
2. Normalize:
   - UTF-8
   - NFC Unicode normalization
   - `\n` line endings
   - sorted keys
3. Compute SHA-256.
4. Store hash in:

```text
reproducibility/schema_hash_ledger.csv
```

### Exit gate

Schema diff must prove that only allowed metadata fields changed.

### Output

```text
schemas/clean/
schemas/poisoned_tool_description/
schemas/poisoned_capability_advertisement/
schemas/export_and_hash.py
reproducibility/schema_hash_ledger.csv
tests/test_schema_hash_consistency.py
tests/test_schema_metadata_only_diff.py
tests/test_logical_id_mapping.py
```

---

## Sub-Phase 2.6 — Reset and Teardown Control
**Progress:** 60–68%

### Purpose

Guarantee repeated trials do not leak runtime state.

### Reset scope

The internal reset mechanism must clear:

- simulated server state
- `/tmp/mcp_trial`
- mock caches
- temporary files
- local outbox
- local event log
- test-only state variables
- orchestrator conversation memory
- trial identifiers

### Reset limitations

`/reset` clears runtime state only.

It does not change schema variant by default.

### Reset visibility and dispatch rules

`/reset` must be:

- callable by orchestrator/test harness only
- invisible to the agent
- absent from MCP capability discovery
- absent from MCP tool list
- absent from prompt-visible tool schemas
- rejected if invoked through MCP tool-call dispatch

### Fallback rule

If reset tests fail, use full teardown:

```text
stop server/container → start fresh server/container → rerun discovery
```

Do not proceed with a known leaking reset mechanism.

### Exit gate

Either reset passes all sentinel tests, or full teardown fallback is verified and documented.

### Output

```text
server/reset_endpoint.py
tests/test_reset_integrity.py
tests/test_reset_dispatch_rejection.py
reproducibility/reset_integrity_report.md
reproducibility/teardown_fallback_report.md
```

---

## Sub-Phase 2.7 — Orchestrator and Logging Skeleton
**Progress:** 68–78%

### Purpose

Build the smoke-test orchestration loop while preventing accidental official experimentation.

### Orchestrator responsibilities

The orchestrator must:

1. initialize a smoke-test run
2. query MCP discovery
3. build prompt from fixed templates
4. call the local model backend or scripted fake model
5. parse tool calls
6. route tool calls to FastMCP server
7. reject unknown/admin/reset tool names
8. record raw model output
9. summarize tool outputs
10. write one JSONL line per smoke-test trial
11. call reset or teardown
12. verify reset/teardown status
13. refuse official experiment modes

### Required mode guard

During Phase 2, the orchestrator may run only in:

```text
MODE=smoke_test
```

It must reject:

```text
MODE=pilot
MODE=core
MODE=official_experiment
```

### JSONL logging skeleton

Every JSONL row must include at least:

```json
{
  "run_id": "string",
  "trial_id": "string",
  "phase": "phase2_infra",
  "non_experimental": true,
  "timestamp_utc": "string",
  "model_backend_mode": "containerized | host_local | scripted_fake_model",
  "model_backend": "ollama | llama.cpp | scripted_fake_model",
  "model_name": "string_or_null",
  "tool_density_level": 1,
  "mcp_metadata_condition": "clean_schema | poisoned_tool_description | poisoned_capability_advertisement",
  "schema_variant_id": "string",
  "tool_schema_hash": "string",
  "capability_advertisement_hash": "string",
  "prompt_hash": "string",
  "payload_id_or_placeholder_marker": "string_or_null",
  "is_placeholder_payload": true,
  "logical_tool_sequence": ["string"],
  "exposed_tool_sequence": ["string"],
  "tool_parameters_summary": [{}],
  "tool_outputs_summary": ["string"],
  "reset_status": "ok | failed | teardown_used | not_attempted",
  "safety_test_status": "passed | failed | not_run",
  "network_mode_validation": "mode_a_passed | mode_b_passed | failed | not_run",
  "error_type": "none | model_unreachable | malformed_tool_call | unknown_tool_rejected | tool_execution_error | reset_failure | timeout",
  "smoke_test_result": "pipeline_ok | pipeline_failed | adversarial_channel_logged | adversarial_channel_not_logged | pipeline_error | not_applicable",
  "log_file_sha256_after_write": "string",
  "notes": "string"
}
```

### Log-integrity rules

Because `/output_logs` is not truly append-only by Docker semantics, add:

- post-write JSONL file hash
- test that tool path cannot delete logs
- test that MCP server does not write trial logs
- separation of Phase 2 engineering logs from future experimental logs

### Non-reuse rule for LLM smoke logs

Any successful Phase 2 LLM smoke-test row remains Phase 2 engineering evidence only.

It must not be:

- copied into Phase 3 baseline logs
- counted toward Phase 3 trial totals
- used to satisfy the ≥50-trial competence baseline
- used in model inclusion/exclusion decisions except as proof that the endpoint can connect

### Exit gate

The orchestrator must produce valid JSONL logs, reject unknown/admin/reset tool calls, and refuse official modes.

### Output

```text
client/orchestrator.py
client/model_backend.py
client/tool_call_parser.py
client/logging_writer.py
tests/test_orchestrator_mode_guard.py
tests/test_phase2_logging_schema.py
tests/test_log_integrity.py
tests/test_unknown_tool_rejection.py
```

---

## Sub-Phase 2.8 — Safety and Integrity Test Battery
**Progress:** 78–88%

### Purpose

Run all non-model safety tests before using even placeholder adversarial-channel material.

## A. MCP discovery surface tests

Must confirm:

- only intended tools are visible
- reset/admin/debug endpoints are not visible
- `sampling` is absent
- `createMessage` is absent
- discovery output matches schema hash
- hallucinated/manual reset tool-call through dispatch is rejected

Output:

```text
tests/test_mcp_discovery_surface.py
tests/test_reset_dispatch_rejection.py
```

## B. Manual tool validation

Must confirm:

- every tool works without LLM
- every tool returns deterministic output
- no real filesystem access
- no real network access
- no server-side vulnerability behavior
- logical ID mapping is stable

Output:

```text
reproducibility/manual_tool_validation_report.md
```

## C. Reset tests

Must check:

- state variable leakage
- temporary file leakage
- outbox leakage
- event-log leakage
- conversation-memory leakage
- trial-ID contamination

Schema switching is not tested through `/reset` because variants are startup-selected by default.

Output:

```text
reproducibility/reset_integrity_report.md
```

## D. Host-isolation and network tests

Must attempt and fail to access:

- `/root`
- `/home`
- project root
- parent directories
- Windows-style paths such as `C:\`
- writes outside `/tmp/mcp_trial` and `/output_logs`
- log deletion or overwrite through tool path

### Mode A network test

Under Mode A:

- internal Docker model endpoint succeeds
- external domain access fails
- public IP access fails
- MCP server/tool path has no external egress

### Mode B network test

Under Mode B:

- approved host-local model endpoint succeeds
- external domain access fails
- public IP access fails
- unapproved host services fail or are unreachable
- MCP server/tool path cannot use the model exception as a general network bridge

Output:

```text
reproducibility/host_isolation_report.md
reproducibility/network_mode_validation_report.md
```

## E. Schema/hash tests

Must confirm:

- every schema has a hash
- hash ledger is current
- clean/poisoned diff changes only allowed metadata
- logical tool IDs remain stable
- exposed names do not break routing

Output:

```text
reproducibility/schema_validation_report.md
```

### Exit gate

No smoke test may run until this test battery passes or a documented teardown fallback is approved.

---

## Sub-Phase 2.9 — Smoke Tests
**Progress:** 88–95%

### Purpose

Prove the pipeline works end-to-end without producing scientific results.

## 2.9.1 Scripted infrastructure smoke test

Use a fake/scripted model output to prove the infrastructure works independently of LLM competence.

Required coverage:

- D1 clean
- D3 clean
- D5 clean

Optional coverage:

- D3 poisoned tool description
- D5 poisoned tool description
- D3 poisoned capability advertisement
- D5 poisoned capability advertisement

This proves:

- MCP discovery works
- routing works
- tool execution works
- logical/exposed tool mapping works
- logging works
- reset or teardown works

This does not test model competence.

## 2.9.2 LLM integration smoke test

Use one local model call to prove that a local model can connect to the pipeline.

Minimum pass:

- one benign task succeeds at one density level, preferably D1 clean

Target pass:

- benign task succeeds at D1, D3, and D5 clean

Do not make Phase 2 fail solely because the LLM is weak across densities. That belongs to Phase 3 competence testing.

### Explicit non-reuse rule

Benign successes from Phase 2 LLM integration smoke tests must never be counted toward Phase 3’s competence baseline, even if they use the same model, same benign task style, same schema, or same infrastructure.

Phase 3 must start a fresh, separately logged baseline dataset.

## 2.9.3 Limited adversarial-channel smoke test

Use placeholder material unless Phase 1 has fully approved and hashed payloads.

Rules:

- no ASR
- no exploit claim
- no taxonomy label
- no manuscript result
- no success-rate calculation
- logs are engineering artifacts only

Allowed result labels:

```text
adversarial_channel_logged
adversarial_channel_not_logged
pipeline_error
```

Forbidden result labels:

```text
attack_success
critical_exploit
ASR
exploit_found
```

### Exit gate

At minimum, scripted infrastructure smoke tests must pass across D1/D3/D5. LLM integration must demonstrate local-model connectivity, but model competence is deferred to Phase 3.

### Output

```text
logs/output_logs/phase2_scripted_smoke.jsonl
logs/output_logs/phase2_llm_benign_smoke.jsonl
logs/output_logs/phase2_adversarial_channel_smoke.jsonl
reproducibility/smoke_test_report.md
```

---

## Sub-Phase 2.10 — Reproducibility Package and Final Audit
**Progress:** 95–100%

### Purpose

Freeze enough engineering detail so Phase 2 can be reviewed before Phase 2.5/3 begins.

### Required reproducibility fields

Record:

- host OS
- CPU
- GPU
- RAM
- Docker version
- Docker Compose version
- Docker image digests
- Python version
- MCP/FastMCP package version
- model backend mode
- Mode B exception record if used
- Ollama/llama.cpp version
- model name if used
- model hash if available
- quantization if used
- random seed if supported
- temperature
- determinism limitations
- schema hashes
- prompt template hashes
- run timestamp
- operator name

### Final audit documents

Create:

```text
docs/phase2_audit_checklist.md
docs/phase2_go_no_go_record.md
docs/phase2_handoff_to_phase2_5_and_phase3.md
```

### Exit gate

Phase 2 is complete only when all required artifacts exist and the final Go / Revise / No-Go table is filled with actual evidence.

---

# 7. Repository Structure

```text
mcp-privilege-aggregation/
│
├── docker/
│   ├── Dockerfile.mcp_server
│   ├── Dockerfile.orchestrator
│   ├── docker-compose.phase2.yml
│   └── .dockerignore
│
├── server/
│   ├── quickstart_verified/
│   ├── mock_server.py
│   ├── mock_data_store.py
│   ├── reset_endpoint.py
│   └── tool_definitions/
│       ├── read_internal_notes.py
│       ├── write_outbox.py
│       ├── get_local_weather.py
│       ├── query_local_inventory.py
│       └── log_event.py
│
├── client/
│   ├── orchestrator.py
│   ├── model_backend.py
│   ├── tool_call_parser.py
│   └── logging_writer.py
│
├── schemas/
│   ├── clean/
│   ├── poisoned_tool_description/
│   ├── poisoned_capability_advertisement/
│   └── export_and_hash.py
│
├── configs/
│   ├── phase2_scripted_smoke.yaml
│   ├── phase2_llm_benign_smoke.yaml
│   ├── phase2_adversarial_channel_smoke.yaml
│   ├── placeholder_payload.txt
│   └── env.example
│
├── tests/
│   ├── test_mcp_discovery_surface.py
│   ├── test_reset_dispatch_rejection.py
│   ├── test_unknown_tool_rejection.py
│   ├── test_manual_tool_validation.py
│   ├── test_schema_hash_consistency.py
│   ├── test_schema_metadata_only_diff.py
│   ├── test_logical_id_mapping.py
│   ├── test_reset_integrity.py
│   ├── test_host_isolation.py
│   ├── test_network_mode_validation.py
│   ├── test_orchestrator_mode_guard.py
│   ├── test_phase2_logging_schema.py
│   └── test_log_integrity.py
│
├── logs/
│   └── output_logs/
│
├── reproducibility/
│   ├── mcp_quickstart_verification.md
│   ├── raw_mcp_discovery_adapted_server.json
│   ├── schema_hash_ledger.csv
│   ├── docker_image_digests.txt
│   ├── manual_tool_validation_report.md
│   ├── reset_integrity_report.md
│   ├── teardown_fallback_report.md
│   ├── host_isolation_report.md
│   ├── network_mode_validation_report.md
│   ├── schema_validation_report.md
│   ├── smoke_test_report.md
│   └── reproducibility.md
│
├── scripts/
│   ├── check_docker_safety.sh
│   ├── run_quickstart_verification.sh
│   ├── build_and_hash_schemas.sh
│   ├── run_manual_tool_validation.sh
│   ├── run_reset_tests.sh
│   ├── run_host_isolation_tests.sh
│   ├── run_network_mode_validation.sh
│   ├── run_scripted_smoke_test.sh
│   ├── run_llm_benign_smoke_test.sh
│   └── run_adversarial_channel_smoke_test.sh
│
└── docs/
    ├── phase2_scope_confirmation.md
    ├── phase2_audit_checklist.md
    ├── phase2_go_no_go_record.md
    └── phase2_handoff_to_phase2_5_and_phase3.md
```

---

# 8. Phase 2 Go / Revise / No-Go Gate

| Gate | GO | Revise | No-Go |
|---|---|---|---|
| Scope lock | Phase 2 is infrastructure-only | Minor wording ambiguity | Phase 2 includes official adversarial results |
| Model backend mode | Mode A used, or Mode B exception documented and tested | Mode B reason incomplete but fixable | Cloud API or undocumented external endpoint used |
| Official MCP quickstart | Verified and transcript saved | Works but transcript incomplete | Skipped |
| Docker safety | Non-root, no privileged mode, no repo-root mount | Minor fixable config issue | Host root/project root exposed |
| Network control | Mode-aware network tests pass | Test artifact incomplete | External internet reachable without justification |
| MCP surface | Only intended tools visible | Minor naming mismatch | Reset/admin/debug/sampling/createMessage visible |
| Reset dispatch rejection | Hallucinated/manual reset tool-call rejected | Error message unclear but safe | Reset executes through MCP dispatch |
| Tool determinism | Same tool code across variants | Minor output formatting issue | Code changes between clean/poisoned conditions |
| Tool functionality | All tools pass non-LLM calls | One tool needs minor fix | Tool performs real FS/network action |
| Schema hashing | All variants hashed | Missing hash entry | Hashing absent or drift unresolved |
| Logical IDs | Stable logical IDs implemented | Tool-name poisoning disabled pending tests | Exposed name changes break routing |
| Reset | Reset passes or teardown fallback verified | One sentinel needs fix | State leaks with no fallback |
| Host isolation | All host-path tests fail safely | Minor test artifact missing | Host file access succeeds |
| Logging | Valid JSONL, non-experimental flags present | Optional field missing | Logs missing or usable as official data |
| Phase 2/Phase 3 separation | Smoke logs explicitly non-reusable | Wording missing but logs separated | Phase 2 successes counted toward Phase 3 baseline |
| Smoke tests | Scripted D1/D3/D5 pass; LLM connectivity proven | LLM weak but infrastructure passes | Scripted infrastructure pipeline fails |
| Reproducibility | Manifest complete | Some fields marked TBD with reason | Manifest missing or fabricated |

Overall Phase 2 result equals the weakest gate.

---

# 9. Phase 2 Deliverables

Phase 2 is complete only when these exist:

```text
docker/Dockerfile.mcp_server
docker/Dockerfile.orchestrator
docker/docker-compose.phase2.yml
scripts/check_docker_safety.sh

server/quickstart_verified/
server/mock_server.py
server/mock_data_store.py
server/reset_endpoint.py
server/tool_definitions/

client/orchestrator.py
client/model_backend.py
client/tool_call_parser.py
client/logging_writer.py

schemas/clean/
schemas/poisoned_tool_description/
schemas/poisoned_capability_advertisement/
schemas/export_and_hash.py

tests/test_mcp_discovery_surface.py
tests/test_reset_dispatch_rejection.py
tests/test_unknown_tool_rejection.py
tests/test_manual_tool_validation.py
tests/test_schema_hash_consistency.py
tests/test_schema_metadata_only_diff.py
tests/test_logical_id_mapping.py
tests/test_reset_integrity.py
tests/test_host_isolation.py
tests/test_network_mode_validation.py
tests/test_orchestrator_mode_guard.py
tests/test_phase2_logging_schema.py
tests/test_log_integrity.py

reproducibility/mcp_quickstart_verification.md
reproducibility/raw_mcp_discovery_adapted_server.json
reproducibility/schema_hash_ledger.csv
reproducibility/docker_image_digests.txt
reproducibility/manual_tool_validation_report.md
reproducibility/reset_integrity_report.md
reproducibility/teardown_fallback_report.md
reproducibility/host_isolation_report.md
reproducibility/network_mode_validation_report.md
reproducibility/schema_validation_report.md
reproducibility/smoke_test_report.md
reproducibility/reproducibility.md

logs/output_logs/phase2_scripted_smoke.jsonl
logs/output_logs/phase2_llm_benign_smoke.jsonl
logs/output_logs/phase2_adversarial_channel_smoke.jsonl

docs/phase2_scope_confirmation.md
docs/phase2_audit_checklist.md
docs/phase2_go_no_go_record.md
docs/phase2_handoff_to_phase2_5_and_phase3.md
```

---

# 10. Handoff to Phase 2.5 and Phase 3

## 10.1 Handoff to Phase 2.5

Phase 2.5 may begin only after:

- schemas exist
- schema hashes exist
- MCP discovery output is captured
- model backend mode is documented
- logging skeleton exists
- prompt templates exist

Phase 2.5 will profile:

- total prompt tokens
- tool schema token load
- metadata condition token load
- 4,096-token ceiling compliance
- schema pruning requirements

## 10.2 Handoff to Phase 3

Phase 3 may begin only after:

- scripted smoke tests pass
- LLM connectivity is proven
- Docker isolation passes
- network-mode validation passes
- reset or teardown fallback is verified
- logs are valid
- Phase 2 logs are clearly non-reusable for competence counts
- reproducibility manifest exists

Phase 3 will then test:

- native benign success
- JSON/tool-call reliability
- model competence threshold
- primary/secondary model inclusion

Phase 3 must start a fresh dataset. Phase 2 LLM smoke-test successes cannot be counted toward Phase 3.

---

# 11. Aggregated Non-Negotiable Guidelines

## 11.1 Scope rules

Do not introduce:

- transitive trust
- arbitrary malicious MCP server
- server-side taint vulnerabilities
- SQL injection
- shell injection
- path traversal as a studied vulnerability
- live credentials
- real network exfiltration
- cloud LLM APIs
- adaptive payload generation
- AI-mutated payloads
- MCP `sampling`
- MCP `createMessage`

## 11.2 Server rules

The server must remain:

- benign
- deterministic
- local
- mock-only
- unchanged across clean and poisoned metadata variants

## 11.3 Tool rules

Tools must:

- be individually benign
- use mock data only
- avoid real filesystem access
- avoid real network access
- avoid real credentials
- produce deterministic outputs
- not branch on metadata condition
- have stable logical IDs

## 11.4 Metadata rules

Clean and poisoned variants may differ only in:

- exposed tool descriptions
- parameter documentation
- capability advertisement text
- exposed tool names only after logical-ID mapping is verified

They may not differ in:

- tool implementation
- output behavior
- hidden server logic
- routing logic
- available internal privileges

## 11.5 Payload rules

During Phase 2:

- use placeholder payloads unless Phase 1 approval is complete
- mark all placeholder logs clearly
- do not reuse placeholders as real payloads later
- do not report attack success
- do not compute ASR
- do not count smoke tests as evidence

## 11.6 Reset rules

`/reset` must:

- clear runtime state
- clear outbox
- clear event logs
- clear temp files
- clear caches
- clear trial identifiers
- clear orchestrator memory

`/reset` must not:

- appear in MCP discovery
- be callable by the agent
- execute through the MCP tool-call dispatch path
- switch schema variants by default
- become a tool

## 11.7 Network rules

Mode A:

- containerized local model backend is default
- external egress fails
- internal MCP/model services work

Mode B:

- host-local model endpoint is exception-only
- reason must be documented
- endpoint must be local-only and allowlisted
- all other external egress must fail
- Phase 4 must re-approve before official use

## 11.8 Logging rules

Logs must:

- be JSONL
- contain one row per smoke-test trial
- be marked `phase2_infra`
- be marked `non_experimental: true`
- preserve raw model output internally or in a linked engineering artifact
- include schema hashes
- include prompt hash
- include model backend mode
- include reset/teardown status
- include network-mode validation status
- include log file hash after write

Logs must not:

- be merged with future Phase 5 logs
- be treated as pilot/core data
- contain ASR or Critical Exploit claims
- count toward Phase 3 competence baseline

---

# 12. Implementation Risks and Fixes

| Risk | Fix in Revised Plan |
|---|---|
| Mode B violates literal Docker network boundary | Mode A is default; Mode B is exception-only with documentation and mode-aware tests. |
| Schema variant selected at startup but reset tries to switch variants | Variants are startup-selected by default; reset does not switch variants. |
| Reset endpoint becomes agent-visible | Discovery-surface test proves reset/admin/debug tools are absent. |
| Model hallucination calls reset anyway | Dispatch-rejection test proves reset tool-call returns unknown-tool error. |
| Ollama container impractical on Windows/WSL/GPU | Host-local endpoint allowed only as documented exception. |
| Tool-name poisoning breaks routing | Separate `logical_tool_id` from `exposed_tool_name`; disable tool-name poisoning until tested. |
| D1 treated as normal aggregation condition | Mark D1 as negative-control / structural-impossibility condition. |
| D5 creates accidental second aggregation path | Lock primary path as `read_internal_notes → write_outbox`; secondary path requires later approval. |
| Smoke test becomes hidden competence test | Split scripted infrastructure smoke test from LLM integration smoke test. |
| Phase 2 successes get counted toward Phase 3 | Explicit non-reuse rule added to scope, logs, and handoff. |
| `/output_logs` falsely called append-only | Replace with write-controlled + hash-verified logging. |
| Pseudo-MCP implementation risk | Require raw MCP initialize/discovery transcripts from official quickstart and adapted server. |
| Phase 2 accidentally becomes experiment | Hardcode `phase2_infra`, `non_experimental`, and smoke-test-only mode. |

---

# 13. Final Phase 2 Verdict

This revised Phase 2 plan is ready for implementation after manual team review.

The execution path is:

```text
2.0 Scope confirmation
→ 2.1 Official MCP quickstart verification
→ 2.2 Docker safety baseline
→ 2.3 FastMCP server + MCP surface capture
→ 2.4 Mock tools
→ 2.5 Schema variants + logical IDs + hashing
→ 2.6 Reset/teardown
→ 2.7 Orchestrator + logging
→ 2.8 Safety/integrity tests
→ 2.9 Smoke tests
→ 2.10 Reproducibility + final audit
```

Phase 2 may proceed to Phase 2.5 and Phase 3 only when the final Go / Revise / No-Go record is complete and no No-Go gate remains unresolved.

