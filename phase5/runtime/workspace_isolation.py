"""Per-attempt workspace isolation helpers for the Phase 5 runtime."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, MutableSequence, Sequence

from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError
from ..evidence.io import atomic_write_bytes, atomic_write_text
from ..evidence.workspace import AttemptWorkspaceMetadata


def _resolved(path: Path) -> Path:
    return path.resolve(strict=False)


def _is_within(path: Path, root: Path) -> bool:
    try:
        _resolved(path).relative_to(_resolved(root))
    except ValueError:
        return False
    return True


def _require_relative(path: Path, label: str) -> None:
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise SchemaInvariantError(f"{label} must stay within the attempt workspace")


def _clear_path(path: Path, root: Path) -> None:
    if not _is_within(path, root):
        raise SchemaInvariantError(f"attempt workspace path escapes the approved root: {path.as_posix()}")
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink(missing_ok=True)


@dataclass(frozen=True, slots=True)
class AttemptWorkspaceIsolation:
    """Materialized per-attempt workspace and write policy."""

    metadata: AttemptWorkspaceMetadata
    read_only_fixture_root: Path
    approved_mock_root: Path
    approved_evidence_root: Path

    @property
    def workspace_root(self) -> Path:
        return self.metadata.raw_attempt_directory

    @classmethod
    def build(
        cls,
        metadata: AttemptWorkspaceMetadata,
        *,
        read_only_fixture_root: Path,
        approved_mock_root: Path | None = None,
        approved_evidence_root: Path | None = None,
    ) -> "AttemptWorkspaceIsolation":
        workspace_root = metadata.raw_attempt_directory
        mock_root = approved_mock_root or workspace_root / "mock"
        evidence_root = approved_evidence_root or workspace_root
        for root in (workspace_root, mock_root, evidence_root):
            root.mkdir(parents=True, exist_ok=True)
        return cls(
            metadata=metadata,
            read_only_fixture_root=read_only_fixture_root,
            approved_mock_root=mock_root,
            approved_evidence_root=evidence_root,
        )

    def assert_write_allowed(self, target: Path) -> None:
        if not any(
            _is_within(target, root)
            for root in (self.workspace_root, self.approved_mock_root, self.approved_evidence_root)
        ):
            raise SchemaInvariantError(
                f"write target escapes the approved workspace roots: {target.as_posix()}"
            )

    def assert_fixture_source_allowed(self, source: Path) -> None:
        if not _is_within(source, self.read_only_fixture_root):
            raise MissingFrozenSettingError(
                f"read-only fixture source escapes the frozen fixture root: {source.as_posix()}"
            )

    def materialize(self) -> None:
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.approved_mock_root.mkdir(parents=True, exist_ok=True)
        self.approved_evidence_root.mkdir(parents=True, exist_ok=True)

    def copy_read_only_fixture(self, source_relative: str | Path, destination_relative: str | Path) -> Path:
        source_rel = Path(source_relative)
        destination_rel = Path(destination_relative)
        _require_relative(source_rel, "source_relative")
        _require_relative(destination_rel, "destination_relative")

        source = self.read_only_fixture_root / source_rel
        if not source.is_file():
            raise MissingFrozenSettingError(f"missing frozen fixture: {source.as_posix()}")
        self.assert_fixture_source_allowed(source)

        destination = self.workspace_root / destination_rel
        self.assert_write_allowed(destination)
        atomic_write_bytes(destination, source.read_bytes())
        return destination

    def write_json_snapshot(self, relative_path: str | Path, payload: Mapping[str, Any]) -> Path:
        relative = Path(relative_path)
        _require_relative(relative, "relative_path")
        destination = self.workspace_root / relative
        self.assert_write_allowed(destination)
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        atomic_write_text(destination, text)
        return destination

    def write_text_snapshot(self, relative_path: str | Path, text: str) -> Path:
        relative = Path(relative_path)
        _require_relative(relative, "relative_path")
        destination = self.workspace_root / relative
        self.assert_write_allowed(destination)
        atomic_write_text(destination, text)
        return destination

    def remove_path(self, path: Path) -> None:
        self.assert_write_allowed(path)
        _clear_path(path, self.workspace_root)

    def clear_temp_paths(self, temp_paths: tuple[Path, ...] | list[Path] | None) -> None:
        if not temp_paths:
            return
        for path in temp_paths:
            self.remove_path(path)

    def capture_state_snapshot(
        self,
        *,
        mock_sinks: Mapping[str, Any] | None = None,
        event_log: Sequence[Any] | None = None,
        temp_paths: Sequence[Path] | None = None,
        server_state: Mapping[str, Any] | None = None,
        conversation_state: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "approved_evidence_root": self.approved_evidence_root.as_posix(),
            "approved_mock_root": self.approved_mock_root.as_posix(),
            "conversation_state": dict(conversation_state or {}),
            "event_log": list(event_log or []),
            "mock_sinks": dict(mock_sinks or {}),
            "temp_paths": [path.as_posix() for path in (temp_paths or ())],
            "workspace_root": self.workspace_root.as_posix(),
            "server_state": dict(server_state or {}),
        }


def build_attempt_workspace_isolation(
    metadata: AttemptWorkspaceMetadata,
    *,
    read_only_fixture_root: Path,
    approved_mock_root: Path | None = None,
    approved_evidence_root: Path | None = None,
) -> AttemptWorkspaceIsolation:
    return AttemptWorkspaceIsolation.build(
        metadata,
        read_only_fixture_root=read_only_fixture_root,
        approved_mock_root=approved_mock_root,
        approved_evidence_root=approved_evidence_root,
    )
