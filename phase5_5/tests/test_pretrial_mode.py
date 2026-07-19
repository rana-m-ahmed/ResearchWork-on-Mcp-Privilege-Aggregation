from __future__ import annotations

from pathlib import Path

from phase5.cli import build_parser
from phase5.runtime.official_execution import ExecutedTrialResult


def test_pretrial_mode_is_distinct_from_official_and_plan_modes() -> None:
    args = build_parser().parse_args(
        [
            "run-campaign",
            "--pretrial",
            "--model-slot",
            "M1",
            "--dataset-version",
            "P5-DV-1.0.2-A7C91E42",
            "--run-id",
            "P5PRE-test",
            "--seal-epoch",
            "1",
            "--max-batches",
            "1",
        ]
    )
    assert args.pretrial is True
    assert args.official is False
    assert args.plan_only is False


def test_real_pretrial_result_passes_nonpublication_boundary(tmp_path: Path) -> None:
    result = ExecutedTrialResult(
        frozen_row_id="row-1",
        target_trial_id="T00001",
        attempt_id="P5ATT-T00001-A000-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
        raw_attempt_directory=tmp_path,
        elapsed_seconds=1.0,
        pipeline_executed=True,
        synthetic_fixture=False,
        official_trial=False,
        counts_for_phase5=False,
        publication_evidence=False,
        pretrial_mode=True,
    )
    result.validate_development_boundary()


def test_pretrial_cli_accepts_isolated_attempt_and_evidence_roots() -> None:
    parser = build_parser()
    args = parser.parse_args([
        "run-campaign",
        "--pretrial",
        "--model-slot",
        "M1",
        "--dataset-version",
        "P5-DV-1.0.2-A7C91E42",
        "--run-id",
        "P5PRE-test",
        "--seal-epoch",
        "1",
        "--attempts-root",
        "/tmp/pretrial-attempts",
        "--evidence-root",
        "/tmp/pretrial-evidence",
    ])
    assert args.attempts_root == "/tmp/pretrial-attempts"
    assert args.evidence_root == "/tmp/pretrial-evidence"
