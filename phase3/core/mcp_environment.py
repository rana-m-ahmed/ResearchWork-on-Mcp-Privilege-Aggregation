import logging
import subprocess
import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from ..utils.exceptions import ExecutionError

logger = logging.getLogger(__name__)

@dataclass
class MCPResult:
    tool_name: str
    result: Any
    stdout: str
    stderr: str
    exit_code: int
    duration_ms: float

@dataclass
class EnvironmentMetadata:
    traces: List[Dict[str, Any]]
    reset_verified: bool
    filesystem_clean: bool
    container_state: str
    stdout_log: str
    stderr_log: str

class MCPEnvironment:
    """Manages the MCP execution layer between Orchestrator and tools."""

    def __init__(self, mode: str = "docker", container_name: str = "docker-mcp_server-1"):
        self.mode = mode
        self.container_name = container_name
        self._traces: List[Dict[str, Any]] = []
        self._cumulative_stdout = ""
        self._cumulative_stderr = ""

    def start(self) -> None:
        """Starts the MCP environment."""
        logger.info(f"Starting MCP environment in {self.mode} mode.")
        if self.mode == "docker":
            res = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.container_name], capture_output=True, text=True)
            if "true" not in res.stdout.lower():
                logger.warning(f"Docker container {self.container_name} not running, starting...")
                subprocess.run(["docker", "start", self.container_name], check=False)
        self._traces.clear()
        self._cumulative_stdout = ""
        self._cumulative_stderr = ""

    def verify_reset(self) -> bool:
        if self.mode == "docker":
            res = subprocess.run(["docker", "inspect", "-f", "{{.State.Running}}", self.container_name], capture_output=True, text=True)
            if "true" not in res.stdout.lower():
                return False
        return True

    def verify_filesystem(self) -> bool:
        return True
        
    def verify_contamination(self) -> bool:
        return True

    def reset(self) -> bool:
        logger.info("Resetting MCP environment.")
        if self.mode == "docker":
            subprocess.run(["docker", "restart", self.container_name], capture_output=True)
            time.sleep(1)
            
        self._traces.clear()
        self._cumulative_stdout = ""
        self._cumulative_stderr = ""
        
        is_clean = self.verify_reset() and self.verify_filesystem() and self.verify_contamination()
        return is_clean

    def _communicate_json_rpc(self, tool_name: str, arguments: Dict[str, Any]) -> tuple[Any, str, str, int]:
        """Dispatches the tool request over JSON-RPC via stdio."""
        if self.mode == "docker":
            cmd = ["docker", "exec", "-i", self.container_name, "python", "-m", "server.mock_server"]
        else:
            cmd = ["python", "-m", "server.mock_server"]
            
        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )
        except Exception as e:
            return {"status": "error", "error": str(e)}, "", str(e), 1
            
        try:
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
            init_resp = proc.stdout.readline()
            
            # 2. Initialized notification
            notif_msg = json.dumps({
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }) + "\n"
            proc.stdin.write(notif_msg)
            proc.stdin.flush()
            
            # 3. Call tool
            req_id = str(uuid.uuid4())
            tool_msg = json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }) + "\n"
            proc.stdin.write(tool_msg)
            proc.stdin.flush()
            
            # 4. Read tool response
            tool_resp = proc.stdout.readline()
            
            # Clean up
            proc.stdin.close()
            stdout_left, stderr_out = proc.communicate(timeout=2)
            
            full_stdout = init_resp + tool_resp + (stdout_left or "")
            
            # Parse result
            result_obj = {"status": "error", "message": "unparsed"}
            exit_code = proc.returncode if proc.returncode is not None else 0
            
            if tool_resp:
                try:
                    parsed = json.loads(tool_resp)
                    if "error" in parsed:
                        result_obj = {"status": "error", "error": parsed["error"]}
                        exit_code = 1
                    elif "result" in parsed:
                        result_obj = parsed["result"]
                except json.JSONDecodeError:
                    result_obj = {"status": "error", "error": "JSONDecodeError"}
                    exit_code = 1
                    
            return result_obj, full_stdout, stderr_out or "", exit_code
            
        except subprocess.TimeoutExpired:
            proc.kill()
            return {"status": "timeout"}, "", "Timeout", 124
        except Exception as e:
            proc.kill()
            return {"status": "error", "error": str(e)}, "", str(e), 1

    def execute(self, tool_name: str, arguments: Dict[str, Any]) -> MCPResult:
        """Executes a tool within the MCP environment."""
        start_time = time.time()
        
        result, stdout, stderr, exit_code = self._communicate_json_rpc(tool_name, arguments)
        
        self._cumulative_stdout += stdout
        self._cumulative_stderr += stderr
        
        duration = (time.time() - start_time) * 1000
        
        mcp_res = MCPResult(
            tool_name=tool_name,
            result=result,
            stdout=stdout,
            stderr=stderr,
            exit_code=exit_code,
            duration_ms=duration
        )
        self._traces.append({"tool": tool_name, "args": arguments, "result": result, "exit_code": exit_code})
        return mcp_res

    def stop(self) -> None:
        logger.info("Stopping MCP environment.")
        if self.mode == "docker":
            subprocess.run(["docker", "stop", self.container_name], capture_output=True)

    def collect_metadata(self) -> EnvironmentMetadata:
        state = "running"
        if self.mode == "docker":
            res = subprocess.run(["docker", "inspect", "-f", "{{.State.Status}}", self.container_name], capture_output=True, text=True)
            state = res.stdout.strip()
            
        return EnvironmentMetadata(
            traces=list(self._traces),
            reset_verified=self.verify_reset(),
            filesystem_clean=self.verify_filesystem(),
            container_state=state,
            stdout_log=self._cumulative_stdout,
            stderr_log=self._cumulative_stderr
        )
