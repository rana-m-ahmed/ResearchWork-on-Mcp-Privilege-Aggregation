"""Internal reset controller for the Phase 5 runtime boundary."""

from __future__ import annotations

import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping, MutableSequence, Sequence

from ..domain.errors import ResetFailureError, SchemaInvariantError
from ..guards import repo_root
from ..evidence.workspace import AttemptWorkspaceMetadata
from .workspace_isolation import AttemptWorkspaceIsolation, build_attempt_workspace_isolation

try:  # pragma: no cover - validated in tests
    from server.reset_endpoint import perform_reset as default_reset_callable
    from server.reset_endpoint import verify_reset_clean as default_verify_callable
except Exception:  # pragma: no cover
    default_reset_callable = None
    default_verify_callable = None


RESET_PRECHECK_FILENAME = "reset_precheck.json"
RESET_POSTCHECK_FILENAME = "reset_postcheck.json"
MOCK_SINK_BEFORE_FILENAME = "mock_sink_snapshot_before.json"
MOCK_SINK_AFTER_FILENAME = "mock_sink_snapshot_after.json"
_RESET_RETRY_PATTERN = re.compile(r"(?i)\b(\d+)\s+reruns?\s+after\s+full\s+environment\s+restart\b")


def load_reset_failure_retry_limit(root: Path | None = None) -> int:
    """Derive the reset retry limit from the frozen registry evidence."""

    repository_root = (root or repo_root()).resolve()
    registry_path = repository_root / "phase5" / "configs" / "upstream_artifact_registry.json"
    if not registry_path.is_file():
        raise SchemaInvariantError(f"upstream registry is missing: {registry_path.as_posix()}")
    data = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    try:
        retry_policy = data["state_machine_controls"]["retry_policy_summary"]["reset_failure"]
    except KeyError as exc:
        raise SchemaInvariantError("frozen retry policy is missing reset_failure") from exc
    if not isinstance(retry_policy, str) or not retry_policy.strip():
        raise SchemaInvariantError("frozen retry policy must be a non-empty string")
    match = _RESET_RETRY_PATTERN.search(retry_policy)
    if match is None:
        raise SchemaInvariantError(f"could not derive reset retry limit from frozen policy: {retry_policy!r}")
    return int(match.group(1))


def _clear_mapping(mapping: MutableMapping[str, Any] | None) -> None:
    if mapping is not None:
        mapping.clear()


def _clear_sequence(sequence: MutableSequence[Any] | None) -> None:
    if sequence is not None:
        del sequence[:]


def _normalize_state(state: Mapping[str, Any] | None) -> dict[str, Any]:
    return dict(state or {})


def _delete_temp_paths(workspace: AttemptWorkspaceIsolation, temp_paths: Sequence[Path] | None) -> None:
    for temp_path in temp_paths or ():
        if temp_path.is_dir() and not temp_path.is_symlink():
            workspace.remove_path(temp_path)
            continue
        workspace.remove_path(temp_path)


@dataclass(frozen=True, slots=True)
class ResetOutcome:
    status: str
    attempts: int
    restart_count: int
    quarantined: bool
    precheck_path: Path
    postcheck_path: Path
    mock_sink_before_path: Path
    mock_sink_after_path: Path
    verification_checks: tuple[tuple[str, bool], ...]
    reset_response: tuple[tuple[str, Any], ...]
    notes: tuple[str, ...] = ()


