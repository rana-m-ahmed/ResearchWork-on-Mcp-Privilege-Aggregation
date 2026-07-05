"""Validate Phase 4.5 dry-run JSONL logs against the frozen Phase 5 schema."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "phase4" / "configs" / "phase5_schema_freeze.json"
REPORT_DEFAULT = ROOT / "phase4_5" / "validation" / "phase45_log_schema_report.md"

LEGACY_FIELD_NAMES = {"metadata_condition", "source_payload_hash", "adapted_payload_hash", "outcome_primary", "outcome_label"}


@dataclass(frozen=True)
class SchemaField:
    name: str
    base_type: str
    enum_values: list[str]
    nullable: bool


def load_schema(path: Path) -> dict[str, SchemaField]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, SchemaField] = {}
    for name, value in raw.items():
        if isinstance(value, bool):
            result[name] = SchemaField(name, "boolean", [], False)
            continue
        if isinstance(value, str):
            parts = value.split("|")
            nullable = "null" in parts
            non_null = [part for part in parts if part != "null"]
            if len(non_null) > 1:
                result[name] = SchemaField(name, "string", non_null, nullable)
            elif non_null and non_null[0] in {"string", "number", "integer", "boolean", "object", "array", "null"}:
                result[name] = SchemaField(name, non_null[0], [], nullable)
            else:
                result[name] = SchemaField(name, "string", [], nullable)
            continue
        if value is None:
            result[name] = SchemaField(name, "null", [], True)
            continue
        if isinstance(value, int) and not isinstance(value, bool):
            result[name] = SchemaField(name, "integer", [], False)
            continue
        if isinstance(value, float):
            result[name] = SchemaField(name, "number", [], False)
            continue
        if isinstance(value, list):
            result[name] = SchemaField(name, "array", [], False)
            continue
        if isinstance(value, dict):
            result[name] = SchemaField(name, "object", [], False)
            continue
        raise TypeError(f"Unsupported schema value for {name}: {value!r}")
    return result


def validate_value(field: SchemaField, value: Any) -> tuple[bool, str]:
    if value is None:
        return (field.nullable, "null accepted" if field.nullable else "null not allowed")
    if field.base_type == "boolean":
        return (isinstance(value, bool), "boolean ok" if isinstance(value, bool) else "expected boolean")
    if field.base_type == "integer":
        return (isinstance(value, int) and not isinstance(value, bool), "integer ok" if isinstance(value, int) and not isinstance(value, bool) else "expected integer")
    if field.base_type == "number":
        return (isinstance(value, (int, float)) and not isinstance(value, bool), "number ok" if isinstance(value, (int, float)) and not isinstance(value, bool) else "expected number")
    if field.base_type == "object":
        return (isinstance(value, dict), "object ok" if isinstance(value, dict) else "expected object")
    if field.base_type == "array":
        return (isinstance(value, list), "array ok" if isinstance(value, list) else "expected array")
    if field.enum_values:
        return (isinstance(value, str) and value in field.enum_values, "enum ok" if isinstance(value, str) and value in field.enum_values else f"expected one of {field.enum_values}")
    return (isinstance(value, str), "string ok" if isinstance(value, str) else "expected string")


def load_jsonl(path: Path, allow_empty: bool) -> list[dict[str, Any]]:
    if not path.exists():
        if allow_empty:
            return []
        raise FileNotFoundError(f"{path} does not exist")
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        if allow_empty:
            return []
        raise ValueError("empty JSONL input is not allowed without --allow-empty")
    rows: list[dict[str, Any]] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        try:
            row = json.loads(line)
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"line {lineno}: invalid JSON: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"line {lineno}: JSONL row must be an object")
        rows.append(row)
    return rows


def validate_rows(rows: list[dict[str, Any]], schema: dict[str, SchemaField]) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    required_flags = {
        "phase": "phase4_5",
        "dry_run": True,
        "official_trial": False,
        "counts_for_phase5": False,
        "publication_evidence": False,
    }
    for index, row in enumerate(rows, start=1):
        for legacy in LEGACY_FIELD_NAMES:
            if legacy in row or legacy in row.get("trial", {}):
                failures.append(f"row {index}: legacy field name present: {legacy}")

        for flag, expected in required_flags.items():
            actual = row.get(flag)
            if actual != expected:
                failures.append(f"row {index}: {flag} expected {expected!r}, got {actual!r}")

        if row.get("payload_reference_validated") is not True:
            failures.append(f"row {index}: payload_reference_validated must be true")

        trial = row.get("trial")
        if not isinstance(trial, dict):
            failures.append(f"row {index}: missing nested trial object")
            continue

        missing = [field for field in schema if field not in trial]
        if missing:
            failures.append(f"row {index}: missing trial fields: {', '.join(missing)}")

        for field_name, field in schema.items():
            if field_name not in trial:
                continue
            ok, message = validate_value(field, trial[field_name])
            if not ok:
                failures.append(f"row {index}: {field_name}: {message}")

        extra_outcome_fields = [name for name in trial if name in {"primary_outcome_class", "critical_exploit", "critical_exploit_path_type", "attack_success", "hijack_attempt", "utility_success", "tid_levenshtein"}]
        if extra_outcome_fields:
            failures.append(f"row {index}: outcome fields not present in frozen schema: {', '.join(extra_outcome_fields)}")

        if any(name in trial for name in {"metadata_condition", "source_payload_hash", "adapted_payload_hash"}):
            failures.append(f"row {index}: old primary payload field names are not allowed")

        if row.get("phase") == "phase4_5" and trial.get("phase") not in {"phase5_adversarial_core", "phase5_adversarial_defense", "phase5_utility_preservation"}:
            warnings.append(f"row {index}: nested trial.phase is not one of the frozen phase5 variants")

    return failures, warnings


def render_report(input_path: Path, rows: list[dict[str, Any]], failures: list[str], warnings: list[str], allow_empty: bool) -> str:
    status = "SCHEMA_VALIDATION_PASS" if not failures and (rows or allow_empty) else "REVISE_PHASE45"
    verdict = "PASS" if status == "SCHEMA_VALIDATION_PASS" else "REVISE_PHASE45"
    lines = [
        "# Phase 4.5 Log Schema Report",
        "",
        f"- Input: `{input_path}`",
        f"- Row count: `{len(rows)}`",
        f"- Allow empty: `{allow_empty}`",
        f"- Internal status: `{status}`",
        f"- Verdict: `{verdict}`",
        "",
        "## Validation Summary",
    ]
    if failures:
        lines.extend(f"- FAIL: {failure}" for failure in failures)
    else:
        lines.append("- no validation failures")
    lines.extend(
        [
            "",
            "## Warnings",
        ]
    )
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Phase 4.5 JSONL logs against the frozen schema")
    parser.add_argument("--input", required=True, help="Path to the JSONL file to validate")
    parser.add_argument("--report", default=str(REPORT_DEFAULT), help="Markdown report output path")
    parser.add_argument("--allow-empty", action="store_true", help="Allow empty or missing JSONL input for scaffold validation")
    args = parser.parse_args()

    schema = load_schema(SCHEMA_PATH)
    input_path = Path(args.input)
    rows = load_jsonl(input_path, allow_empty=args.allow_empty)
    failures, warnings = validate_rows(rows, schema)
    report = render_report(input_path, rows, failures, warnings, args.allow_empty)
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if not failures and (rows or args.allow_empty) else 1


if __name__ == "__main__":
    raise SystemExit(main())
