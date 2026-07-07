from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from phase5.cli import PLANNED_COMMANDS, build_parser
from phase5.domain import BatchId, DefenseCondition, Density, MetadataSurfaceCondition, ModelSlot, TrialPhase


def test_cli_help_exposes_planned_commands() -> None:
    help_text = build_parser().format_help()
    for command in PLANNED_COMMANDS:
        assert command in help_text


def test_module_help_and_not_implemented_command() -> None:
    help_result = subprocess.run(
        [sys.executable, "-m", "phase5", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    for command in ("validate-batch", "run-batch", "sync-github"):
        assert command in help_result.stdout

    assert "gate0" in help_result.stdout

    gate0_help = subprocess.run(
        [sys.executable, "-m", "phase5", "gate0", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert gate0_help.returncode == 0
    assert "--strict" in gate0_help.stdout

    batch_id = BatchId.build(
        dataset="P5-DV-1.0.0-A7C91E42",
        workload=TrialPhase.PHASE5_ADVERSARIAL_CORE,
        model=ModelSlot.M1,
        density_or_mix=Density.D3,
        surface_or_mix=MetadataSurfaceCondition.POISON_TD,
        defense=DefenseCondition.BASELINE,
        run_token="ABCDEF12",
        slice_token="A1B2",
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "validate-batch",
            "--batch-id",
            str(batch_id),
            "--strict",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 90
    assert "NOT_IMPLEMENTED" in result.stderr


def test_plan_kaggle_runs_cli_writes_outputs(tmp_path: Path) -> None:
    output = tmp_path / "kaggle_run_plan.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "plan-kaggle-runs",
            "--timing-report",
            "phase4_5/validation/phase45_kaggle_quota_feasibility_report.md",
            "--safe-session-hours",
            "7.5",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert output.is_file()
    assert output.with_suffix(".md").is_file()
    assert (Path("phase5/manifests/batch_partition_manifest.json")).is_file()
