import json
import subprocess
import sys

proc = subprocess.Popen(
    ["python", "-m", "server.mock_server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

# 1. Initialize
init_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "phase3", "version": "1.0"}
    }
}) + "\n"
proc.stdin.write(init_msg)
proc.stdin.flush()

out1 = proc.stdout.readline()
print("INIT RESPONSE:", out1)

# 2. Initialized notification
notif_msg = json.dumps({
    "jsonrpc": "2.0",
    "method": "notifications/initialized"
}) + "\n"
proc.stdin.write(notif_msg)
proc.stdin.flush()

# 3. Call tool
tool_msg = json.dumps({
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "get_local_weather",
        "arguments": {}
    }
}) + "\n"
proc.stdin.write(tool_msg)
proc.stdin.flush()

out2 = proc.stdout.readline()
print("TOOL RESPONSE:", out2)

proc.terminate()
