"""Per-attempt workspace metadata and manifest helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from ..domain.errors import SchemaInvariantError
from .io import atomic_write_text


DEFAULT_REQUIRED_ARTIFACTS = (
    "frozen_row_snapshot.json",
    "compiled_prompt.txt",
    "compiled_prompt_metadata.json",
    "model_outputs.jsonl",
    "parser_events.jsonl",
    "tool_transcript.jsonl",
    "mock_sink_snapshot_before.json",
    "mock_sink_snapshot_after.json",
    "reset_precheck.json",
    "reset_postcheck.json",
    "token_counts_per_turn.json",
    "hardware_snapshot.json",
    "grader_evidence.json",
    "attempt_manifest.json",
)


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _path_to_text(path: Path) -> str:
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class AttemptWorkspaceMetadata:
    dataset_version: str
    frozen_row_id: str
    target_trial_id: str
    attempt_id: str
    attempt_index: int
    parent_attempt_id: str | None
    run_id: str
    batch_id: str
    attempt_status: str
    raw_attempt_directory: Path
    event_log_path: Path
    lineage_path: Path
    manifest_path: Path
    artifact_index_path: Path
    created_utc: str
    required_artifacts: tuple[str, ...] = field(default=DEFAULT_REQUIRED_ARTIFACTS)

    def __post_init__(self) -> None:
        if self.attempt_index < 0:
            raise SchemaInvariantError("attempt_index must be non-negative")
        if not self.required_artifacts:
            raise SchemaInvariantError("required_artifacts cannot be empty")

    @classmethod
    def build(
        cls,
        *,
        base_attempts_root: Path,
        base_evidence_root: Path,
        dataset_version: str,
        frozen_row_id: str,
        target_trial_id: str,
        attempt_id: str,
        attempt_index: int,
        parent_attempt_id: str | None,
        run_id: str,
        batch_id: str,
        attempt_status: str,
        created_utc: str,
    ) -> "AttemptWorkspaceMetadata":
        raw_attempt_directory = base_evidence_root / "attempts" / attempt_id
        return cls(
            dataset_version=dataset_version,
            frozen_row_id=frozen_row_id,
            target_trial_id=target_trial_id,
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            parent_attempt_id=parent_attempt_id,
            run_id=run_id,
            batch_id=batch_id,
            attempt_status=attempt_status,
            raw_attempt_directory=raw_attempt_directory,
            event_log_path=raw_attempt_directory / "attempt_events.jsonl",
            lineage_path=base_attempts_root / "attempt_lineage.csv",
            manifest_path=raw_attempt_directory / "attempt_manifest.json",
            artifact_index_path=raw_attempt_directory / "evidence_hash_index.jsonl",
            created_utc=created_utc,
        )

    def required_artifact_paths(self) -> dict[str, str]:
        return {
            name: _path_to_text(self.raw_attempt_directory / name)
            for name in self.required_artifacts
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "attempt_index": self.attempt_index,
            "attempt_status": self.attempt_status,
            "artifact_index_path": _path_to_text(self.artifact_index_path),
            "batch_id": self.batch_id,
            "created_utc": self.created_utc,
            "dataset_version": self.dataset_version,
            "event_log_path": _path_to_text(self.event_log_path),
            "frozen_row_id": self.frozen_row_id,
            "lineage_path": _path_to_text(self.lineage_path),
            "manifest_path": _path_to_text(self.manifest_path),
            "parent_attempt_id": self.parent_attempt_id,
            "raw_attempt_directory": _path_to_text(self.raw_attempt_directory),
            "required_artifact_paths": self.required_artifact_paths(),
            "required_artifacts": list(self.required_artifacts),
            "run_id": self.run_id,
            "target_trial_id": self.target_trial_id,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "AttemptWorkspaceMetadata":
        try:
            required_artifacts = mapping.get("required_artifacts", DEFAULT_REQUIRED_ARTIFACTS)
            if not isinstance(required_artifacts, list) or not all(isinstance(item, str) and item for item in required_artifacts):
                raise SchemaInvariantError("required_artifacts must be a list of non-empty strings")
            parent_attempt_id = mapping.get("parent_attempt_id") or None
            return cls(
                dataset_version=_require_string(mapping["dataset_version"], "dataset_version"),
                frozen_row_id=_require_string(mapping["frozen_row_id"], "frozen_row_id"),
                target_trial_id=_require_string(mapping["target_trial_id"], "target_trial_id"),
                attempt_id=_require_string(mapping["attempt_id"], "attempt_id"),
                attempt_index=mapping["attempt_index"],
                parent_attempt_id=parent_attempt_id,
                run_id=_require_string(mapping["run_id"], "run_id"),
                batch_id=_require_string(mapping["batch_id"], "batch_id"),
                attempt_status=_require_string(mapping["attempt_status"], "attempt_status"),
                raw_attempt_directory=Path(_require_string(mapping["raw_attempt_directory"], "raw_attempt_directory")),
                event_log_path=Path(_require_string(mapping["event_log_path"], "event_log_path")),
                lineage_path=Path(_require_string(mapping["lineage_path"], "lineage_path")),
                manifest_path=Path(_require_string(mapping["manifest_path"], "manifest_path")),
                artifact_index_path=Path(_require_string(mapping["artifact_index_path"], "artifact_index_path")),
                created_utc=_require_string(mapping["created_utc"], "created_utc"),
                required_artifacts=tuple(required_artifacts),
            )
        except KeyError as exc:
            raise SchemaInvariantError(f"missing workspace field: {exc.args[0]}") from exc

    def write_manifest(self, *, before_replace_hook: Callable[[], None] | None = None) -> None:
        atomic_write_text(
            self.manifest_path,
            json.dumps(self.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
            before_replace_hook=before_replace_hook,
        )
