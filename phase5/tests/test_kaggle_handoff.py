from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from phase5.kaggle import (
    EDITABLE_PARAMETER_KEYS,
    NOTEBOOK_STAGE_SEQUENCE,
    KaggleHandoffParameters,
    build_bootstrap_plan,
    build_final_closure_plan,
    build_reverify_environment,
    build_session_plan,
    build_sync_barrier_plan,
    build_sync_environment,
    build_unified_campaign_plan,
    run_bootstrap,
    run_session,
    run_sync_barrier,
)
from phase5.domain.errors import SchemaInvariantError
from phase5.kaggle.validation import (
    extract_stage_sequence,
    load_notebook,
    validate_editable_parameter_whitelist,
    validate_notebook,
    validate_public_cli_only,
    validate_scans,
    validate_stage_sequence,
)


NOTEBOOK_PATH = Path("phase5/kaggle/phase5_runner.ipynb")
SCHEMA_PATH = Path("phase5/kaggle/manifests/phase5_runner_parameters.schema.json")
HANDOFF_SOURCE = Path("phase5/kaggle/handoff.py").read_text(encoding="utf-8")
NOTEBOOK = load_notebook(NOTEBOOK_PATH)


def _parameters() -> KaggleHandoffParameters:
    return KaggleHandoffParameters(
        repository_branch="repo/handoff",
        source_tag_or_commit="phase5-official-source-v2",
        model_branch="model/handoff",
        evidence_branch="evidence/handoff",
        approved_operational_limits={
            "safe_session_hours": 7.5,
            "checkpoint_barrier_interval_trials": 6,
        },
    )


def test_notebook_json_parses_and_preserves_stage_order() -> None:
    assert NOTEBOOK["nbformat"] == 4
    assert NOTEBOOK["nbformat_minor"] == 5
    assert extract_stage_sequence(NOTEBOOK) == NOTEBOOK_STAGE_SEQUENCE
    assert validate_stage_sequence(NOTEBOOK) == []


def test_notebook_static_scans_pass() -> None:
    secret_findings, forbidden_findings = validate_scans(NOTEBOOK)
    assert secret_findings == []
    assert forbidden_findings == []


def test_notebook_parameter_whitelist_matches_schema() -> None:
    issues = validate_editable_parameter_whitelist(NOTEBOOK, SCHEMA_PATH)
    assert issues == []
    assert set(EDITABLE_PARAMETER_KEYS) == {
        "repository_branch",
        "source_tag_or_commit",
        "model_branch",
        "evidence_branch",
        "approved_operational_limits",
    }
    assert "source_tag_or_commit" in json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["required"]


def test_notebook_requires_detached_source_checkout_and_verification() -> None:
    text = json.dumps(NOTEBOOK)
    assert "SOURCE_TAG_OR_COMMIT" in text
    assert "EXPECTED_SOURCE_COMMIT" in text
    assert "--detach" in text
    assert "branch HEAD execution is prohibited" in text


def test_handoff_defaults_to_reconciled_v2_run_plan() -> None:
    from phase5.kaggle import DEFAULT_BATCH_MANIFEST, DEFAULT_RUN_PLAN

    assert DEFAULT_RUN_PLAN.as_posix() == "phase5/validation/kaggle_run_plan_v2.json"
    assert DEFAULT_BATCH_MANIFEST.as_posix() == "phase5/manifests/batch_partition_manifest_v2.json"


def test_m4_reconciled_run_plan_is_active_and_evidence_bound() -> None:
    plan = json.loads(Path("phase5/validation/kaggle_run_plan_v2.json").read_text(encoding="utf-8"))
    recon = json.loads(Path("phase5/validation/m4_loader_status_reconciliation.json").read_text(encoding="utf-8"))
    m4_plan = next(item for item in plan["model_plans"] if item["model_slot"] == "M4")
    m4_status = next(item for item in plan["timing_evidence"]["model_load_status"] if item["model_slot"] == "M4")

    assert recon["prior_status"] == "LOAD_FAILURE"
    assert recon["final_non_official_kaggle_status"] == "PASS"
    assert recon["official_trials_executed"] == 0
    assert m4_plan["model_load_status"] == "LOAD_SUCCESS"
    assert m4_status["status"] == "LOAD_SUCCESS"
    assert plan["dataset_version"] == "P5-DV-1.0.1-A7C91E42"
    assert {
        "label": "M4 loader status reconciliation",
        "sha256": "b3893e14ac5203f3021f128ffd4f13f49af19a745eaca74a9a4664d12fefb112",
    } in plan["source_evidence"]


