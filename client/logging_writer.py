"""
JSONL logging writer for Phase 2.

Every JSONL row must include:
  phase: "phase2_infra"
  non_experimental: true

Log-integrity requirements:
  - compute SHA-256 after writing JSONL
  - Phase 2 logs stored separately from future Phase 3/5 logs
  - MCP server does not write trial JSONL logs
  - tool path cannot delete or overwrite logs

NOTE: Phase 2 token fields (tool_count, schema_token_count, etc.) are
preliminary engineering measurements only.  Authoritative context-window
and token analysis belongs to Phase 2.5.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any


# Required fields for every Phase 2 JSONL row
_REQUIRED_FIELDS = {
    "phase", "non_experimental", "timestamp_utc",
    "model_backend_mode", "model_backend",
    "tool_density_level", "mcp_metadata_condition",
    "schema_variant_id", "tool_schema_hash",
    "capability_advertisement_hash", "prompt_hash",
    "payload_id_or_placeholder_marker", "is_placeholder_payload",
    "logical_tool_sequence", "exposed_tool_sequence",
    "reset_status", "safety_test_status",
    "network_mode_validation", "error_type",
    "smoke_test_result", "log_file_sha256_after_write",
}

# Forbidden labels that must never appear in Phase 2 logs
FORBIDDEN_LABELS = frozenset({
    "attack_success", "critical_exploit", "ASR", "exploit_found",
    "TID",
})

# Allowed adversarial-channel result labels
ALLOWED_ADVERSARIAL_LABELS = frozenset({
    "adversarial_channel_logged",
    "adversarial_channel_not_logged",
    "pipeline_error",
})


def build_row(
    *,
    run_id: str,
    trial_id: str,
    schema_variant_id: str,
    tool_density_level: int,
    mcp_metadata_condition: str,
    model_backend_mode: str,
    model_backend: str,
    model_name: str | None = None,
    model_version: str | None = None,
    quantization_format: str | None = None,
    runtime_backend: str | None = None,
    runtime_version: str | None = None,
    tool_schema_hash: str = "",
    capability_advertisement_hash: str = "",
    prompt_hash: str = "",
    payload_id_or_placeholder_marker: str | None = None,
    is_placeholder_payload: bool = True,
    logical_tool_sequence: list[str] | None = None,
    exposed_tool_sequence: list[str] | None = None,
    tool_parameters_summary: list[dict] | None = None,
    tool_outputs_summary: list[str] | None = None,
    reset_status: str = "not_attempted",
    safety_test_status: str = "not_run",
    network_mode_validation: str = "not_run",
    error_type: str = "none",
    smoke_test_result: str = "not_applicable",
    notes: str = "",
    # Phase 2 preliminary token fields (see module docstring)
    tool_count: int = 0,
    schema_token_count: int = 0,
    metadata_token_count: int = 0,
    total_prompt_token_count: int = 0,
    total_context_token_count: int = 0,
) -> dict[str, Any]:
    """Build a complete Phase 2 JSONL row with all required fields."""
    row: dict[str, Any] = {
        "run_id": run_id,
        "trial_id": trial_id,
        "phase": "phase2_infra",
        "non_experimental": True,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "model_backend_mode": model_backend_mode,
        "model_backend": model_backend,
        "model_name": model_name,
        "model_version": model_version,
        "quantization_format": quantization_format,
        "runtime_backend": runtime_backend,
        "runtime_version": runtime_version,
        "tool_density_level": tool_density_level,
        "mcp_metadata_condition": mcp_metadata_condition,
        "schema_variant_id": schema_variant_id,
        "tool_schema_hash": tool_schema_hash,
        "capability_advertisement_hash": capability_advertisement_hash,
        "prompt_hash": prompt_hash,
        "payload_id_or_placeholder_marker": payload_id_or_placeholder_marker,
        "is_placeholder_payload": is_placeholder_payload,
        # Phase 2 preliminary token fields — authoritative analysis in Phase 2.5
        "tool_count": tool_count,
        "schema_token_count": schema_token_count,
        "metadata_token_count": metadata_token_count,
        "total_prompt_token_count": total_prompt_token_count,
        "total_context_token_count": total_context_token_count,
        "logical_tool_sequence": logical_tool_sequence or [],
        "exposed_tool_sequence": exposed_tool_sequence or [],
        "tool_parameters_summary": tool_parameters_summary or [],
        "tool_outputs_summary": tool_outputs_summary or [],
        "reset_status": reset_status,
        "safety_test_status": safety_test_status,
        "network_mode_validation": network_mode_validation,
        "error_type": error_type,
        "smoke_test_result": smoke_test_result,
        "log_file_sha256_after_write": "",  # Filled after write
        "notes": notes,
    }
    return row


def validate_row(row: dict[str, Any]) -> list[str]:
    """Validate a JSONL row against Phase 2 requirements.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []

    # Check required fields
    missing = _REQUIRED_FIELDS - set(row.keys())
    if missing:
        errors.append(f"Missing required fields: {missing}")

    # Check locked values
    if row.get("phase") != "phase2_infra":
        errors.append(f"phase must be 'phase2_infra', got '{row.get('phase')}'")
    if row.get("non_experimental") is not True:
        errors.append("non_experimental must be true")

    # Check for forbidden labels in any string value
    for key, val in row.items():
        if isinstance(val, str):
            for forbidden in FORBIDDEN_LABELS:
                if forbidden.lower() in val.lower() and key != "notes":
                    errors.append(
                        f"Forbidden label '{forbidden}' found in field '{key}'"
                    )

    return errors


def write_jsonl_row(filepath: str, row: dict[str, Any]) -> str:
    """Append a JSONL row to a log file and return the file's SHA-256.

    The SHA-256 is computed AFTER writing, covering the entire file.
    """
    line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)

    # Compute SHA-256 of the entire file after write
    sha = _file_sha256(filepath)
    return sha


def _file_sha256(filepath: str) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_log_hash(filepath: str) -> str:
    """Public accessor for file hash (used by tests and audit)."""
    return _file_sha256(filepath)
