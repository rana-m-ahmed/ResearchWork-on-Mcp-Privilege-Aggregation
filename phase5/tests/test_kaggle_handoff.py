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
        source_branch="source/handoff",
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
        "source_branch",
        "model_branch",
        "evidence_branch",
        "approved_operational_limits",
    }


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
