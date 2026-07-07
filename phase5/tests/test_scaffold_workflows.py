from __future__ import annotations

from pathlib import Path

import pytest

from phase5.guards import validate_report_json


def _workflow_text(name: str) -> str:
    return Path(".github/workflows") / name


def test_source_ci_workflow_covers_required_check_classes() -> None:
    yaml = pytest.importorskip("yaml")
    workflow = yaml.safe_load(_workflow_text("phase5-source-ci.yml").read_text(encoding="utf-8"))
    step_names = [step.get("name", "") for step in workflow["jobs"]["checks"]["steps"] if isinstance(step, dict)]

    expected = [
        "Formatting and lint",
        "Type checks",
        "Instruction hierarchy",
        "Unit tests",
        "Integration tests",
        "Schema tests",
        "Golden-vector tests",
        "State-machine tests",
        "Checkpoint/resume tests",
        "Forbidden analysis lint",
        "Secret lint",
        "Workflow syntax parse",
    ]
    for item in expected:
        assert item in step_names


def test_evidence_integrity_workflow_targets_checkpoint_manifest() -> None:
    text = _workflow_text("phase5-evidence-integrity.yml").read_text(encoding="utf-8")
    assert "P01_checkpoint.json" in text
    assert "P01_implementation_report.md" not in text
    assert "expected rejection observed" in text


def test_checkpoint_manifest_schema_is_present() -> None:
    report = Path("phase5/implementation/reports/P01_checkpoint.json")
    required = [
        "dataset_version",
        "model_slot",
        "workload",
        "run_id",
        "batch_id",
        "source_commit",
        "phase4_lock_hash",
        "phase45_go_hash",
        "expected_remote_head_before_push",
        "accepted_finalized_count",
        "invalid_attempt_count",
        "orphan_attempt_count",
        "batch_manifest_sha256",
        "evidence_index_sha256",
        "session_seal_closed",
        "no_more_official_execution_in_session",
    ]
    assert validate_report_json(report, required) == []


def test_checkpoint_manifest_missing_key_fails_closed(tmp_path: Path) -> None:
    manifest = tmp_path / "checkpoint.json"
    manifest.write_text(
        '{"dataset_version": "<pending>", "model_slot": "<pending>"}',
        encoding="utf-8",
    )

    missing = validate_report_json(
        manifest,
        required_keys=[
            "dataset_version",
            "model_slot",
            "workload",
            "run_id",
        ],
    )
    assert missing == ["workload", "run_id"]


def test_negative_fixture_workflows_assert_rejection() -> None:
    freeze_guard = _workflow_text("phase5-freeze-guard.yml").read_text(encoding="utf-8")
    evidence = _workflow_text("phase5-evidence-integrity.yml").read_text(encoding="utf-8")

    assert "phase5 frozen path guard unexpectedly passed" in freeze_guard
    assert "phase5 evidence staging guard unexpectedly passed" in evidence
