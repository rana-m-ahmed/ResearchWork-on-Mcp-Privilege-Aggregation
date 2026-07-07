"""Transactional attempt lineage store."""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..domain.errors import DuplicateAcceptedAttemptError, SchemaInvariantError
from ..domain.invariants import AcceptedAttemptRecord, validate_single_accepted_attempt
from .schema import LINEAGE_COLUMNS
from ..evidence.io import atomic_append_snapshot_text


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaInvariantError(f"{field} must be a boolean")
    return value


def _require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise SchemaInvariantError(f"{field} must be a non-negative integer")
    return value


def _parse_int(value: Any, field: str) -> int:
    if isinstance(value, int):
        return _require_int(value, field)
    if isinstance(value, str) and value.strip().isdigit():
        return _require_int(int(value), field)
    raise SchemaInvariantError(f"{field} must be a non-negative integer")


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value in {"True", "False"}:
        return value == "True"
    raise SchemaInvariantError(f"{field} must be a boolean")


@dataclass(frozen=True, slots=True)
class AttemptLineageRecord:
    dataset_version: str
    frozen_row_id: str
    target_trial_id: str
    attempt_id: str
    attempt_index: int
    parent_attempt_id: str | None
    run_id: str
    batch_id: str
    attempt_status: str
    invalid_reason: str | None
    counts_toward_cell_n: bool
    accepted_attempt: bool
    raw_attempt_directory: Path

    def __post_init__(self) -> None:
        if self.attempt_index < 0:
            raise SchemaInvariantError("attempt_index must be non-negative")
        if not self.attempt_status.strip():
            raise SchemaInvariantError("attempt_status must be a non-empty string")

    def to_row(self) -> dict[str, Any]:
        return {
            "accepted_attempt": self.accepted_attempt,
            "attempt_id": self.attempt_id,
            "attempt_index": self.attempt_index,
            "attempt_status": self.attempt_status,
            "batch_id": self.batch_id,
            "counts_toward_cell_n": self.counts_toward_cell_n,
            "dataset_version": self.dataset_version,
            "frozen_row_id": self.frozen_row_id,
            "invalid_reason": self.invalid_reason,
            "parent_attempt_id": self.parent_attempt_id,
            "raw_attempt_directory": self.raw_attempt_directory.as_posix(),
            "run_id": self.run_id,
            "target_trial_id": self.target_trial_id,
        }

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> "AttemptLineageRecord":
        try:
            parent_attempt_id = row.get("parent_attempt_id") or None
            invalid_reason = row.get("invalid_reason") or None
            return cls(
                dataset_version=_require_string(row["dataset_version"], "dataset_version"),
                frozen_row_id=_require_string(row["frozen_row_id"], "frozen_row_id"),
                target_trial_id=_require_string(row["target_trial_id"], "target_trial_id"),
                attempt_id=_require_string(row["attempt_id"], "attempt_id"),
                attempt_index=_parse_int(row["attempt_index"], "attempt_index"),
                parent_attempt_id=parent_attempt_id,
                run_id=_require_string(row["run_id"], "run_id"),
                batch_id=_require_string(row["batch_id"], "batch_id"),
                attempt_status=_require_string(row["attempt_status"], "attempt_status"),
                invalid_reason=invalid_reason,
                counts_toward_cell_n=_parse_bool(row["counts_toward_cell_n"], "counts_toward_cell_n"),
                accepted_attempt=_parse_bool(row["accepted_attempt"], "accepted_attempt"),
                raw_attempt_directory=Path(_require_string(row["raw_attempt_directory"], "raw_attempt_directory")),
            )
        except KeyError as exc:
            raise SchemaInvariantError(f"missing lineage field: {exc.args[0]}") from exc

    def accepted_record(self) -> AcceptedAttemptRecord:
        from ..domain.identifiers import FrozenRowId

        return AcceptedAttemptRecord(target_frozen_row_id=FrozenRowId.parse(self.frozen_row_id), attempt_id=self.attempt_id, accepted_attempt=self.accepted_attempt)


def render_lineage_csv(records: Sequence[AttemptLineageRecord]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=list(LINEAGE_COLUMNS), lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow({column: record.to_row()[column] for column in LINEAGE_COLUMNS})
    return buffer.getvalue()


def parse_lineage_csv(path: Path) -> tuple[AttemptLineageRecord, ...]:
    if not path.exists():
        return ()
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise SchemaInvariantError(f"attempt lineage csv is not newline-terminated: {path.as_posix()}")
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if tuple(reader.fieldnames or ()) != LINEAGE_COLUMNS:
            raise SchemaInvariantError(f"attempt lineage csv header mismatch: {path.as_posix()}")
        return tuple(AttemptLineageRecord.from_row(row) for row in reader)


@dataclass(frozen=True, slots=True)
class AttemptLineageStore:
    path: Path

    def load_records(self) -> tuple[AttemptLineageRecord, ...]:
        return parse_lineage_csv(self.path)

    def append(self, record: AttemptLineageRecord) -> AttemptLineageRecord:
        existing = list(self.load_records())
        if any(item.attempt_id == record.attempt_id for item in existing):
            current = next(item for item in existing if item.attempt_id == record.attempt_id)
            if current == record:
                return record
            raise SchemaInvariantError(f"duplicate attempt_id detected with different lineage content: {record.attempt_id}")

        accepted = [item.accepted_record() for item in existing if item.accepted_attempt]
        accepted.append(record.accepted_record())
        validate_single_accepted_attempt(accepted)

        updated = tuple(existing + [record])
        self.write_snapshot(updated)
        return record

    def write_snapshot(
        self,
        records: Sequence[AttemptLineageRecord],
        *,
        before_replace_hook: Callable[[], None] | None = None,
    ) -> None:
        content = render_lineage_csv(records)
        atomic_append_snapshot_text(self.path, content, before_replace_hook=before_replace_hook)
