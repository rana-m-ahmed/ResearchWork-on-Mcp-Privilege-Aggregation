"""Checkpoint schema and validation for Phase 5 finalization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError, SyncSafetyError


CHECKPOINT_SCHEMA_PATH = Path(__file__).resolve().parent / "schemas" / "checkpoint.schema.json"
FINALIZATION_STATUS_FINALIZED_NOT_SYNCED = "FINALIZED_NOT_SYNCED"
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


def load_checkpoint_schema() -> dict[str, Any]:
    if not CHECKPOINT_SCHEMA_PATH.is_file():
        raise MissingFrozenSettingError(
            f"checkpoint schema is missing: {CHECKPOINT_SCHEMA_PATH.as_posix()}"
        )
    data = json.loads(CHECKPOINT_SCHEMA_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError("checkpoint schema must be a JSON object")
    return data


def _require_keys(mapping: Mapping[str, Any], required: tuple[str, ...]) -> None:
    missing = [field for field in required if field not in mapping]
    extra = [field for field in mapping if field not in required]
    if missing or extra:
        details: list[str] = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise MissingFrozenSettingError(f"checkpoint record field mismatch: {'; '.join(details)}")


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    dataset_version: str
    model_slot: str
    workload: str
    run_id: str
    batch_id: str
    source_commit: str
    phase4_lock_hash: str
    phase45_go_hash: str
    expected_remote_head_before_push: str
    accepted_finalized_count: int
    invalid_attempt_count: int
    orphan_attempt_count: int
    batch_manifest_sha256: str
    evidence_index_sha256: str
    session_seal_closed: bool
    seal_epoch: int
    sync_barrier_status: str
    continuation_authorized_after_reverify: bool
    no_more_official_execution_in_session: bool
    finalization_status: str = FINALIZATION_STATUS_FINALIZED_NOT_SYNCED

    def __post_init__(self) -> None:
        if self.seal_epoch < 0:
            raise SchemaInvariantError("seal_epoch must be non-negative")
        if self.finalization_status != FINALIZATION_STATUS_FINALIZED_NOT_SYNCED:
            raise SchemaInvariantError(
                f"finalization_status must be {FINALIZATION_STATUS_FINALIZED_NOT_SYNCED!r}"
            )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_finalized_count": self.accepted_finalized_count,
            "batch_id": self.batch_id,
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "continuation_authorized_after_reverify": self.continuation_authorized_after_reverify,
            "dataset_version": self.dataset_version,
            "evidence_index_sha256": self.evidence_index_sha256,
            "expected_remote_head_before_push": self.expected_remote_head_before_push,
            "finalization_status": self.finalization_status,
            "invalid_attempt_count": self.invalid_attempt_count,
            "model_slot": self.model_slot,
            "no_more_official_execution_in_session": self.no_more_official_execution_in_session,
            "orphan_attempt_count": self.orphan_attempt_count,
            "phase45_go_hash": self.phase45_go_hash,
            "phase4_lock_hash": self.phase4_lock_hash,
            "run_id": self.run_id,
            "seal_epoch": self.seal_epoch,
            "session_seal_closed": self.session_seal_closed,
            "source_commit": self.source_commit,
            "sync_barrier_status": self.sync_barrier_status,
            "workload": self.workload,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "CheckpointRecord":
        required = (
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
            "seal_epoch",
            "sync_barrier_status",
            "continuation_authorized_after_reverify",
            "no_more_official_execution_in_session",
            "finalization_status",
        )
        _require_keys(mapping, required)
        return cls(
            dataset_version=_require_string(mapping["dataset_version"], "dataset_version"),
            model_slot=_require_string(mapping["model_slot"], "model_slot"),
            workload=_require_string(mapping["workload"], "workload"),
            run_id=_require_string(mapping["run_id"], "run_id"),
            batch_id=_require_string(mapping["batch_id"], "batch_id"),
            source_commit=_require_string(mapping["source_commit"], "source_commit"),
            phase4_lock_hash=_require_string(mapping["phase4_lock_hash"], "phase4_lock_hash"),
            phase45_go_hash=_require_string(mapping["phase45_go_hash"], "phase45_go_hash"),
            expected_remote_head_before_push=_require_string(
                mapping["expected_remote_head_before_push"], "expected_remote_head_before_push"
            ),
            accepted_finalized_count=_require_int(mapping["accepted_finalized_count"], "accepted_finalized_count"),
            invalid_attempt_count=_require_int(mapping["invalid_attempt_count"], "invalid_attempt_count"),
            orphan_attempt_count=_require_int(mapping["orphan_attempt_count"], "orphan_attempt_count"),
            batch_manifest_sha256=_require_string(mapping["batch_manifest_sha256"], "batch_manifest_sha256"),
            evidence_index_sha256=_require_string(mapping["evidence_index_sha256"], "evidence_index_sha256"),
            session_seal_closed=_require_bool(mapping["session_seal_closed"], "session_seal_closed"),
            seal_epoch=_require_int(mapping["seal_epoch"], "seal_epoch"),
            sync_barrier_status=_require_string(mapping["sync_barrier_status"], "sync_barrier_status"),
            continuation_authorized_after_reverify=_require_bool(
                mapping["continuation_authorized_after_reverify"], "continuation_authorized_after_reverify"
            ),
            no_more_official_execution_in_session=_require_bool(
                mapping["no_more_official_execution_in_session"], "no_more_official_execution_in_session"
            ),
            finalization_status=_require_string(mapping["finalization_status"], "finalization_status"),
        )

    def requires_reverification_before_continuation(self) -> None:
        if not self.continuation_authorized_after_reverify:
            raise SyncSafetyError("continuation is forbidden before re-verification")


def validate_checkpoint_record(mapping: Mapping[str, Any]) -> list[str]:
    try:
        CheckpointRecord.from_mapping(mapping)
    except Exception as exc:  # pragma: no cover - deterministic error mapping tested elsewhere
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def validate_continuation_authorization(record: CheckpointRecord) -> None:
    record.requires_reverification_before_continuation()


def build_checkpoint_record(
    *,
    dataset_version: str,
    model_slot: str,
    workload: str,
    run_id: str,
    batch_id: str,
    source_commit: str,
    phase4_lock_hash: str,
    phase45_go_hash: str,
    expected_remote_head_before_push: str,
    accepted_finalized_count: int,
    invalid_attempt_count: int,
    orphan_attempt_count: int,
    batch_manifest_sha256: str,
    evidence_index_sha256: str,
    session_seal_closed: bool,
    seal_epoch: int,
    sync_barrier_status: str,
    continuation_authorized_after_reverify: bool,
    no_more_official_execution_in_session: bool,
    finalization_status: str = FINALIZATION_STATUS_FINALIZED_NOT_SYNCED,
) -> CheckpointRecord:
    record = CheckpointRecord(
        dataset_version=dataset_version,
        model_slot=model_slot,
        workload=workload,
        run_id=run_id,
        batch_id=batch_id,
        source_commit=source_commit,
        phase4_lock_hash=phase4_lock_hash,
        phase45_go_hash=phase45_go_hash,
        expected_remote_head_before_push=expected_remote_head_before_push,
        accepted_finalized_count=accepted_finalized_count,
        invalid_attempt_count=invalid_attempt_count,
        orphan_attempt_count=orphan_attempt_count,
        batch_manifest_sha256=batch_manifest_sha256,
        evidence_index_sha256=evidence_index_sha256,
        session_seal_closed=session_seal_closed,
        seal_epoch=seal_epoch,
        sync_barrier_status=sync_barrier_status,
        continuation_authorized_after_reverify=continuation_authorized_after_reverify,
        no_more_official_execution_in_session=no_more_official_execution_in_session,
        finalization_status=finalization_status,
    )
    return record
