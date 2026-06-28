"""
Tool call parser for Phase 2.

Parses model output to extract structured tool call requests.
Handles both the scripted fake model format (pre-parsed) and
raw LLM text output (simple JSON extraction).

This parser does NOT evaluate, route, or execute tool calls.
It only extracts them from model output.
"""

from __future__ import annotations

import json
import re
from typing import Any

# Admin/forbidden tool names that must be rejected before routing
FORBIDDEN_TOOL_NAMES = frozenset({
    "reset", "reset_state", "admin_reset", "set_schema_variant",
    "debug", "teardown",
})


def parse_tool_calls(model_output: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract tool calls from model output.

    If the model output already has pre-parsed tool_calls (scripted model),
    use them directly.  Otherwise attempt to parse from raw_output text.

    Each tool call dict has:
      - tool_name: str
      - arguments: dict
    """
    # Pre-parsed (scripted model)
    if model_output.get("tool_calls"):
        return model_output["tool_calls"]

    # Attempt to parse from raw text
    raw = model_output.get("raw_output", "")
    if not raw:
        return []

    return _extract_tool_calls_from_text(raw)


def _extract_tool_calls_from_text(text: str) -> list[dict[str, Any]]:
    """Best-effort extraction of tool calls from raw LLM text.

    Looks for JSON objects with tool_name/name and arguments/parameters fields.
    This is a simple heuristic — not a full LLM output parser.
    """
    calls: list[dict[str, Any]] = []

    # Try to find JSON blocks
    json_pattern = re.compile(r'\{[^{}]*\}', re.DOTALL)
    for match in json_pattern.finditer(text):
        try:
            obj = json.loads(match.group())
            name = obj.get("tool_name") or obj.get("name")
            args = obj.get("arguments") or obj.get("parameters") or {}
            if name and isinstance(name, str):
                calls.append({"tool_name": name, "arguments": args})
        except (json.JSONDecodeError, TypeError):
            continue

    return calls


def classify_tool_call(tool_name: str, valid_tool_names: set[str]) -> str:
    """Classify a tool call as valid, forbidden, or unknown.

    Returns:
      - "valid" if the tool name is in the valid set
      - "forbidden" if it's in the forbidden list
      - "unknown" otherwise
    """
    if tool_name in FORBIDDEN_TOOL_NAMES:
        return "forbidden"
    if tool_name in valid_tool_names:
        return "valid"
    return "unknown"


import json

class ModelOutputFailure(Exception): pass

def parse_phase3_tool_call(text):
    try:
        data = json.loads(text)
        return data
    except Exception as e:
        raise ModelOutputFailure("Invalid JSON, no auto-correction.")

