from __future__ import annotations

from pathlib import Path

import pytest

from phase5.attempts import (
    AttemptLineageRecord,
    AttemptLineageStore,
    build_recovery_plan,
    build_replacement_lineage_record,
    build_replacement_workspace,
    discover_orphan_attempts,
)
from phase5.domain.identifiers import AttemptId, EventId
from phase5.domain.errors import FrozenArtifactHashError, SchemaInvariantError
from phase5.evidence import (
    AttemptEvent,
    AttemptEventLogWriter,
    AttemptEventType,
    AttemptWorkspaceMetadata,
    ContentAddressedArtifactWriter,
    RawArtifactRecord,
    load_attempt_events,
    validate_raw_artifact,
)


def _attempt_id() -> str:
    return str(AttemptId.build("trial-001", 0, "ABCDEF12"))


def _workspace(tmp_path: Path) -> AttemptWorkspaceMetadata:
    attempt_id = _attempt_id()
    return AttemptWorkspaceMetadata.build(
        base_attempts_root=tmp_path / "phase5" / "attempts",
        base_evidence_root=tmp_path / "phase5" / "evidence",
        dataset_version="P5-DV-1.0.0-A7C91E42",
        frozen_row_id="row_001",
        target_trial_id="trial-001",
        attempt_id=attempt_id,
        attempt_index=0,
        parent_attempt_id=None,
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        attempt_status="DISPATCHED",
        created_utc="2026-07-08T00:00:00Z",
    )


def _build_event(workspace: AttemptWorkspaceMetadata, sequence: int, event_type: AttemptEventType, artifact_ref: str | None = None, artifact_sha256: str | None = None) -> AttemptEvent:
    return AttemptEvent(
        event_id=EventId.build(workspace.attempt_id, sequence),
        dataset_version=workspace.dataset_version,
        frozen_row_id=workspace.frozen_row_id,
        target_trial_id=workspace.target_trial_id,
        attempt_id=workspace.attempt_id,
        run_id=workspace.run_id,
        batch_id=workspace.batch_id,
        event_sequence=sequence,
        event_type=event_type,
        timestamp_utc=f"2026-07-08T00:00:{sequence:02d}Z",
        artifact_ref=artifact_ref,
        artifact_sha256=artifact_sha256,
        details={"event_type": event_type.value},
    )


def _simulate_attempt_until_crash(
    workspace: AttemptWorkspaceMetadata,
    *,
    stop_after: str,
) -> tuple[list[AttemptEvent], RawArtifactRecord | None]:
    event_writer = AttemptEventLogWriter(workspace.event_log_path)
    artifact_writer = ContentAddressedArtifactWriter(workspace.raw_attempt_directory)
    prompt_record = artifact_writer.write_text(
        "compiled prompt\nwith preserved line endings\n",
        artifact_type="compiled_prompt",
        line_ending="\n",
    )
    event_writer.append(_build_event(workspace, 1, AttemptEventType.PREPARED, artifact_ref=prompt_record.relative_path.as_posix(), artifact_sha256=prompt_record.sha256))
    if stop_after == "after_prepared":
        raise RuntimeError("simulated crash")

    event_writer.append(_build_event(workspace, 2, AttemptEventType.DISPATCHED, artifact_ref=prompt_record.relative_path.as_posix(), artifact_sha256=prompt_record.sha256))
    if stop_after == "after_dispatched":
        raise RuntimeError("simulated crash")

    model_record = artifact_writer.write_text("model output\n", artifact_type="model_output", line_ending="\n")
    event_writer.append(_build_event(workspace, 3, AttemptEventType.MODEL_OUTPUT_CAPTURED, artifact_ref=model_record.relative_path.as_posix(), artifact_sha256=model_record.sha256))
    if stop_after == "after_model_output":
        raise RuntimeError("simulated crash")

    tool_record = artifact_writer.write_text("tool event\n", artifact_type="tool_event", line_ending="\n")
    event_writer.append(_build_event(workspace, 4, AttemptEventType.TOOL_EVENT, artifact_ref=tool_record.relative_path.as_posix(), artifact_sha256=tool_record.sha256))
    if stop_after == "after_tool_event":
        raise RuntimeError("simulated crash")

    reset_record = artifact_writer.write_text("reset\n", artifact_type="reset_check", line_ending="\n")
    event_writer.append(_build_event(workspace, 5, AttemptEventType.RESET_CHECKED, artifact_ref=reset_record.relative_path.as_posix(), artifact_sha256=reset_record.sha256))
    if stop_after == "after_reset_event":
        raise RuntimeError("simulated crash")

    graded_record = artifact_writer.write_text("graded\n", artifact_type="graded", line_ending="\n")
    event_writer.append(_build_event(workspace, 6, AttemptEventType.GRADED, artifact_ref=graded_record.relative_path.as_posix(), artifact_sha256=graded_record.sha256))
    event_writer.append(_build_event(workspace, 7, AttemptEventType.TRIAL_ROW_MATERIALIZED, artifact_ref=graded_record.relative_path.as_posix(), artifact_sha256=graded_record.sha256))
    if stop_after == "before_final_row":
        raise RuntimeError("simulated crash")

    event_writer.append(_build_event(workspace, 8, AttemptEventType.FINALIZED, artifact_ref=graded_record.relative_path.as_posix(), artifact_sha256=graded_record.sha256))
    return load_attempt_events(workspace.event_log_path), prompt_record


