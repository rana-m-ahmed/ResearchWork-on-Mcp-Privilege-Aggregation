"""Estimate Kaggle runtime feasibility from authentic Phase 4.5B smoke metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics

from _phase45_utils import DRYRUN_KAGGLE_DIR, DRYRUN_LOADER_DIR, VALIDATION_DIR


def load_hardware_metrics(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Estimate Phase 5 Kaggle runtime feasibility")
    parser.add_argument("--report", default=str(VALIDATION_DIR / "phase45_kaggle_quota_feasibility_report.md"))
    args = parser.parse_args()

    # We specifically want the expanded smoke inference times
    metrics_path = DRYRUN_KAGGLE_DIR / "hardware_metrics.jsonl"
    metrics = load_hardware_metrics(metrics_path)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    if not metrics:
        lines = [
            "# Phase 4.5 Kaggle Quota Feasibility Report",
            "",
            "- Status: `REVISE_PHASE45`",
            "- Reason: `REVISE_PHASE45 until Kaggle authentic smoke metrics are available.`",
            "- Kaggle authentic metrics available: `false`",
            "",
            "## Notes",
            "- No authentic Kaggle runtime measurements were found locally.",
            "- No runtime estimate was invented.",
            "- This report remains provisional until the authentic Kaggle Phase 4.5B executor returns metrics to GitHub.",
        ]
        report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("\n".join(lines))
        return 0

    inference_times = [m.get("inference_time_seconds", 0) for m in metrics if "inference_time_seconds" in m]
    
    if not inference_times:
        print("Metrics found, but missing inference_time_seconds.")
        return 0

    mean_time = statistics.mean(inference_times)
    p95_time = statistics.quantiles(inference_times, n=20)[18] if len(inference_times) > 1 else mean_time

    core_trials = 5400 # 4 models * 3 densities * 3 metadata * 150 accepted trials
    
    # Calculate Phase 5 requirements
    total_seconds_mean = core_trials * mean_time
    total_hours_mean = total_seconds_mean / 3600
    
    total_seconds_p95 = core_trials * p95_time
    total_hours_p95 = total_seconds_p95 / 3600

    # Kaggle allows max 12 hours per GPU session
    sessions_needed_mean = total_hours_mean / 11.0 # 11 hours safe buffer
    
    lines = [
        "# Phase 4.5 Kaggle Quota Feasibility Report",
        "",
        "- Status: `PENDING_REVIEW`",
        f"- Sample metric rows ingested: `{len(inference_times)}`",
        "",
        "## Real Timing Data",
        f"- Mean trial inference time: `{mean_time:.2f}s`",
        f"- P95 trial inference time: `{p95_time:.2f}s`",
        "",
        "## Phase 5 Core Trial Projections",
        "- Estimated total core trials: `5,400`",
        f"- Projected total runtime (mean): `{total_hours_mean:.2f} hours`",
        f"- Projected total runtime (P95): `{total_hours_p95:.2f} hours`",
        "",
        "## Quota Strategy",
        f"- Estimated Kaggle 12-hour sessions required: `{int(sessions_needed_mean) + 1}`",
        "- Checkpointing is required. Trials must be sharded across sessions to avoid timeout loss.",
        "",
        "## Notes",
        "- The above figures are calculated from the authentic Phase 4.5B Kaggle executor.",
        "- No Phase 5 claim is made in this report.",
    ]

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
