# Phase 2 Scope Confirmation

- **Phase 2 is infrastructure-only.**
- **Phase 2 does not collect ASR, TID, Critical Exploit counts, taxonomy outcomes, or publishable security results.**
- **Phase 2 uses placeholder-only adversarial-channel material unless Phase 1 approved payloads already exist.**
- **No Phase 2 LLM smoke-test run may ever count toward Phase 3’s competence baseline.**
- **Mode A is the default backend.** (Containerized Ollama/llama.cpp on the same Docker network)
- **Mode B requires a documented exception record if used.** (Host-local model endpoint)

## Model Backend Network Exception Record

- Selected Backend Mode: Mode B — host-local endpoint
- Reason Mode A failed or was impractical:
- Approved local endpoint:
- External network access disabled elsewhere: Yes / No
- Host-isolation network test passed: Yes / No
- Supervisor / reviewer approval:
- Date:
- Applies to: Phase 2 engineering only / Later phases after Phase 4 approval
