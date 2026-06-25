#!/bin/bash
# Run Phase 2 LLM benign integration smoke test
# Requires a local model endpoint (Mode A or Mode B)
# NEVER count results toward Phase 3 competence baseline
set -e
cd "$(dirname "$0")/.."

ENDPOINT="${OLLAMA_ENDPOINT:-http://ollama:11434}"
MODEL="${OLLAMA_MODEL:-llama3.2:1b}"
BACKEND_MODE="${BACKEND_MODE:-containerized}"

echo "[Phase 2] Running LLM benign smoke test..."
echo "  Endpoint: $ENDPOINT"
echo "  Model: $MODEL"
echo "  Backend mode: $BACKEND_MODE"

python -c "
from client.orchestrator import Orchestrator
orch = Orchestrator(mode='smoke_test')
for v in ['D1-CLEAN', 'D3-CLEAN', 'D5-CLEAN']:
    r = orch.run_llm_benign_smoke(
        v,
        endpoint='${ENDPOINT}',
        model_name='${MODEL}',
        backend_mode='${BACKEND_MODE}',
    )
    print(f'{v}: {r[\"smoke_test_result\"]} | error={r[\"error_type\"]}')
print('LLM benign smoke test complete.')
print('WARNING: These rows must NEVER be counted toward Phase 3 competence baseline.')
"
