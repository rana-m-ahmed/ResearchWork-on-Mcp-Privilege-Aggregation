"""
Test: Unknown Tool Rejection

Verifies that the orchestrator/tool_call_parser rejects:
  - Admin/reset/debug tool names
  - Unknown tool names not in the active tool set
  - Forbidden tool names from PHASE2.md
"""
import pytest
from client.tool_call_parser import classify_tool_call, FORBIDDEN_TOOL_NAMES
from server.mock_server import DENSITY_TOOLS


VALID_D5_TOOLS = set(DENSITY_TOOLS[5])


class TestClassifyToolCall:
    @pytest.mark.parametrize("name", list(FORBIDDEN_TOOL_NAMES))
    def test_forbidden_tools_classified(self, name):
        result = classify_tool_call(name, VALID_D5_TOOLS)
        assert result == "forbidden"

    def test_valid_tool_classified(self):
        assert classify_tool_call("read_internal_notes", VALID_D5_TOOLS) == "valid"

    def test_unknown_tool_classified(self):
        assert classify_tool_call("nonexistent_tool", VALID_D5_TOOLS) == "unknown"

    def test_sampling_rejected(self):
        # sampling is not in FORBIDDEN_TOOL_NAMES but is unknown
        result = classify_tool_call("sampling", VALID_D5_TOOLS)
        assert result == "unknown"

    def test_createMessage_rejected(self):
        result = classify_tool_call("createMessage", VALID_D5_TOOLS)
        assert result == "unknown"


class TestDensityFiltering:
    def test_d1_rejects_write_outbox(self):
        d1_tools = set(DENSITY_TOOLS[1])
        assert classify_tool_call("write_outbox", d1_tools) == "unknown"

    def test_d3_accepts_write_outbox(self):
        d3_tools = set(DENSITY_TOOLS[3])
        assert classify_tool_call("write_outbox", d3_tools) == "valid"
