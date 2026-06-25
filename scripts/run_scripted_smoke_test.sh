#!/bin/bash
# Run Phase 2 scripted infrastructure smoke test
# Uses ScriptedFakeModel — no LLM required
# Coverage: D1-CLEAN, D3-CLEAN, D5-CLEAN
set -e
cd "$(dirname "$0")/.."
echo "[Phase 2] Running scripted infrastructure smoke test..."
python -c "
from client.orchestrator import Orchestrator
orch = Orchestrator(mode='smoke_test')
for v in ['D1-CLEAN', 'D3-CLEAN', 'D5-CLEAN']:
    r = orch.run_scripted_smoke(v)
    print(f'{v}: {r[\"smoke_test_result\"]} | reset={r[\"reset_status\"]} | tools={r[\"tool_calls_executed\"]}')
print('Scripted smoke test complete.')
"
