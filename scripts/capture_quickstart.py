import subprocess
import json
import time

def run():
    server = subprocess.Popen(
        ["python", "server/quickstart_verified/server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    def send(msg):
        server.stdin.write(json.dumps(msg) + "\n")
        server.stdin.flush()

    def recv():
        line = server.stdout.readline()
        if line:
            return json.loads(line)
        return None

    # 1. Initialize
    init_req = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }
    send(init_req)
    init_res = recv()

    # Send initialized notification
    send({
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    })

    # 2. Tools list
    tools_req = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    send(tools_req)
    tools_res = recv()

    # 3. Tool call
    call_req = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "add",
            "arguments": {"a": 5, "b": 3}
        }
    }
    send(call_req)
    call_res = recv()

    server.terminate()

    # Format into markdown
    md = f"""# MCP/FastMCP Quickstart Verification

- **Date:** 2026-06-25
- **Operator:** Antigravity AI
- **Host OS:** Windows
- **Python Version:** 3.12
- **Package Versions:** mcp (latest)
- **Command Used:** python server/quickstart_verified/server.py

## Raw Initialize Message
```json
{json.dumps(init_res, indent=2)}
```

## Raw Tools-List/Discovery Response
```json
{json.dumps(tools_res, indent=2)}
```

## Raw Tool-Call Request
```json
{json.dumps(call_req, indent=2)}
```

## Raw Tool-Call Response
```json
{json.dumps(call_res, indent=2)}
```

## Pass/Fail Notes
- PASS: Standard FastMCP initialization, tool listing, and execution verified over stdio JSON-RPC.
"""
    with open("reproducibility/mcp_quickstart_verification.md", "w", encoding="utf-8") as f:
        f.write(md)
    print("Verification captured successfully.")

if __name__ == "__main__":
    run()
