# Phase 2 Reproducibility Manifest

**Phase:** phase2_infra | **Non-experimental:** true

## Host Environment

- **Host OS:** Microsoft Windows 11 Pro Education (Build 26200)
- **CPU:** 1 Processor(s) Installed (MECHREVO R14P Series)
- **GPU:** N/A (CPU-only / Integrated)
- **RAM:** 7,583 MB

## Software Versions

- **Docker version:** 29.5.3, build d1c06ef
- **Docker Compose version:** v5.1.4
- **Docker image digests:** 
  - `docker-mcp_server`: sha256:6ae50465d7dad46a9acabd4a702aaf169864eb307d16a7f2b12310c3eb902f3a
  - `docker-orchestrator`: sha256:d857e80f1c4e54af1351dbe3bfa6c61dfa91ed56ca3713bcdd4f57fdce9da57b
- **Python version:** 3.12.10
- **MCP/FastMCP package version:** 1.28.0
- **pytest version:** 9.1.1

## Model Backend

- **Model backend mode:** Mode A (containerized) — default
- **Mode B exception record:** N/A unless Mode B is used (see template in `docs/phase2_scope_confirmation.md`)
- **Ollama/llama.cpp version:** 0.30.10
- **Model name:** llama3.2:1b
- **Model version:** latest
- **Quantization format:** default / native
- **Runtime backend:** ollama
- **Runtime version:** 0.30.10
- **Access date:** 2026-06-25
- **Model hash:** N/A (depends on model provider)

## Inference Parameters

- **Random seed:** N/A
- **Temperature:** default
- **Determinism limitations:** LLM outputs are inherently non-deterministic even with fixed seeds; scripted smoke tests are fully deterministic.

## Schema Hashes

See `reproducibility/schema_hash_ledger.csv` for all 9 variant hashes.

## Prompt Template Hashes

- Computed per-trial and recorded in JSONL `prompt_hash` field.

## Run Information

- **Run timestamp:** 2026-06-25T13:59:00Z
- **Operator name:** Antigravity

## Notes

- Phase 2 is infrastructure-only. No experimental results.
- Verified isolation constraints successfully.
