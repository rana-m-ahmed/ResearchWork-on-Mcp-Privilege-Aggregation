"""Verify the Phase 4 freeze artifacts and write a Phase 4.5 preflight report."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[2]
PHASE4_ROOT = ROOT / "phase4"
PHASE45_ROOT = ROOT / "phase4_5"
REPORT_PATH = PHASE45_ROOT / "validation" / "phase45_preflight_report.md"
ENUM_PATH = PHASE45_ROOT / "configs" / "phase45_status_enum.yaml"

REQUIRED_PHASE4_FILES = [
    PHASE4_ROOT / "configs" / "phase5_schema_freeze.json",
    PHASE4_ROOT / "configs" / "model_set_freeze.yaml",
    PHASE4_ROOT / "configs" / "payload_reference_map.json",
    PHASE4_ROOT / "configs" / "statistical_plan.yaml",
    PHASE4_ROOT / "configs" / "defense_config_freeze.yaml",
    PHASE4_ROOT / "frozen_bundle" / "phase5_execution_manifest.json",
    PHASE4_ROOT / "frozen_bundle" / "cryptographic_lock_manifest.json",
    PHASE4_ROOT / "frozen_bundle" / "master_hash_ledger.csv",
    PHASE4_ROOT / "frozen_bundle" / "trial_order_core.csv",
    PHASE4_ROOT / "frozen_bundle" / "trial_order_defense.csv",
    PHASE4_ROOT / "reports" / "phase4_go_no_go_decision.md",
]

EXPECTED_ENUM = {
    "final_verdicts": ["GO_TO_PHASE5", "REVISE_PHASE45", "NO_GO"],
    "internal_statuses": [
        "PHASE4_FREEZE_VERIFIED",
        "PHASE45_SCAFFOLD_COMPLETE",
        "LOCAL_PREFLIGHT_PASS",
        "LOCAL_DRYRUN_PASS",
        "LOCAL_MODEL_EXECUTION_DEFERRED_TO_KAGGLE",
        "KAGGLE_SMOKE_PREPARED",
        "KAGGLE_SMOKE_PASS",
        "KAGGLE_MODEL_LOAD_SMOKE_PASS",
        "KAGGLE_QUOTA_FEASIBILITY_PASS",
        "SCHEMA_VALIDATION_PASS",
        "PAYLOAD_VALIDATION_PASS",
        "TOKEN_BUDGET_VALIDATION_PASS",
        "RESET_VALIDATION_PASS",
        "STATISTICS_SMOKE_PASS",
        "FORBIDDEN_CLAIMS_LINT_PASS",
        "EXTERNAL_AUDIT_GO",
        "GO_TO_PHASE5",
        "REVISE_PHASE45",
        "NO_GO",
    ],
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def canonicalize_yaml_like_list(path: Path) -> dict[str, list[str]]:
    current_key = None
    result: dict[str, list[str]] = {}
    for raw_line in read_text(path).splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.endswith(":"):
            current_key = line[:-1]
            result[current_key] = []
            continue
        if line.startswith("- "):
            if current_key is None:
                raise ValueError(f"list item without section in {path}")
            result[current_key].append(line[2:].strip())
    return result


def parse_json(path: Path) -> tuple[bool, str]:
    try:
        json.loads(read_text(path))
    except Exception as exc:  # noqa: BLE001 - captured for report text
        return False, f"json parse failed: {exc}"
    return True, "json parse passed"


def parse_model_set_yaml(path: Path) -> tuple[bool, str]:
    text = read_text(path)
    try:
        import yaml  # type: ignore
    except Exception:
        return True, "yaml semantic validation skipped; PyYAML not available"

    try:
        yaml.safe_load(text)
    except Exception as exc:  # noqa: BLE001 - captured for report text
        return False, f"yaml parse failed: {exc}"
    return True, "yaml parse passed"


def parse_status_enum(path: Path) -> tuple[bool, str]:
    try:
        parsed = canonicalize_yaml_like_list(path)
    except Exception as exc:  # noqa: BLE001 - captured for report text
        return False, f"status enum parse failed: {exc}"

    for key, expected_values in EXPECTED_ENUM.items():
        actual_values = parsed.get(key)
        if actual_values != expected_values:
            return (
                False,
                f"status enum mismatch for {key}: expected {expected_values}, got {actual_values}",
            )
    return True, "status enum canonical"


def verify_required_files(paths: Iterable[Path]) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    missing: list[str] = []
    for path in paths:
        row = {"path": str(path.relative_to(ROOT))}
        if not path.exists():
            row.update({"found": "no", "readable": "no", "sha256": "", "note": "missing"})
            rows.append(row)
            missing.append(row["path"])
            continue

        try:
            path.read_bytes()
            readable = "yes"
            note = "present"
        except Exception as exc:  # noqa: BLE001 - captured for report text
            readable = "no"
            note = f"unreadable: {exc}"
            missing.append(row["path"])

        row.update(
            {
                "found": "yes",
                "readable": readable,
                "sha256": sha256_file(path) if readable == "yes" else "",
                "note": note,
            }
        )
        rows.append(row)
    return rows, missing


def render_markdown(
    rows: list[dict[str, str]],
    missing: list[str],
    parse_status: dict[str, tuple[bool, str]],
    final_status: str,
    final_verdict: str,
    status_enum_ok: tuple[bool, str],
) -> str:
    timestamp = datetime.now(timezone.utc).isoformat()
    found_count = sum(1 for row in rows if row["found"] == "yes" and row["readable"] == "yes")
    sections = [
        "# Phase 4.5 Preflight Report",
        "",
        f"- UTC timestamp: `{timestamp}`",
        f"- Final internal status: `{final_status}`",
        f"- Final verdict candidate: `{final_verdict}`",
        "",
        "## Required Artifacts Found",
        f"- Count: `{found_count}` of `{len(rows)}`",
    ]
    for row in rows:
        if row["found"] == "yes" and row["readable"] == "yes":
            sections.append(f"- `{row['path']}`")

    sections.extend(
        [
            "",
            "## Missing Artifacts",
            "- none" if not missing else "",
        ]
    )
    if missing:
        sections.extend(f"- `{path}`" for path in missing)

    sections.extend(
        [
            "",
            "## Parse Status",
            f"- `phase4/configs/phase5_schema_freeze.json`: `{parse_status['phase5_schema_freeze'][1]}`",
            f"- `phase4/configs/payload_reference_map.json`: `{parse_status['payload_reference_map'][1]}`",
            f"- `phase4/configs/model_set_freeze.yaml`: `{parse_status['model_set_freeze'][1]}`",
            f"- `phase4_5/configs/phase45_status_enum.yaml`: `{status_enum_ok[1]}`",
            "",
            "## File Hashes",
        ]
    )

    for row in rows:
        sections.append(
            f"- `{row['path']}` - `{row['sha256'] or 'unavailable'}` - {row['note']}"
        )

    sections.extend(
        [
            "",
            "## Canonical Enum Check",
            f"- Result: `{status_enum_ok[1]}`",
            "",
            "## Notes",
            "- Phase 4 frozen artifacts were only read, not modified.",
            "- Phase 4.5 remains non-official.",
        ]
    )
    return "\n".join(sections) + "\n"


def main() -> int:
    rows, missing = verify_required_files(REQUIRED_PHASE4_FILES)
    parse_status = {
        "phase5_schema_freeze": parse_json(REQUIRED_PHASE4_FILES[0]),
        "payload_reference_map": parse_json(REQUIRED_PHASE4_FILES[2]),
        "model_set_freeze": parse_model_set_yaml(REQUIRED_PHASE4_FILES[1]),
    }
    status_enum_ok = parse_status_enum(ENUM_PATH)

    issues = []
    for key, (ok, message) in parse_status.items():
        if not ok:
            issues.append(f"{key}: {message}")
    if not status_enum_ok[0]:
        issues.append(f"status_enum: {status_enum_ok[1]}")
    issues.extend(f"missing: {item}" for item in missing)

    final_status = "LOCAL_PREFLIGHT_PASS" if not issues else "REVISE_PHASE45"
    final_verdict = final_status
    report = render_markdown(rows, missing, parse_status, final_status, final_verdict, status_enum_ok)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")

    print(report, end="")
    return 0 if final_status == "LOCAL_PREFLIGHT_PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
