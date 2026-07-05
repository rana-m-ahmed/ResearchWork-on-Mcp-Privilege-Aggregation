"""Estimate Kaggle runtime feasibility from available smoke metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from _phase45_utils import DRYRUN_KAGGLE_DIR, DRYRUN_LOADER_DIR, VALIDATION_DIR


def load_metric_rows(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def collect_metric_files() -> list[Path]:
    candidates: list[Path] = []
    for directory in (DRYRUN_KAGGLE_DIR, DRYRUN_LOADER_DIR):
        if directory.exists():
            candidates.extend(sorted(directory.glob("*.jsonl")))
            candidates.extend(sorted(directory.glob("*.json")))
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate Phase 5 Kaggle runtime feasibility")
    parser.add_argument("--report", default=str(VALIDATION_DIR / "phase45_kaggle_quota_feasibility_report.md"))
    args = parser.parse_args()

    metric_files = collect_metric_files()
    metric_rows = []
    for path in metric_files:
        metric_rows.extend(load_metric_rows(path))

    if not metric_rows:
        lines = [
            "# Phase 4.5 Kaggle Quota Feasibility Report",
            "",
            "- Status: `REVISE_PHASE45`",
            "- Reason: `REVISE_PHASE45 until Kaggle smoke metrics are available.`",
            "- Kaggle smoke metrics available: `false`",
            "",
            "## Notes",
            "- No Kaggle runtime measurements were found locally.",
            "- No runtime estimate was invented.",
            "- This report remains provisional until Kaggle execution returns metrics to GitHub.",
        ]
    else:
        total_rows = len(metric_rows)
        lines = [
            "# Phase 4.5 Kaggle Quota Feasibility Report",
            "",
            "- Status: `PENDING_REVIEW`",
            f"- Metric rows ingested: `{total_rows}`",
            "",
            "## Notes",
            "- Kaggle metrics were found locally and can be summarized in a later review pass.",
            "- No Phase 5 claim is made in this scaffold.",
        ]

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
