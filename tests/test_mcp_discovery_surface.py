"""
Test: MCP Discovery Surface

Confirms that the FastMCP server exposes ONLY the intended tools for
each density level and that forbidden capabilities are absent.

Forbidden names in discovery:
  reset, reset_state, admin_reset, set_schema_variant,
  debug, teardown, sampling, createMessage
"""

from __future__ import annotations

import pytest

from server.mock_server import build_server, DENSITY_TOOLS

FORBIDDEN_NAMES = {
    "reset", "reset_state", "admin_reset", "set_schema_variant",
    "debug", "teardown", "sampling", "createMessage",
}

# All 9 variants to test
ALL_VARIANTS = [
    "D1-CLEAN", "D1-POISON-TD", "D1-POISON-CA",
    "D3-CLEAN", "D3-POISON-TD", "D3-POISON-CA",
    "D5-CLEAN", "D5-POISON-TD", "D5-POISON-CA",
]


def _get_tool_names(variant_id: str) -> set[str]:
    """Build a server and extract the registered MCP tool names."""
    mcp = build_server(variant_id)
    # FastMCP stores tools in mcp._tool_manager._tools dict
    # The keys are the tool names as registered
    tools = mcp._tool_manager._tools
    return set(tools.keys())


@pytest.mark.parametrize("variant_id", ALL_VARIANTS)
def test_only_intended_tools_visible(variant_id: str) -> None:
    """Verify that only tools for the correct density level are registered."""
    density = int(variant_id.split("-")[0][1:])
    expected = set(DENSITY_TOOLS[density])
    actual = _get_tool_names(variant_id)
    assert actual == expected, (
        f"Variant {variant_id}: expected tools {expected}, got {actual}"
    )


@pytest.mark.parametrize("variant_id", ALL_VARIANTS)
def test_forbidden_names_absent(variant_id: str) -> None:
    """Verify that no forbidden capability names appear in discovery."""
    actual = _get_tool_names(variant_id)
    overlap = actual & FORBIDDEN_NAMES
    assert len(overlap) == 0, (
        f"Variant {variant_id}: forbidden names found in discovery: {overlap}"
    )


@pytest.mark.parametrize("variant_id", ALL_VARIANTS)
def test_no_sampling_capability(variant_id: str) -> None:
    """Verify that 'sampling' is not registered as a tool."""
    assert "sampling" not in _get_tool_names(variant_id)


@pytest.mark.parametrize("variant_id", ALL_VARIANTS)
def test_no_createMessage_capability(variant_id: str) -> None:
    """Verify that 'createMessage' is not registered as a tool."""
    assert "createMessage" not in _get_tool_names(variant_id)


@pytest.mark.parametrize("variant_id", ALL_VARIANTS)
def test_no_reset_in_discovery(variant_id: str) -> None:
    """Verify that 'reset' is not registered as a tool."""
    assert "reset" not in _get_tool_names(variant_id)


def test_density_1_has_one_tool() -> None:
    names = _get_tool_names("D1-CLEAN")
    assert len(names) == 1
    assert "read_internal_notes" in names


def test_density_3_has_three_tools() -> None:
    names = _get_tool_names("D3-CLEAN")
    assert len(names) == 3


def test_density_5_has_five_tools() -> None:
    names = _get_tool_names("D5-CLEAN")
    assert len(names) == 5
