from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase5.domain.errors import MissingFrozenSettingError, ResetFailureError, RuntimeMismatchError, SchemaInvariantError
from phase5.evidence.workspace import AttemptWorkspaceMetadata
from phase5.runtime import (
    AttemptWorkspaceIsolation,
    McpServerLauncher,
    ResetController,
    discover_tool_names,
    is_loopback_host,
    load_reset_failure_retry_limit,
    probe_reset_dispatch,
)
from server.mock_server import build_server


def _workspace(tmp_path: Path, attempt_suffix: str) -> AttemptWorkspaceMetadata:
    return AttemptWorkspaceMetadata.build(
        base_attempts_root=tmp_path / "phase5" / "attempts",
        base_evidence_root=tmp_path / "phase5" / "evidence",
        dataset_version="P5-DV-1.0.0-A7C91E42",
        frozen_row_id=f"row_{attempt_suffix}",
        target_trial_id=f"trial-{attempt_suffix}",
        attempt_id=f"P5ATT-trial-{attempt_suffix}-A000-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        attempt_status="DISPATCHED",
        created_utc="2026-07-08T00:00:00Z",
    )


def _build_isolation(tmp_path: Path, attempt_suffix: str) -> tuple[AttemptWorkspaceMetadata, AttemptWorkspaceIsolation]:
    metadata = _workspace(tmp_path, attempt_suffix)
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    (fixture_root / "seed.txt").write_text("frozen fixture\n", encoding="utf-8")
    isolation = AttemptWorkspaceIsolation.build(metadata, read_only_fixture_root=fixture_root)
    return metadata, isolation


def test_loopback_launcher_accepts_loopback_and_rejects_public_hosts(tmp_path: Path) -> None:
    launcher = McpServerLauncher(host="127.0.0.1", port=8000, server_factory=build_server)
    verified = launcher.validate()

    assert is_loopback_host("127.0.0.1") is True
    assert verified.host == "127.0.0.1"
    assert verified.reset_hidden is True
    assert "reset" not in verified.tool_names

    with pytest.raises(RuntimeMismatchError):
        McpServerLauncher(host="0.0.0.0", port=8000, server_factory=build_server).validate()


def test_discovery_surface_hides_reset_and_rejects_dispatch() -> None:
    server = build_server("D3-CLEAN")
    tool_names = discover_tool_names(server)
    probe = probe_reset_dispatch(server)

    assert "reset" not in tool_names
    assert probe.rejected is True
    assert probe.error_type == "ToolError"
    assert probe.error_message is not None
    assert "Unknown tool: reset" in probe.error_message


def test_workspace_isolation_copies_fixtures_and_rejects_traversal(tmp_path: Path) -> None:
    metadata_a, isolation_a = _build_isolation(tmp_path, "001")
    _, isolation_b = _build_isolation(tmp_path, "002")

    isolation_a.materialize()
    copied = isolation_a.copy_read_only_fixture("seed.txt", "frozen_row_snapshot.json")
    source = isolation_a.read_only_fixture_root / "seed.txt"
    original_bytes = source.read_bytes()

    assert copied.is_file()
    assert copied.read_text(encoding="utf-8") == "frozen fixture\n"

    copied.write_text("mutated copy\n", encoding="utf-8")
    assert source.read_bytes() == original_bytes

    with pytest.raises(SchemaInvariantError):
        isolation_a.copy_read_only_fixture("../escape.txt", "bad.json")

    with pytest.raises(SchemaInvariantError):
        isolation_a.write_json_snapshot("../escape.json", {"bad": True})

    with pytest.raises(SchemaInvariantError):
        isolation_a.assert_write_allowed(isolation_b.workspace_root / "cross_attempt.txt")

    with pytest.raises(MissingFrozenSettingError):
        isolation_a.assert_fixture_source_allowed(isolation_b.workspace_root / "seed.txt")


def test_reset_controller_writes_snapshots_and_clears_state(tmp_path: Path) -> None:
    metadata, isolation = _build_isolation(tmp_path, "003")
    controller = ResetController(
        workspace=isolation,
        reset_callable=lambda: {"runtime_state_cleared": True},
        verify_callable=lambda: {
            "event_log_empty": True,
            "extra_state_empty": True,
            "outbox_empty": True,
            "scratch_dir_empty": True,
            "trial_id_none": True,
        },
        retry_limit=0,
    )

    mock_sinks = {"sink": "value"}
    event_log = ["event-1"]
    server_state = {"alive": True}
    conversation_state = {"turn": 1}
    temp_file = metadata.raw_attempt_directory / "scratch" / "temp.txt"
    temp_file.parent.mkdir(parents=True, exist_ok=True)
    temp_file.write_text("temp\n", encoding="utf-8")

    outcome = controller.execute(
        mock_sinks=mock_sinks,
        event_log=event_log,
        temp_paths=(temp_file,),
        server_state=server_state,
        conversation_state=conversation_state,
    )

    assert outcome.status == "PASS"
    assert outcome.quarantined is False
    assert outcome.restart_count == 0
    assert not mock_sinks
    assert not event_log
    assert not server_state
    assert not conversation_state
    assert not temp_file.exists()

    for filename in ("mock_sink_snapshot_before.json", "mock_sink_snapshot_after.json", "reset_precheck.json", "reset_postcheck.json"):
        assert (isolation.workspace_root / filename).is_file()

    precheck = json.loads((isolation.workspace_root / "reset_precheck.json").read_text(encoding="utf-8"))
    postcheck = json.loads((isolation.workspace_root / "reset_postcheck.json").read_text(encoding="utf-8"))
    assert precheck["stage"] == "precheck"
    assert postcheck["stage"] == "postcheck"
    assert postcheck["verification_checks"]["outbox_empty"] is True


def test_reset_controller_restarts_and_quarantines_after_repeated_failure(tmp_path: Path) -> None:
    _, isolation = _build_isolation(tmp_path, "004")
    restart_calls: list[str] = []
    rerun_calls: list[str] = []
    retry_limit = load_reset_failure_retry_limit()
    controller = ResetController(
        workspace=isolation,
        reset_callable=lambda: {"runtime_state_cleared": True},
        verify_callable=lambda: {"outbox_empty": False},
        restart_callable=lambda: restart_calls.append("restart"),
        rerun_callable=lambda: rerun_calls.append("rerun"),
        retry_limit=retry_limit,
    )

    outcome = controller.execute(
        mock_sinks={"sink": "value"},
        event_log=["event-1"],
        temp_paths=(),
        server_state={"alive": True},
        conversation_state={"turn": 1},
    )

    assert outcome.status == "QUARANTINED"
    assert outcome.quarantined is True
    assert outcome.restart_count == retry_limit
    assert len(restart_calls) == retry_limit
    assert len(rerun_calls) == retry_limit
    assert controller.quarantined is True

    with pytest.raises(ResetFailureError):
        controller.execute()


def test_runtime_sources_do_not_reference_nested_docker_or_shell_invocation() -> None:
    runtime_files = [
        Path("phase5/runtime/mcp_server_launcher.py"),
        Path("phase5/runtime/reset_controller.py"),
        Path("phase5/runtime/workspace_isolation.py"),
    ]
    forbidden_terms = (
        "nested docker",
        "privileged container",
        "docker run",
        "docker exec",
        "docker socket",
        "docker-compose",
        "dockerd",
        "docker shell",
    )

    for path in runtime_files:
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden_terms:
            assert term not in text, f"{path.as_posix()} unexpectedly references {term!r}"