def test_notebook_public_cli_only_contract_holds() -> None:
    issues = validate_public_cli_only(NOTEBOOK, HANDOFF_SOURCE)
    assert issues == []
    report = validate_notebook(NOTEBOOK_PATH, SCHEMA_PATH, handoff_source=HANDOFF_SOURCE)
    assert report.status == "PASS"
    assert report.stage_sequence == NOTEBOOK_STAGE_SEQUENCE


def test_bootstrap_and_plan_builders_use_public_cli_prefix() -> None:
    parameters = _parameters()
    bootstrap = build_bootstrap_plan(parameters)
    campaign = build_unified_campaign_plan(parameters)
    assert bootstrap.commands[0].argv[:3] == (sys.executable, "-m", "phase5")
    assert campaign.commands[0].argv[:3] == (sys.executable, "-m", "phase5")


def test_sync_environment_mapping_uses_secret_names_only() -> None:
    env = {
        "GITHUB_WRITE_TOKEN_PHASE5": "write-token",
        "GITHUB_READ_TOKEN_PHASE5": "read-token",
        "EXTRA": "value",
    }
    sync_env = build_sync_environment(env)
    assert sync_env["GITHUB_TOKEN"] == "write-token"
    assert sync_env["GITHUB_READ_TOKEN_PHASE5"] == "read-token"
    reverify_env = build_reverify_environment(sync_env)
    assert "GITHUB_TOKEN" not in reverify_env
    assert "GITHUB_WRITE_TOKEN_PHASE5" not in reverify_env


def test_sync_environment_refuses_missing_write_secret() -> None:
    with pytest.raises(SchemaInvariantError):
        build_sync_environment({"GITHUB_READ_TOKEN_PHASE5": "read-token"})


def test_public_cli_wrapper_smoke_and_sync_reseal_order(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    parameters = _parameters()
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("phase5.kaggle.handoff.subprocess.run", fake_run)

    bootstrap = run_bootstrap(parameters, cwd=tmp_path)
    assert len(bootstrap) == 2

    session = run_session(parameters, model_slot="M1", cwd=tmp_path)
    assert len(session) == 2

    barrier = run_sync_barrier(
        parameters,
        manifest_path=tmp_path / "manifest.json",
        receipt_path=tmp_path / "receipt.json",
        cwd=tmp_path,
        env={"GITHUB_WRITE_TOKEN_PHASE5": "write-token"},
    )
    assert len(barrier) == 4

    expected = [
        "gate0",
        "plan-kaggle-runs",
        "session-seal",
        "run-campaign",
        "session-close-seal",
        "sync-github",
        "session-reverify",
        "session-seal",
    ]
    assert [command[3] for command in captured] == expected


def test_sync_barrier_stops_after_sync_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    parameters = _parameters()
    captured: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured.append(list(cmd))
        if cmd[3] == "sync-github":
            raise subprocess.CalledProcessError(returncode=1, cmd=cmd, output="", stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr("phase5.kaggle.handoff.subprocess.run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        run_sync_barrier(
            parameters,
            manifest_path=tmp_path / "manifest.json",
            receipt_path=tmp_path / "receipt.json",
            cwd=tmp_path,
            env={"GITHUB_WRITE_TOKEN_PHASE5": "write-token"},
        )

    assert [command[3] for command in captured] == ["session-close-seal", "sync-github"]


def test_final_closure_plan_requires_reverify_before_reseal() -> None:
    plan = build_final_closure_plan(_parameters())
    assert [command.stage for command in plan.commands] == [
        "final_closure_sync",
        "final_closure_sync",
        "final_closure_sync",
        "final_closure_sync",
    ]
    assert [command.argv[3] for command in plan.commands] == [
        "session-close-seal",
        "sync-github",
        "session-reverify",
        "session-seal",
    ]