@dataclass
class ResetController:
    """Run the internal reset control path with fail-closed fallback."""

    workspace: AttemptWorkspaceIsolation
    reset_callable: Callable[[], Mapping[str, Any]] | None = default_reset_callable
    verify_callable: Callable[[], Mapping[str, bool]] | None = default_verify_callable
    restart_callable: Callable[[], Any] | None = None
    rerun_callable: Callable[[], Any] | None = None
    retry_limit: int = 0
    failure_count: int = 0
    quarantined: bool = False

    @classmethod
    def build(
        cls,
        metadata: AttemptWorkspaceMetadata,
        *,
        read_only_fixture_root: Path,
        retry_limit: int | None = None,
    ) -> "ResetController":
        workspace = build_attempt_workspace_isolation(metadata, read_only_fixture_root=read_only_fixture_root)
        return cls(
            workspace=workspace,
            retry_limit=retry_limit if retry_limit is not None else load_reset_failure_retry_limit(),
        )

    def _write_snapshot(self, filename: str, payload: Mapping[str, Any]) -> Path:
        return self.workspace.write_json_snapshot(filename, payload)

    def _clear_local_state(
        self,
        *,
        mock_sinks: MutableMapping[str, Any] | None = None,
        event_log: MutableSequence[Any] | None = None,
        temp_paths: Sequence[Path] | None = None,
        server_state: MutableMapping[str, Any] | None = None,
        conversation_state: MutableMapping[str, Any] | None = None,
    ) -> None:
        _clear_mapping(mock_sinks)
        _clear_sequence(event_log)
        _clear_mapping(server_state)
        _clear_mapping(conversation_state)
        _delete_temp_paths(self.workspace, temp_paths)

    def _state_payload(
        self,
        *,
        stage: str,
        mock_sinks: Mapping[str, Any] | None = None,
        event_log: Sequence[Any] | None = None,
        temp_paths: Sequence[Path] | None = None,
        server_state: Mapping[str, Any] | None = None,
        conversation_state: Mapping[str, Any] | None = None,
        reset_response: Mapping[str, Any] | None = None,
        verification_checks: Mapping[str, bool] | None = None,
        restart_count: int = 0,
        attempts: int = 0,
        notes: Sequence[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "attempt_id": self.workspace.metadata.attempt_id,
            "attempts": attempts,
            "conversation_state": _normalize_state(conversation_state),
            "event_log": list(event_log or []),
            "failure_count": self.failure_count,
            "mock_sinks": _normalize_state(mock_sinks),
            "notes": list(notes or ()),
            "reset_response": _normalize_state(reset_response),
            "restart_count": restart_count,
            "server_state": _normalize_state(server_state),
            "stage": stage,
            "temp_paths": [path.as_posix() for path in (temp_paths or ())],
            "verification_checks": dict(verification_checks or {}),
            "workspace": self.workspace.capture_state_snapshot(
                mock_sinks=mock_sinks,
                event_log=event_log,
                temp_paths=temp_paths,
                server_state=server_state,
                conversation_state=conversation_state,
            ),
        }

    def execute(
        self,
        *,
        mock_sinks: MutableMapping[str, Any] | None = None,
        event_log: MutableSequence[Any] | None = None,
        temp_paths: Sequence[Path] | None = None,
        server_state: MutableMapping[str, Any] | None = None,
        conversation_state: MutableMapping[str, Any] | None = None,
    ) -> ResetOutcome:
        if self.quarantined:
            raise ResetFailureError("reset controller is quarantined")

        temp_paths = tuple(temp_paths or ())
        before_payload = self._state_payload(
            stage="precheck",
            mock_sinks=mock_sinks,
            event_log=event_log,
            temp_paths=temp_paths,
            server_state=server_state,
            conversation_state=conversation_state,
        )
        mock_sink_before_path = self._write_snapshot(MOCK_SINK_BEFORE_FILENAME, before_payload)
        precheck_path = self._write_snapshot(RESET_PRECHECK_FILENAME, before_payload)

        notes: list[str] = []
        restart_count = 0
        attempts = 0
        verification_checks: dict[str, bool] = {}
        reset_response: dict[str, Any] = {}

        for attempt_index in range(self.retry_limit + 1):
            attempts = attempt_index + 1
            try:
                reset_response = dict(self.reset_callable() if self.reset_callable is not None else {})
            except Exception as exc:
                notes.append(f"reset attempt {attempts} raised {type(exc).__name__}: {exc}")
                reset_response = {"error": type(exc).__name__, "detail": str(exc)}

            self._clear_local_state(
                mock_sinks=mock_sinks,
                event_log=event_log,
                temp_paths=temp_paths,
                server_state=server_state,
                conversation_state=conversation_state,
            )

            try:
                verification_checks = dict(self.verify_callable() if self.verify_callable is not None else {})
            except Exception as exc:
                notes.append(f"verification raised {type(exc).__name__}: {exc}")
                verification_checks = {"verification_error": False}

            if verification_checks and all(verification_checks.values()):
                self.failure_count = 0
                self.quarantined = False
                post_payload = self._state_payload(
                    stage="postcheck",
                    mock_sinks=mock_sinks,
                    event_log=event_log,
                    temp_paths=temp_paths,
                    server_state=server_state,
                    conversation_state=conversation_state,
                    reset_response=reset_response,
                    verification_checks=verification_checks,
                    restart_count=restart_count,
                    attempts=attempts,
                    notes=notes,
                )
                mock_sink_after_path = self._write_snapshot(MOCK_SINK_AFTER_FILENAME, post_payload)
                postcheck_path = self._write_snapshot(RESET_POSTCHECK_FILENAME, post_payload)
                return ResetOutcome(
                    status="PASS",
                    attempts=attempts,
                    restart_count=restart_count,
                    quarantined=False,
                    precheck_path=precheck_path,
                    postcheck_path=postcheck_path,
                    mock_sink_before_path=mock_sink_before_path,
                    mock_sink_after_path=mock_sink_after_path,
                    verification_checks=tuple(sorted(verification_checks.items())),
                    reset_response=tuple(sorted(reset_response.items())),
                    notes=tuple(notes),
                )

            self.failure_count += 1
            if attempt_index < self.retry_limit:
                restart_count += 1
                if self.restart_callable is not None:
                    self.restart_callable()
                if self.rerun_callable is not None:
                    self.rerun_callable()
                continue

            self.quarantined = True
            post_payload = self._state_payload(
                stage="postcheck",
                mock_sinks=mock_sinks,
                event_log=event_log,
                temp_paths=temp_paths,
                server_state=server_state,
                conversation_state=conversation_state,
                reset_response=reset_response,
                verification_checks=verification_checks,
                restart_count=restart_count,
                attempts=attempts,
                notes=notes,
            )
            mock_sink_after_path = self._write_snapshot(MOCK_SINK_AFTER_FILENAME, post_payload)
            postcheck_path = self._write_snapshot(RESET_POSTCHECK_FILENAME, post_payload)
            return ResetOutcome(
                status="QUARANTINED",
                attempts=attempts,
                restart_count=restart_count,
                quarantined=True,
                precheck_path=precheck_path,
                postcheck_path=postcheck_path,
                mock_sink_before_path=mock_sink_before_path,
                mock_sink_after_path=mock_sink_after_path,
                verification_checks=tuple(sorted(verification_checks.items())),
                reset_response=tuple(sorted(reset_response.items())),
                notes=tuple(notes),
            )

        raise SchemaInvariantError("reset controller failed without producing an outcome")
