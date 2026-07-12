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


def test_official_campaign_commands_default_to_reconciled_v2_plan() -> None:
    parser = build_parser()
    for command in ("checkpoint-status", "resume-plan", "run-campaign"):
        args = parser.parse_args([command, "--model-slot", "M1"] if command != "run-campaign" else [
            command,
            "--model-slot",
            "M1",
            "--run-id",
            "P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260710-ABCDEF12",
            "--utcdate",
            "20260710",
            "--plan-only",
        ])
        assert args.run_plan == "phase5/validation/kaggle_run_plan_v2.json"
        assert args.batch_manifest == "phase5/manifests/batch_partition_manifest_v2.json"


def test_module_help_and_not_implemented_command() -> None:
    help_result = subprocess.run(
        [sys.executable, "-m", "phase5", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert help_result.returncode == 0
    for command in ("validate-batch", "run-batch", "sync-github", "session-reverify", "run-campaign", "checkpoint-status"):
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
        dataset="P5-DV-1.0.1-A7C91E42",
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
    assert (Path("phase5/manifests/batch_partition_manifest_v2.json")).is_file()


def test_campaign_cli_smoke_writes_operational_reports(tmp_path: Path) -> None:
    session_output = tmp_path / "session_open.json"
    status_output = tmp_path / "checkpoint_status.md"
    campaign_output = tmp_path / "campaign_run.json"

    batch_id = BatchId.build(
        dataset="P5-DV-1.0.0-A7C91E42",
        workload=TrialPhase.PHASE5_ADVERSARIAL_CORE,
        model=ModelSlot.M1,
        density_or_mix=Density.D3,
        surface_or_mix=MetadataSurfaceCondition.POISON_TD,
        defense=DefenseCondition.BASELINE,
        run_token="ABCDEF12",
        slice_token="1A2B",
    )
    open_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "session-open",
            "--model-slot",
            "M1",
            "--batch-id",
            str(batch_id),
            "--output",
            str(session_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert open_result.returncode == 0
    assert session_output.is_file()
    assert session_output.with_suffix(".md").is_file()

    status_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "checkpoint-status",
            "--model-slot",
            "M1",
            "--output",
            str(status_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert status_result.returncode == 0
    assert status_output.is_file()
    assert status_output.with_suffix(".json").is_file()

    campaign_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "run-campaign",
            "--model-slot",
            "M1",
            "--run-id",
            "P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12",
            "--utcdate",
            "20260708",
            "--until-safety-horizon",
            "--max-batches",
            "1",
            "--plan-only",
            "--output",
            str(campaign_output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert campaign_result.returncode == 0
    assert campaign_output.is_file()
    assert campaign_output.with_suffix(".md").is_file()
