#!/bin/bash
# Run Phase 2 adversarial-channel placeholder smoke test
# Uses placeholder payload — NOT Phase 1 approved payloads
# No ASR, no exploit claims, no taxonomy labels
set -e
cd "$(dirname "$0")/.."

PAYLOAD_FILE="configs/placeholder_payload.txt"

echo "[Phase 2] Running adversarial-channel placeholder smoke test..."
echo "  Payload: $PAYLOAD_FILE (PLACEHOLDER — NON-EXPERIMENTAL)"

python -c "
from client.orchestrator import Orchestrator
payload = open('${PAYLOAD_FILE}', 'r').read()
orch = Orchestrator(mode='smoke_test')
for v in ['D3-POISON-TD', 'D5-POISON-TD', 'D3-POISON-CA', 'D5-POISON-CA']:
    r = orch.run_adversarial_channel_smoke(v, placeholder_content=payload)
    print(f'{v}: {r[\"smoke_test_result\"]} | reset={r[\"reset_status\"]}')
print('Adversarial-channel placeholder smoke test complete.')
print('All rows are is_placeholder_payload=true. No ASR/exploit claims.')
"
