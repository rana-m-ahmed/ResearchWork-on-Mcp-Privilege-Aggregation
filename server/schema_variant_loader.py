"""
Helpers for loading schema variants for both legacy Phase 2 and Phase 3.

Phase 3 is benign competence only. Runtime schema selection must use:
  - CLEAN_SURFACE
  - TD_SURFACE
  - CA_SURFACE

The poisoned directories remain archival-only for later phases and are kept
loadable here only for backwards compatibility with existing Phase 2 code.
"""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent

PHASE3_SURFACE_MAP = {
    "CLEAN": ("schemas/clean", "clean_schema"),
    "CLEAN_SURFACE": ("schemas/clean", "clean_schema"),
    "TD": ("schemas/phase3_surface/td_surface", "td_surface"),
    "TD_SURFACE": ("schemas/phase3_surface/td_surface", "td_surface"),
    "CA": ("schemas/phase3_surface/ca_surface", "ca_surface"),
    "CA_SURFACE": ("schemas/phase3_surface/ca_surface", "ca_surface"),
}

LEGACY_PHASE2_MAP = {
    "POISON-TD": ("schemas/poisoned_tool_description", "poisoned_tool_description"),
    "POISON-CA": (
        "schemas/poisoned_capability_advertisement",
        "poisoned_capability_advertisement",
    ),
}


def parse_variant_id(variant_id: str) -> tuple[str, str]:
    """Split a variant string into density token and condition token."""
    density, _, condition = variant_id.partition("-")
    return density.upper(), (condition or "CLEAN").upper()


def density_to_filename(density_token: str) -> str:
    """Convert D1/D3/D5 to the schema filename."""
    if density_token not in {"D1", "D3", "D5"}:
        raise ValueError(f"Unsupported density token: {density_token}")
    return f"density{density_token[1:]}.json"


def resolve_schema_path(variant_id: str) -> tuple[Path, str]:
    """Resolve the schema path and metadata label for a variant."""
    density_token, condition_token = parse_variant_id(variant_id)

    if condition_token in PHASE3_SURFACE_MAP:
        base_dir, metadata_label = PHASE3_SURFACE_MAP[condition_token]
    elif condition_token in LEGACY_PHASE2_MAP:
        base_dir, metadata_label = LEGACY_PHASE2_MAP[condition_token]
    else:
        raise ValueError(f"Unknown schema condition token: {condition_token}")

    path = REPO_ROOT / base_dir / density_to_filename(density_token)
    return path, metadata_label


def load_schema_variant(variant_id: str) -> dict:
    """Load a schema JSON document for the requested variant."""
    path, _metadata_label = resolve_schema_path(variant_id)
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
