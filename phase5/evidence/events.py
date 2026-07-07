"""Write-ahead attempt events for Phase 5 evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from ..domain.errors import SchemaInvariantError
from ..domain.identifiers import EventId
from .io import append_jsonl_record, load_jsonl_records


class AttemptEventType(str, Enum):
    PREPARED = "PREPARED"
    DISPATCHED = "DISPATCHED"
    MODEL_OUTPUT_CAPTURED = "MODEL_OUTPUT_CAPTURED"
    PARSE_COMPLETED = "PARSE_COMPLETED"
    TOOL_EVENT = "TOOL_EVENT"
    TOOL_RESULT_CAPTURED = "TOOL_RESULT_CAPTURED"
    TURN_COMPLETED = "TURN_COMPLETED"
    TERMINATED = "TERMINATED"
    RESET_CHECKED = "RESET_CHECKED"
    GRADED = "GRADED"
    TRIAL_ROW_MATERIALIZED = "TRIAL_ROW_MATERIALIZED"
    FINALIZED = "FINALIZED"

    @classmethod
    def from_value(cls, value: str) -> "AttemptEventType":
        try:
            return cls(value)
        except ValueError as exc:  # pragma: no cover - exercised by negative tests
            raise SchemaInvariantError(f"unsupported attempt event type: {value!r}") from exc


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field)


@dataclass(frozen=True, slots=True)
class AttemptEvent:
    event_id: EventId
    dataset_version: str
    frozen_row_id: str
    target_trial_id: str
    attempt_id: str
    run_id: str
    batch_id: str
    event_sequence: int
    event_type: AttemptEventType
    timestamp_utc: str
    artifact_ref: str | None
    artifact_sha256: str | None
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.event_sequence < 1:
            raise SchemaInvariantError("event_sequence must be positive")
        if (self.artifact_ref is None) != (self.artifact_sha256 is None):
            raise SchemaInvariantError("artifact_ref and artifact_sha256 must either both be null or both be populated")
        if not isinstance(self.details, Mapping):
            raise SchemaInvariantError("details must be a mapping")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "artifact_ref": self.artifact_ref,
            "artifact_sha256": self.artifact_sha256,
            "attempt_id": self.attempt_id,
            "batch_id": self.batch_id,
            "dataset_version": self.dataset_version,
            "details": dict(self.details),
            "event_id": str(self.event_id),
            "event_sequence": self.event_sequence,
            "event_type": self.event_type.value,
            "frozen_row_id": self.frozen_row_id,
            "run_id": self.run_id,
            "target_trial_id": self.target_trial_id,
            "timestamp_utc": self.timestamp_utc,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "AttemptEvent":
        try:
            event_id = EventId.parse(_require_string(mapping["event_id"], "event_id"))
            event_type = AttemptEventType.from_value(_require_string(mapping["event_type"], "event_type"))
            details = mapping.get("details", {})
            if not isinstance(details, Mapping):
                raise SchemaInvariantError("details must be a mapping")
            event_sequence = mapping["event_sequence"]
            if not isinstance(event_sequence, int):
                raise SchemaInvariantError("event_sequence must be an integer")
            return cls(
                event_id=event_id,
                dataset_version=_require_string(mapping["dataset_version"], "dataset_version"),
                frozen_row_id=_require_string(mapping["frozen_row_id"], "frozen_row_id"),
                target_trial_id=_require_string(mapping["target_trial_id"], "target_trial_id"),
                attempt_id=_require_string(mapping["attempt_id"], "attempt_id"),
                run_id=_require_string(mapping["run_id"], "run_id"),
                batch_id=_require_string(mapping["batch_id"], "batch_id"),
                event_sequence=event_sequence,
                event_type=event_type,
                timestamp_utc=_require_string(mapping["timestamp_utc"], "timestamp_utc"),
                artifact_ref=_require_optional_string(mapping.get("artifact_ref"), "artifact_ref"),
                artifact_sha256=_require_optional_string(mapping.get("artifact_sha256"), "artifact_sha256"),
                details=details,
            )
        except KeyError as exc:
            raise SchemaInvariantError(f"missing event field: {exc.args[0]}") from exc


def load_attempt_events(path: Path) -> tuple[AttemptEvent, ...]:
    return tuple(AttemptEvent.from_mapping(item) for item in load_jsonl_records(path))


class AttemptEventLogWriter:
    """Append-only event log writer with immediate flush and fsync."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, event: AttemptEvent) -> AttemptEvent:
        existing = list(load_attempt_events(self.path))
        if existing:
            if existing[-1].event_type is AttemptEventType.FINALIZED:
                raise SchemaInvariantError("finalized attempt logs cannot accept additional events")
            if existing[-1].to_mapping() == event.to_mapping():
                return event
            if any(item.event_id == event.event_id for item in existing):
                raise SchemaInvariantError(f"duplicate attempt event id detected: {event.event_id}")
            if event.event_sequence != existing[-1].event_sequence + 1:
                raise SchemaInvariantError("attempt event sequence must be contiguous")
        else:
            if event.event_sequence != 1:
                raise SchemaInvariantError("first attempt event must use event_sequence=1")

        append_jsonl_record(self.path, event.to_mapping())
        return event
