"""
Test: Reset Dispatch Rejection

Verifies that manually invoking a tool call named "reset" through the
same MCP tool-call dispatch path used for real tools returns an
unknown-tool / unknown-method error — NOT a successful reset.

From PHASE2.md §2.3:
  "Hiding /reset from discovery is not enough. The tool-call dispatch
   path must also reject hallucinated or manually injected reset calls."
"""

from __future__ import annotations

import pytest

from server.mock_server import build_server

ADMIN_TOOL_NAMES = [
    "reset",
    "reset_state",
    "admin_reset",
    "set_schema_variant",
    "debug",
    "teardown",
]


@pytest.mark.parametrize("tool_name", ADMIN_TOOL_NAMES)
def test_dispatch_rejects_admin_tool(tool_name: str) -> None:
    """Attempting to call an admin/reset tool through MCP dispatch must fail."""
    mcp = build_server("D5-CLEAN")
    # Attempt to look up the tool — it should not exist
    tools = mcp._tool_manager._tools
    assert tool_name not in tools, (
        f"Tool '{tool_name}' must not be registered in MCP dispatch"
    )


@pytest.mark.parametrize("tool_name", ADMIN_TOOL_NAMES)
@pytest.mark.asyncio
async def test_dispatch_call_returns_error(tool_name: str) -> None:
    """Calling a non-existent admin tool through FastMCP must raise an error."""
    mcp = build_server("D5-CLEAN")
    # FastMCP's call_tool raises a ToolError or KeyError for unknown tools
    with pytest.raises(Exception) as exc_info:
        await mcp.call_tool(tool_name, arguments={})
    # The error should indicate unknown tool, not a successful execution
    error_text = str(exc_info.value).lower()
    assert any(kw in error_text for kw in ("unknown", "not found", "error", "tool")), (
        f"Expected unknown-tool error, got: {exc_info.value}"
    )


def test_reset_not_registered_any_density() -> None:
    """Confirm 'reset' is absent from MCP tools at every density level."""
    for variant in ["D1-CLEAN", "D3-CLEAN", "D5-CLEAN"]:
        mcp = build_server(variant)
        tools = mcp._tool_manager._tools
        assert "reset" not in tools, (
            f"'reset' found in {variant} tool registry"
        )
