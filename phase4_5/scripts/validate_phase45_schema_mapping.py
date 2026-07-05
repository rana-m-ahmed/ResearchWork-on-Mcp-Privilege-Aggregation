"""Validate the Phase 4.5 schema mapping against the frozen Phase 5 schema."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "phase4" / "configs" / "phase5_schema_freeze.json"
MAPPING_PATH = ROOT / "phase4_5" / "configs" / "phase45_schema_mapping.yaml"
REPORT_PATH = ROOT / "phase4_5" / "validation" / "phase45_schema_mapping_report.md"

DISALLOWED_FIELD_NAMES = {
    "metadata_condition",
    "source_payload_hash",
    "adapted_payload_hash",
    "outcome_primary",
    "outcome_label",
}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    required: bool
    base_type: str
    enum_values: list[str]
    nullable: bool
    raw_value: Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a mapping at the top level")
    return loaded


def infer_field_spec(name: str, raw_value: Any) -> FieldSpec:
    if isinstance(raw_value, bool):
        return FieldSpec(name, True, "boolean", [], False, raw_value)
    if raw_value is None:
        return FieldSpec(name, True, "null", [], True, raw_value)
    if isinstance(raw_value, str):
        parts = raw_value.split("|")
        nullable = "null" in parts
        non_null_parts = [part for part in parts if part != "null"]
        if len(non_null_parts) == 1 and non_null_parts[0] in {"string", "number", "integer", "boolean", "object", "array", "null"}:
            return FieldSpec(name, True, non_null_parts[0], [], nullable, raw_value)
        if raw_value.startswith("sha") or raw_value == "string" or raw_value == "string|null":
            return FieldSpec(name, True, "string", [], nullable or "|null" in raw_value, raw_value)
        if len(parts) > 1:
            return FieldSpec(name, True, "string", non_null_parts, nullable, raw_value)
        return FieldSpec(name, True, "string", [], False, raw_value)
    if isinstance(raw_value, (int, float)):
        base_type = "integer" if isinstance(raw_value, int) and not isinstance(raw_value, bool) else "number"
        return FieldSpec(name, True, base_type, [], False, raw_value)
    if isinstance(raw_value, list):
        return FieldSpec(name, True, "array", [], False, raw_value)
    if isinstance(raw_value, dict):
        return FieldSpec(name, True, "object", [], False, raw_value)
    raise TypeError(f"Unsupported schema value for {name}: {raw_value!r}")


def schema_specs(schema: dict[str, Any]) -> dict[str, FieldSpec]:
    return {name: infer_field_spec(name, value) for name, value in schema.items()}


def validate_mapping(schema: dict[str, Any], mapping: dict[str, Any]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    specs = schema_specs(schema)
    schema_fields = list(schema.keys())
    mapped_fields = list(mapping.keys())
    missing_required: list[str] = []
    missing_optional: list[str] = []
    extra_fields: list[str] = []
    enum_issues: list[str] = []
    outcome_issues: list[str] = []

    for field in schema_fields:
        if field not in mapping:
            spec = specs[field]
            if spec.nullable:
                missing_optional.append(field)
            else:
                missing_required.append(field)
            continue

        entry = mapping[field]
        if not isinstance(entry, dict):
            missing_required.append(field)
            continue

        for required_key in (
            "required",
            "phase5_type",
            "source_category",
            "source_field",
            "transformation",
            "dry_run_allowed",
            "official_phase5_required",
            "validation_rule",
        ):
            if required_key not in entry:
                missing_required.append(field)
                break

        if field in DISALLOWED_FIELD_NAMES:
            outcome_issues.append(f"{field} is disallowed by the frozen schema compatibility rule")

        spec = specs[field]
        phase5_type = str(entry.get("phase5_type", "")).lower()
        if phase5_type != spec.base_type:
            enum_issues.append(f"{field}: expected phase5_type {spec.base_type}, got {phase5_type or '<missing>'}")

        if spec.enum_values:
            transformation = str(entry.get("transformation", ""))
            if transformation not in {"enum_normalize", "constant", "rename"}:
                enum_issues.append(f"{field}: enum field must use enum_normalize/constant/rename, got {transformation}")

        if field == "phase" and "phase4_5" in str(entry.get("source_field", "")):
            enum_issues.append("phase field must map to frozen phase5 phase values, not the Phase 4.5 wrapper flag")

        if field == "official_trial" and entry.get("transformation") not in {"constant", "runtime_generated"}:
            enum_issues.append("official_trial must be a boolean runtime or constant mapping")

    for field in mapped_fields:
        if field not in schema:
            extra_fields.append(field)

    if any(name in mapping for name in DISALLOWED_FIELD_NAMES):
        outcome_issues.append("mapping includes disallowed legacy field names")

    return schema_fields, missing_required, missing_optional, extra_fields, enum_issues + outcome_issues


def render_report(
    schema_fields: list[str],
    mapped_fields: list[str],
    missing_required: list[str],
    missing_optional: list[str],
    extra_fields: list[str],
    issues: list[str],
) -> str:
    status = "SCHEMA_VALIDATION_PASS" if not issues and not missing_required and not extra_fields else "REVISE_PHASE45"
    verdict = "PASS" if status == "SCHEMA_VALIDATION_PASS" else "REVISE_PHASE45"
    lines = [
        "# Phase 4.5 Schema Mapping Report",
        "",
        f"- Internal status: `{status}`",
        f"- Verdict: `{verdict}`",
        "",
        "## Frozen Schema Fields Discovered",
    ]
    lines.extend(f"- `{field}`" for field in schema_fields)
    lines.extend(
        [
            "",
            "## Frozen Schema Fields Mapped",
        ]
    )
    lines.extend(f"- `{field}`" for field in mapped_fields if field in schema_fields)
    lines.extend(
        [
            "",
            "## Unmapped Required Fields",
        ]
    )
    if missing_required:
        lines.extend(f"- `{field}`" for field in missing_required)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Unmapped Optional Fields",
        ]
    )
    if missing_optional:
        lines.extend(f"- `{field}`" for field in missing_optional)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Extra Non-Frozen Mapping Fields",
        ]
    )
    if extra_fields:
        lines.extend(f"- `{field}`" for field in extra_fields)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Enum Compatibility",
        ]
    )
    enum_notes = [issue for issue in issues if "enum" in issue.lower()]
    if enum_notes:
        lines.extend(f"- {issue}" for issue in enum_notes)
    else:
        lines.append("- pass")
    lines.extend(
        [
            "",
            "## Outcome Representation Compatibility",
        ]
    )
    outcome_notes = [issue for issue in issues if "outcome" in issue.lower() or "legacy field" in issue.lower()]
    if outcome_notes:
        lines.extend(f"- {issue}" for issue in outcome_notes)
    else:
        lines.append("- pass")
    lines.extend(
        [
            "",
            "## Verdict",
            f"- `{verdict}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 4.5 schema mapping")
    parser.parse_args()

    schema = load_json(SCHEMA_PATH)
    mapping = load_yaml(MAPPING_PATH)
    schema_fields, missing_required, missing_optional, extra_fields, issues = validate_mapping(schema, mapping)
    mapped_fields = list(mapping.keys())
    report = render_report(schema_fields, mapped_fields, missing_required, missing_optional, extra_fields, issues)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if not issues and not missing_required and not extra_fields else 1


if __name__ == "__main__":
    raise SystemExit(main())