@pytest.mark.parametrize(
    "stop_after,expect_orphan",
    [
        ("after_prepared", False),
        ("after_dispatched", True),
        ("after_model_output", True),
        ("after_tool_event", True),
        ("after_reset_event", True),
        ("before_final_row", True),
    ],
)
def test_simulated_crashes_leave_durable_prefix_and_orphan_state(tmp_path: Path, stop_after: str, expect_orphan: bool) -> None:
    workspace = _workspace(tmp_path)
    with pytest.raises(RuntimeError):
        _simulate_attempt_until_crash(workspace, stop_after=stop_after)

    events = load_attempt_events(workspace.event_log_path)
    assert events
    assert events[-1].event_type is not AttemptEventType.FINALIZED
    orphans = discover_orphan_attempts([workspace])
    assert bool(orphans) is expect_orphan


def test_event_writer_fsyncs_and_rejects_duplicate_finalization(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    workspace = _workspace(tmp_path)
    calls: list[int] = []
    monkeypatch.setattr("os.fsync", lambda fd: calls.append(fd))

    writer = AttemptEventLogWriter(workspace.event_log_path)
    writer.append(_build_event(workspace, 1, AttemptEventType.PREPARED))
    writer.append(_build_event(workspace, 2, AttemptEventType.DISPATCHED))
    writer.append(_build_event(workspace, 3, AttemptEventType.FINALIZED))

    assert calls
    with pytest.raises(SchemaInvariantError):
        writer.append(_build_event(workspace, 4, AttemptEventType.FINALIZED))


def test_partial_jsonl_lines_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "attempt_events.jsonl"
    path.write_text('{"event_id":"P5EVT-trial-001-A000-ABCDEF12-0001"}\n{"event_id":"P5EVT-trial-001-A000-ABCDEF12-0002"', encoding="utf-8")

    with pytest.raises(SchemaInvariantError):
        load_attempt_events(path)


def test_content_addressed_artifact_writer_preserves_bytes_and_detects_corruption(tmp_path: Path) -> None:
    writer = ContentAddressedArtifactWriter(tmp_path / "artifacts")
    record = writer.write_text("line one\r\nline two\n", artifact_type="compiled_prompt", encoding="utf-8")

    assert record.relative_path.name.startswith("P5ART-")
    validate_raw_artifact(record, root=tmp_path / "artifacts")

    target = tmp_path / "artifacts" / record.relative_path
    target.write_bytes(b"corrupted bytes")
    with pytest.raises(FrozenArtifactHashError):
        validate_raw_artifact(record, root=tmp_path / "artifacts")


def test_recovery_is_idempotent_and_retains_parent_lineage(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    with pytest.raises(RuntimeError):
        _simulate_attempt_until_crash(workspace, stop_after="after_dispatched")

    orphan = discover_orphan_attempts([workspace])[0]
    replacement = build_replacement_workspace(
        orphan,
        base_attempts_root=tmp_path / "phase5" / "attempts",
        base_evidence_root=tmp_path / "phase5" / "evidence",
        session_token="ABCDEF12",
        created_utc="2026-07-08T00:05:00Z",
    )
    assert replacement.parent_attempt_id == workspace.attempt_id
    lineage_record = build_replacement_lineage_record(replacement)
    store = AttemptLineageStore(replacement.lineage_path)
    store.append(lineage_record)
    store.append(lineage_record)

    records = store.load_records()
    assert len(records) == 1
    assert records[0].parent_attempt_id == workspace.attempt_id

    plan = build_recovery_plan(
        [workspace],
        base_attempts_root=tmp_path / "phase5" / "attempts",
        base_evidence_root=tmp_path / "phase5" / "evidence",
        session_token="ABCDEF12",
        created_utc="2026-07-08T00:05:00Z",
    )
    assert plan.orphan_attempts[0].attempt_id == workspace.attempt_id
    assert plan.replacement_lineage_records[0].parent_attempt_id == workspace.attempt_id


def test_lineage_snapshot_write_is_atomic_and_append_only(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    store = AttemptLineageStore(workspace.lineage_path)
    record = AttemptLineageRecord(
        dataset_version=workspace.dataset_version,
        frozen_row_id=workspace.frozen_row_id,
        target_trial_id=workspace.target_trial_id,
        attempt_id=workspace.attempt_id,
        attempt_index=workspace.attempt_index,
        parent_attempt_id=None,
        run_id=workspace.run_id,
        batch_id=workspace.batch_id,
        attempt_status="DISPATCHED",
        invalid_reason=None,
        counts_toward_cell_n=False,
        accepted_attempt=False,
        raw_attempt_directory=workspace.raw_attempt_directory,
    )

    with pytest.raises(RuntimeError):
        store.write_snapshot([record], before_replace_hook=lambda: (_ for _ in ()).throw(RuntimeError("crash")))

    assert not workspace.lineage_path.exists()
    store.write_snapshot([record])
    assert workspace.lineage_path.is_file()


def test_atomic_manifest_write_is_crash_safe(tmp_path: Path) -> None:
    workspace = _workspace(tmp_path)
    with pytest.raises(RuntimeError):
        workspace.write_manifest(before_replace_hook=lambda: (_ for _ in ()).throw(RuntimeError("crash")))
    assert not workspace.manifest_path.exists()

    workspace.write_manifest()
    assert workspace.manifest_path.is_file()
