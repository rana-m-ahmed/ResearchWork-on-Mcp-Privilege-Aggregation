"""Smoke test parsing and grouping logic for Phase 4.5 statistics."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from _phase45_utils import VALIDATION_DIR


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for lineno, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def group_counts(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    groups: dict[str, Counter[str]] = {
        "model": Counter(),
        "density": Counter(),
        "metadata_surface_condition": Counter(),
        "attack_family": Counter(),
    }
    for row in rows:
        trial = row.get("trial", {})
        if not isinstance(trial, dict):
            continue
        groups["model"][str(trial.get("model_id", "UNKNOWN"))] += 1
        groups["density"][str(trial.get("density", "UNKNOWN"))] += 1
        groups["metadata_surface_condition"][str(trial.get("metadata_surface_condition", "UNKNOWN"))] += 1
        groups["attack_family"][str(trial.get("attack_family", "UNKNOWN"))] += 1
    return {key: dict(value) for key, value in groups.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test Phase 4.5 statistics parsing")
    parser.add_argument("--input", default="phase4_5/dryrun_results/local/trials.jsonl")
    parser.add_argument("--report", default=str(VALIDATION_DIR / "phase45_statistics_smoke_report.md"))
    args = parser.parse_args()

    input_path = Path(args.input)
    rows = load_rows(input_path)
    groups = group_counts(rows)
    official_rows = sum(1 for row in rows if row.get("official_trial") is True)
    counted_rows = sum(1 for row in rows if row.get("counts_for_phase5") is True)
    dry_run_rows = sum(1 for row in rows if row.get("dry_run") is True)
    outcome_fields_present = sum(
        1
        for row in rows
        if isinstance(row.get("trial"), dict)
        and any(
            field in row["trial"]
            for field in ("primary_outcome_class", "critical_exploit", "attack_success", "hijack_attempt", "utility_success")
        )
    )

    lines = [
        "# Phase 4.5 Statistics Smoke Report",
        "",
        f"- Input: `{input_path}`",
        f"- Row count: `{len(rows)}`",
        f"- Official rows: `{official_rows}`",
        f"- counts_for_phase5 rows: `{counted_rows}`",
        f"- dry_run rows: `{dry_run_rows}`",
        f"- Outcome-field rows discovered: `{outcome_fields_present}`",
        "",
        "## Grouping Summary",
    ]
    for group_name, counts in groups.items():
        lines.append(f"### {group_name}")
        if counts:
            for key, value in sorted(counts.items()):
                lines.append(f"- `{key}`: `{value}`")
        else:
            lines.append("- none")
    lines.extend(
        [
            "",
            "## Smoke Guardrails",
            "- final ASR must not be reported.",
            "- final exploit rate must not be reported.",
            "- vulnerability confirmed must not be reported.",
            "- defense effective must not be claimed.",
            "- robustness confirmed must not be claimed.",
            "- publishable result must not be reported.",
            "",
            "No Phase 4.5 row is valid for publication or Phase 5 inference.",
        ]
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
