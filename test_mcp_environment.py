import unittest
from unittest.mock import patch, MagicMock
import subprocess
from phase3.core.mcp_environment import MCPEnvironment, MCPResult

class TestMCPEnvironment(unittest.TestCase):
    
    @patch('subprocess.run')
    def test_start_docker_not_running(self, mock_run):
        # Mock inspect returning false, then start
        mock_inspect = MagicMock()
        mock_inspect.stdout = "false"
        mock_start = MagicMock()
        mock_run.side_effect = [mock_inspect, mock_start]
        
        env = MCPEnvironment(mode="docker", container_name="test_container")
        env.start()
        
        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_called_with(["docker", "start", "test_container"], check=False)

    @patch('subprocess.run')
    def test_start_host_local(self, mock_run):
        env = MCPEnvironment(mode="host-local")
        env.start()
        mock_run.assert_not_called()

    @patch('subprocess.run')
    def test_reset_docker(self, mock_run):
        env = MCPEnvironment(mode="docker", container_name="test_container")
        mock_inspect = MagicMock()
        mock_inspect.stdout = "true"
        # Restart then inspect
        mock_run.side_effect = [MagicMock(), mock_inspect]
        
        result = env.reset()
        self.assertTrue(result)
        self.assertEqual(mock_run.call_count, 2)

    @patch('subprocess.run')
    def test_execute_docker(self, mock_run):
        env = MCPEnvironment(mode="docker", container_name="test_container")
        mock_exec = MagicMock()
        mock_exec.stdout = "Executed get_weather"
        mock_exec.stderr = ""
        mock_exec.returncode = 0
        mock_run.return_value = mock_exec
        
        res = env.execute("get_weather", {"location": "NYC"})
        
        self.assertEqual(res.tool_name, "get_weather")
        self.assertEqual(res.exit_code, 0)
        self.assertEqual(res.stdout, "Executed get_weather")
        self.assertEqual(len(env._traces), 1)

    def test_execute_host_local(self):
        env = MCPEnvironment(mode="host-local")
        res = env.execute("read_file", {"path": "/etc/passwd"})
        
        self.assertEqual(res.tool_name, "read_file")
        self.assertEqual(res.exit_code, 0)
        self.assertTrue("read_file" in res.stdout)
        self.assertEqual(len(env._traces), 1)

    @patch('subprocess.run')
    def test_collect_metadata(self, mock_run):
        env = MCPEnvironment(mode="docker", container_name="test_container")
        mock_status = MagicMock()
        mock_status.stdout = "exited"
        mock_inspect = MagicMock()
        mock_inspect.stdout = "false"
        mock_run.side_effect = [mock_status, mock_inspect]
        
        # Manually add a trace
        env._traces.append({"tool": "test", "result": "ok"})
        env._cumulative_stdout = "test log"
        
        meta = env.collect_metadata()
        self.assertEqual(len(meta.traces), 1)
        self.assertFalse(meta.reset_verified)
        self.assertEqual(meta.container_state, "exited")
        self.assertEqual(meta.stdout_log, "test log")

if __name__ == '__main__':
    unittest.main()
