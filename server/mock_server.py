"""
Phase 2 FastMCP Server Skeleton.

Uses the official MCP Python SDK (FastMCP) to register tools through the
actual MCP mechanism.  The server is benign and deterministic.

Key design rules (from PHASE2.md):
  - Tool execution code is identical across clean/poisoned metadata variants.
  - Clean/poisoned variants differ ONLY in MCP-exposed metadata
    (descriptions, parameter docs, capability advertisement text).
  - /reset is NOT an MCP tool.  It is an internal admin endpoint only.
  - sampling and createMessage are NOT exposed.
  - Tool-name poisoning is disabled: exposed_tool_name == logical_tool_id.
  - Schema variant is selected at server startup via environment variable.

Usage:
  SCHEMA_VARIANT=D3-CLEAN python -m server.mock_server
"""

from __future__ import annotations

import json
import os
import sys

from mcp.server.fastmcp import FastMCP

from server.tool_definitions import read_internal_notes
from server.tool_definitions import write_outbox
from server.tool_definitions import get_local_weather
from server.tool_definitions import query_local_inventory
from server.tool_definitions import log_event
from server.mock_data_store import runtime_state

# ---------------------------------------------------------------------------
# Density-level tool membership
# ---------------------------------------------------------------------------

DENSITY_TOOLS: dict[int, list[str]] = {
    1: ["read_internal_notes"],
    3: ["read_internal_notes", "write_outbox", "get_local_weather"],
    5: ["read_internal_notes", "write_outbox", "get_local_weather",
        "query_local_inventory", "log_event"],
}

# Map logical_tool_id → module
_TOOL_MODULES = {
    "read_internal_notes": read_internal_notes,
    "write_outbox": write_outbox,
    "get_local_weather": get_local_weather,
    "query_local_inventory": query_local_inventory,
    "log_event": log_event,
}

# ---------------------------------------------------------------------------
# Schema loading
# ---------------------------------------------------------------------------

def _load_schema(variant_id: str) -> dict:
    """Load a schema variant JSON from the schemas/ directory tree.

    Expected variant IDs:  D1-CLEAN, D3-CLEAN, D5-CLEAN,
    D1-POISON-TD, D3-POISON-TD, D5-POISON-TD,
    D1-POISON-CA, D3-POISON-CA, D5-POISON-CA
    """
    parts = variant_id.split("-", 1)
    density_str = parts[0]  # e.g. "D1"
    condition = parts[1] if len(parts) > 1 else "CLEAN"

    density_file = f"density{density_str[1:]}.json"

    condition_upper = condition.upper()
    if condition_upper == "CLEAN":
        schema_dir = "schemas/clean"
    elif condition_upper == "POISON-TD":
        schema_dir = "schemas/poisoned_tool_description"
    elif condition_upper == "POISON-CA":
        schema_dir = "schemas/poisoned_capability_advertisement"
    else:
        raise ValueError(f"Unknown schema condition: {condition}")

    schema_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        schema_dir,
        density_file,
    )
    with open(schema_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _extract_density_level(variant_id: str) -> int:
    """Extract density number from variant ID like 'D3-CLEAN'."""
    return int(variant_id.split("-")[0][1:])


# ---------------------------------------------------------------------------
# Server construction
# ---------------------------------------------------------------------------

def build_server(variant_id: str = "D3-CLEAN") -> FastMCP:
    """Build and return a FastMCP server for the given schema variant.

    Tools are registered through the actual FastMCP mechanism.
    Only tools belonging to the selected density level are registered.
    Metadata (descriptions, parameter docs) comes from the schema file.
    Tool execution code is always the same module function regardless
    of clean/poisoned metadata.
    """
    schema = _load_schema(variant_id)
    density = _extract_density_level(variant_id)
    active_tool_ids = DENSITY_TOOLS[density]

    mcp = FastMCP(
        name="phase2-mcp-research-server",
    )

    # Build a lookup from logical_tool_id → schema entry
    tool_schema_map: dict[str, dict] = {}
    for tool_entry in schema.get("tools", []):
        lid = tool_entry["logical_tool_id"]
        tool_schema_map[lid] = tool_entry

    for tool_id in active_tool_ids:
        mod = _TOOL_MODULES[tool_id]
        entry = tool_schema_map.get(tool_id, {})
        description = entry.get("description", f"Tool: {tool_id}")

        # Tool-name poisoning disabled: exposed_tool_name == logical_tool_id
        exposed_name = entry.get("exposed_tool_name", tool_id)
        assert exposed_name == tool_id, (
            f"Tool-name poisoning is disabled in this pass. "
            f"exposed_tool_name '{exposed_name}' must equal "
            f"logical_tool_id '{tool_id}'."
        )

        # Register through actual FastMCP @mcp.tool() mechanism.
        # We use mcp.tool() as a decorator on the module's execute function,
        # supplying the description from the schema variant.
        mcp.tool(name=exposed_name, description=description)(mod.execute)

    # Store variant on the server object for introspection by tests
    mcp._phase2_variant_id = variant_id  # type: ignore[attr-defined]
    mcp._phase2_density = density  # type: ignore[attr-defined]
    mcp._phase2_schema = schema  # type: ignore[attr-defined]

    return mcp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    variant = os.environ.get("SCHEMA_VARIANT", "D3-CLEAN")
    print(f"[Phase2 MCP Server] Starting with variant: {variant}", file=sys.stderr)
    mcp = build_server(variant)
    mcp.run()


if __name__ == "__main__":
    main()
