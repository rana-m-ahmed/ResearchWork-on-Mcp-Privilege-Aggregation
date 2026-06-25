"""
Test: Network Mode Validation

Structural tests for Mode A / Mode B network configuration.
Full network-level tests require Docker runtime.

Mode A (default):
  - Internal Docker model endpoint succeeds
  - External domain access fails
  - MCP server/tool path has no external egress

Mode B (exception):
  - Approved host-local model endpoint succeeds
  - External domain access fails
  - MCP server/tool path cannot use model exception as bridge
"""
import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestModeADockerConfig:
    """Verify docker-compose.phase2.yml uses Mode A by default."""

    def _load_compose(self):
        path = os.path.join(PROJECT_ROOT, "docker", "docker-compose.phase2.yml")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def test_no_host_network_mode(self):
        content = self._load_compose()
        assert "network_mode: host" not in content

    def test_uses_bridge_network(self):
        content = self._load_compose()
        assert "phase2_net" in content
        assert "bridge" in content

    def test_no_privileged(self):
        content = self._load_compose()
        assert "privileged: true" not in content


class TestModeBDocumentation:
    """If Mode B is used, verify documentation exists."""

    def test_scope_confirmation_has_mode_b_template(self):
        path = os.path.join(PROJECT_ROOT, "docs", "phase2_scope_confirmation.md")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "Mode B" in content
        assert "Exception Record" in content or "exception" in content.lower()


class TestToolsHaveNoNetworkCapability:
    """Verify tool definition modules cannot make network requests."""

    TOOL_FILES = [
        os.path.join(PROJECT_ROOT, "server", "tool_definitions", f)
        for f in [
            "read_internal_notes.py", "write_outbox.py", "get_local_weather.py",
            "query_local_inventory.py", "log_event.py",
        ]
    ]

    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_network_modules(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        for mod in ["socket", "urllib", "http.client", "requests", "httpx",
                     "aiohttp", "websocket"]:
            assert mod not in source, (
                f"{os.path.basename(tool_file)} references network module {mod}"
            )
