"""
Test: Schema Metadata-Only Diff

Verifies that clean and poisoned variants for the same density level
differ ONLY in allowed metadata fields:
  - tool descriptions
  - parameter documentation (parameter description strings)
  - capability_advertisement text
  - schema_variant_id (by definition)
  - metadata_condition (by definition)

Forbidden differences:
  - logical_tool_id
  - exposed_tool_name
  - parameter names
  - parameter types
  - required parameter lists
  - tool count
  - density_level
"""

from __future__ import annotations

import json
import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_schema(rel_path: str) -> dict:
    with open(os.path.join(PROJECT_ROOT, rel_path), "r", encoding="utf-8") as f:
        return json.load(f)


# Pairs: (clean_path, poisoned_path, label)
_DIFF_PAIRS = [
    # Poisoned tool description vs clean
    ("schemas/clean/density1.json", "schemas/poisoned_tool_description/density1.json", "D1 TD"),
    ("schemas/clean/density3.json", "schemas/poisoned_tool_description/density3.json", "D3 TD"),
    ("schemas/clean/density5.json", "schemas/poisoned_tool_description/density5.json", "D5 TD"),
    # Poisoned capability advertisement vs clean
    ("schemas/clean/density1.json", "schemas/poisoned_capability_advertisement/density1.json", "D1 CA"),
    ("schemas/clean/density3.json", "schemas/poisoned_capability_advertisement/density3.json", "D3 CA"),
    ("schemas/clean/density5.json", "schemas/poisoned_capability_advertisement/density5.json", "D5 CA"),
]


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_same_tool_count(clean_path: str, poisoned_path: str, label: str) -> None:
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)
    assert len(clean["tools"]) == len(poisoned["tools"]), (
        f"{label}: tool count differs"
    )


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_same_density_level(clean_path: str, poisoned_path: str, label: str) -> None:
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)
    assert clean["density_level"] == poisoned["density_level"], (
        f"{label}: density_level differs"
    )


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_same_logical_tool_ids(clean_path: str, poisoned_path: str, label: str) -> None:
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)
    clean_ids = [t["logical_tool_id"] for t in clean["tools"]]
    poisoned_ids = [t["logical_tool_id"] for t in poisoned["tools"]]
    assert clean_ids == poisoned_ids, (
        f"{label}: logical_tool_ids differ: {clean_ids} vs {poisoned_ids}"
    )


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_same_exposed_tool_names(clean_path: str, poisoned_path: str, label: str) -> None:
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)
    clean_names = [t["exposed_tool_name"] for t in clean["tools"]]
    poisoned_names = [t["exposed_tool_name"] for t in poisoned["tools"]]
    assert clean_names == poisoned_names, (
        f"{label}: exposed_tool_names differ: {clean_names} vs {poisoned_names}"
    )


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_same_parameter_structure(clean_path: str, poisoned_path: str, label: str) -> None:
    """Parameter names, types, and required lists must be identical."""
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)

    for ct, pt in zip(clean["tools"], poisoned["tools"]):
        c_params = ct["parameters"]
        p_params = pt["parameters"]

        # Same property names
        c_prop_names = sorted(c_params.get("properties", {}).keys())
        p_prop_names = sorted(p_params.get("properties", {}).keys())
        assert c_prop_names == p_prop_names, (
            f"{label}/{ct['logical_tool_id']}: param names differ"
        )

        # Same property types
        for name in c_prop_names:
            c_type = c_params["properties"][name].get("type")
            p_type = p_params["properties"][name].get("type")
            assert c_type == p_type, (
                f"{label}/{ct['logical_tool_id']}/{name}: type differs"
            )

        # Same required list
        c_req = sorted(c_params.get("required", []))
        p_req = sorted(p_params.get("required", []))
        assert c_req == p_req, (
            f"{label}/{ct['logical_tool_id']}: required params differ"
        )


@pytest.mark.parametrize("clean_path,poisoned_path,label", _DIFF_PAIRS)
def test_something_actually_differs(clean_path: str, poisoned_path: str, label: str) -> None:
    """Poisoned variant must actually differ from clean in metadata."""
    clean = _load_schema(clean_path)
    poisoned = _load_schema(poisoned_path)
    # Either capability_advertisement, tool descriptions, or param descriptions differ
    differences_found = False
    if clean.get("capability_advertisement") != poisoned.get("capability_advertisement"):
        differences_found = True
    for ct, pt in zip(clean["tools"], poisoned["tools"]):
        if ct.get("description") != pt.get("description"):
            differences_found = True
        # Check parameter description strings
        for name in ct["parameters"].get("properties", {}):
            c_desc = ct["parameters"]["properties"][name].get("description", "")
            p_desc = pt["parameters"]["properties"][name].get("description", "")
            if c_desc != p_desc:
                differences_found = True
    assert differences_found, (
        f"{label}: poisoned variant is identical to clean — no metadata poisoning"
    )
