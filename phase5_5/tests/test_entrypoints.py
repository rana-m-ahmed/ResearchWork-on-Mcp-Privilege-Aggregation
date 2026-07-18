from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from phase5.cli import build_parser


def test_qualification_canary_script_entrypoint_resolves_repo_imports() -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(root / "phase5_5/scripts/run_qualification_canary.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--root" in completed.stdout


def test_official_campaign_parser_uses_phase5_5_entrypoint_contract() -> None:
    parser = build_parser()
    args = parser.parse_args(
        [
            "run-campaign",
            "--official",
            "--model-slot",
            "M1",
            "--dataset-version",
            "P5-DV-1.0.2-A7C91E42",
            "--run-id",
            "P5RUN-P5-DV-1.0.2-A7C91E42-M1-20260718-ABCDEF12",
            "--seal-epoch",
            "1",
            "--until-safety-horizon",
        ]
    )
    assert args.batch_manifest.endswith("batch_partition_manifest_v3.json")
    assert args.run_plan.endswith("kaggle_run_plan_v3.json")
