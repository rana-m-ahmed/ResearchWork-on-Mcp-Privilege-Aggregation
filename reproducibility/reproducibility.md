# Phase 2 Reproducibility Manifest

**Phase:** phase2_infra | **Non-experimental:** true

## Host Environment

- **Host OS:** TBD (fill before formal run)
- **CPU:** TBD
- **GPU:** TBD
- **RAM:** TBD

## Software Versions

- **Docker version:** TBD
- **Docker Compose version:** TBD
- **Docker image digests:** See `reproducibility/docker_image_digests.txt`
- **Python version:** TBD
- **MCP/FastMCP package version:** TBD
- **pytest version:** TBD

## Model Backend

- **Model backend mode:** Mode A (containerized) — default
- **Mode B exception record:** N/A unless Mode B is used (see template in `docs/phase2_scope_confirmation.md`)
- **Ollama/llama.cpp version:** TBD (reason: not yet deployed for formal run)
- **Model name:** TBD
- **Model version:** TBD
- **Quantization format:** TBD
- **Runtime backend:** TBD
- **Runtime version:** TBD
- **Access date:** TBD
- **Model hash:** TBD (reason: depends on model provider)

## Inference Parameters

- **Random seed:** TBD (reason: depends on backend support)
- **Temperature:** TBD
- **Determinism limitations:** LLM outputs are inherently non-deterministic even with fixed seeds; scripted smoke tests are fully deterministic.

## Schema Hashes

See `reproducibility/schema_hash_ledger.csv` for all 9 variant hashes.

## Prompt Template Hashes

- Computed per-trial and recorded in JSONL `prompt_hash` field.

## Run Information

- **Run timestamp:** TBD
- **Operator name:** TBD

## Notes

- Phase 2 is infrastructure-only. No experimental results.
- All TBD fields will be populated during formal execution.
