"""
Test: Logical ID Mapping

Verifies that:
  - Every tool has both logical_tool_id and exposed_tool_name
  - Tool-name poisoning is disabled: exposed_tool_name == logical_tool_id
  - Logical IDs are stable across all 9 schema variants
  - Logical IDs match the constants in tool definition modules
"""

from __future__ import annotations

import json
import os

import pytest

from server.tool_definitions import (
    read_internal_notes,
    write_outbox,
    get_local_weather,
    query_local_inventory,
    log_event,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ALL_SCHEMA_FILES = [
    "schemas/clean/density1.json",
    "schemas/clean/density3.json",
    "schemas/clean/density5.json",
    "schemas/poisoned_tool_description/density1.json",
    "schemas/poisoned_tool_description/density3.json",
    "schemas/poisoned_tool_description/density5.json",
    "schemas/poisoned_capability_advertisement/density1.json",
    "schemas/poisoned_capability_advertisement/density3.json",
    "schemas/poisoned_capability_advertisement/density5.json",
]

# Canonical logical IDs from tool definition modules
EXPECTED_LOGICAL_IDS = {
    "read_internal_notes": read_internal_notes.LOGICAL_TOOL_ID,
    "write_outbox": write_outbox.LOGICAL_TOOL_ID,
    "get_local_weather": get_local_weather.LOGICAL_TOOL_ID,
    "query_local_inventory": query_local_inventory.LOGICAL_TOOL_ID,
    "log_event": log_event.LOGICAL_TOOL_ID,
}


def _load_schema(rel_path: str) -> dict:
    with open(os.path.join(PROJECT_ROOT, rel_path), "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_FILES)
def test_every_tool_has_logical_id(schema_path: str) -> None:
    schema = _load_schema(schema_path)
    for tool in schema["tools"]:
        assert "logical_tool_id" in tool, (
            f"{schema_path}: tool missing logical_tool_id: {tool}"
        )
        assert isinstance(tool["logical_tool_id"], str)
        assert len(tool["logical_tool_id"]) > 0


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_FILES)
def test_every_tool_has_exposed_name(schema_path: str) -> None:
    schema = _load_schema(schema_path)
    for tool in schema["tools"]:
        assert "exposed_tool_name" in tool, (
            f"{schema_path}: tool missing exposed_tool_name: {tool}"
        )


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_FILES)
def test_tool_name_poisoning_disabled(schema_path: str) -> None:
    """exposed_tool_name must equal logical_tool_id (poisoning disabled)."""
    schema = _load_schema(schema_path)
    for tool in schema["tools"]:
        assert tool["exposed_tool_name"] == tool["logical_tool_id"], (
            f"{schema_path}: tool-name poisoning detected — "
            f"exposed '{tool['exposed_tool_name']}' != "
            f"logical '{tool['logical_tool_id']}'"
        )


@pytest.mark.parametrize("schema_path", ALL_SCHEMA_FILES)
def test_logical_ids_match_modules(schema_path: str) -> None:
    """Schema logical IDs must match the constants in tool definition modules."""
    schema = _load_schema(schema_path)
    for tool in schema["tools"]:
        lid = tool["logical_tool_id"]
        assert lid in EXPECTED_LOGICAL_IDS, (
            f"{schema_path}: unknown logical_tool_id '{lid}'"
        )
        assert EXPECTED_LOGICAL_IDS[lid] == lid


def test_logical_ids_stable_across_variants() -> None:
    """Same density level must have identical logical IDs across all variants."""
    ids_by_density: dict[int, list[list[str]]] = {}
    for schema_path in ALL_SCHEMA_FILES:
        schema = _load_schema(schema_path)
        density = schema["density_level"]
        tool_ids = [t["logical_tool_id"] for t in schema["tools"]]
        ids_by_density.setdefault(density, []).append(tool_ids)

    for density, id_lists in ids_by_density.items():
        for i in range(1, len(id_lists)):
            assert id_lists[0] == id_lists[i], (
                f"Density {density}: logical IDs not stable across variants"
            )
