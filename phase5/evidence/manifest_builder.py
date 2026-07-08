"""Hash-bound finalization manifests for Phase 5 batches and runs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..checkpoints import (
    CheckpointRecord,
    FINALIZATION_STATUS_FINALIZED_NOT_SYNCED,
    build_checkpoint_record,
)
from ..domain.errors import DuplicateAcceptedAttemptError, MissingFrozenSettingError, SchemaInvariantError
from .archive_index import ArchiveIndex, ArchiveIndexEntry, build_archive_index
from .io import atomic_write_text
from .trial_materializer import EvidenceReference, verify_evidence_references


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise SchemaInvariantError(f"{field} must be a non-negative integer")
    return value


def _sorted_attempt_ids(records: Sequence[AttemptLineageRecord]) -> tuple[str, ...]:
    return tuple(record.attempt_id for record in sorted(records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))


def _sorted_frozen_row_ids(records: Sequence[AttemptLineageRecord]) -> tuple[str, ...]:
    return tuple(record.frozen_row_id for record in sorted(records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))


def _sorted_target_trial_ids(records: Sequence[AttemptLineageRecord]) -> tuple[str, ...]:
    return tuple(record.target_trial_id for record in sorted(records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))


def _validate_attempt_record(record: AttemptLineageRecord) -> None:
    if not record.attempt_id.strip():
        raise SchemaInvariantError("attempt_id must be non-empty")
    if not record.frozen_row_id.strip():
        raise SchemaInvariantError("frozen_row_id must be non-empty")
    if not record.target_trial_id.strip():
        raise SchemaInvariantError("target_trial_id must be non-empty")


def _validate_unique_accepted_targets(records: Sequence[AttemptLineageRecord]) -> None:
    seen_frozen_row_ids: set[str] = set()
    seen_target_trial_ids: set[str] = set()
    for record in records:
        if not record.accepted_attempt:
            continue
        if record.frozen_row_id in seen_frozen_row_ids or record.target_trial_id in seen_target_trial_ids:
            raise DuplicateAcceptedAttemptError(
                f"more than one accepted attempt was recorded for target frozen row {record.frozen_row_id!r}"
            )
        seen_frozen_row_ids.add(record.frozen_row_id)
        seen_target_trial_ids.add(record.target_trial_id)


def _validate_cell_reconciliation(
    *,
    accepted_records: Sequence[AttemptLineageRecord],
    invalid_records: Sequence[AttemptLineageRecord],
    orphan_records: Sequence[AttemptLineageRecord],
    incomplete_records: Sequence[AttemptLineageRecord],
) -> None:
    total_records = len(accepted_records) + len(invalid_records) + len(orphan_records) + len(incomplete_records)
    if total_records == 0:
        raise MissingFrozenSettingError("finalization requires at least one attempt record")
    if incomplete_records:
        raise SchemaInvariantError("incomplete attempt records cannot be finalized")
    accepted_frozen_row_ids = {record.frozen_row_id for record in accepted_records}
    if len(accepted_frozen_row_ids) != len(accepted_records):
        raise DuplicateAcceptedAttemptError("accepted frozen row ids must be unique")


def _compact_accepted_row(record: AttemptLineageRecord) -> dict[str, Any]:
    if not record.accepted_attempt:
        raise SchemaInvariantError("compact accepted rows require accepted attempts")
    return {
        "accepted_attempt": True,
        "attempt_id": record.attempt_id,
        "attempt_index": record.attempt_index,
        "batch_id": record.batch_id,
        "counts_toward_cell_n": record.counts_toward_cell_n,
        "dataset_version": record.dataset_version,
        "frozen_row_id": record.frozen_row_id,
        "run_id": record.run_id,
        "target_trial_id": record.target_trial_id,
    }


def build_accepted_row_jsonl(records: Sequence[AttemptLineageRecord]) -> tuple[str, str]:
    accepted_records = tuple(
        sorted(
            (record for record in records if record.accepted_attempt),
            key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id),
        )
    )
    _validate_unique_accepted_targets(accepted_records)
    lines = [json.dumps(_compact_accepted_row(record), sort_keys=True, separators=(",", ":")) for record in accepted_records]
    text = "\n".join(lines) + ("\n" if lines else "")
    return text, _sha256_bytes(text.encode("utf-8"))


@dataclass(frozen=True, slots=True)
class AttemptFinalizationRecord:
    lineage: AttemptLineageRecord
    evidence_references: tuple[EvidenceReference, ...] = ()
    category: str = "INVALID"
    archive_uri: str | None = None
    archive_size_bytes: int | None = None
    archive_sha256: str | None = None
    archive_retrieval_status: str | None = None

    def __post_init__(self) -> None:
        if self.category not in {"ACCEPTED", "INVALID", "ORPHAN", "INCOMPLETE"}:
            raise SchemaInvariantError(f"unsupported finalization category: {self.category!r}")

    @property
    def is_incomplete(self) -> bool:
        return self.category == "INCOMPLETE"

    @property
    def is_accepted(self) -> bool:
        return self.category == "ACCEPTED"

    @property
    def is_orphan(self) -> bool:
        return self.category == "ORPHAN"

    @property
    def is_invalid(self) -> bool:
        return self.category == "INVALID"

    def archive_entry(self) -> ArchiveIndexEntry | None:
        if self.archive_uri is None and self.archive_sha256 is None and self.archive_size_bytes is None:
            return None
        if self.archive_uri is None or self.archive_sha256 is None or self.archive_size_bytes is None:
            raise MissingFrozenSettingError("archive index entries require uri, size_bytes, and sha256")
        return ArchiveIndexEntry(
            uri=_require_string(self.archive_uri, "archive_uri"),
            size_bytes=_require_int(self.archive_size_bytes, "archive_size_bytes"),
            sha256=_require_string(self.archive_sha256, "archive_sha256"),
            included_attempt_ids=(self.lineage.attempt_id,),
            retrieval_status=_require_string(self.archive_retrieval_status or "AVAILABLE", "archive_retrieval_status"),
        )


@dataclass(frozen=True, slots=True)
class BatchManifest:
    task_id: str
    status: str
    generated_utc: str
    dataset_version: str
    run_id: str
    batch_id: str
    model_slot: str
    workload: str
    source_commit: str
    phase4_lock_hash: str
    phase45_go_hash: str
    model_runtime_hash: str
    schema_grader_tid_hash: str
    archive_hash: str
    count_hash: str
    accepted_attempt_mapping: tuple[tuple[str, str], ...]
    invalid_attempt_mapping: tuple[tuple[str, str], ...]
    orphan_attempt_mapping: tuple[tuple[str, str], ...]
    frozen_row_ids: tuple[str, ...]
    target_trial_ids: tuple[str, ...]
    attempt_ids: tuple[str, ...]
    accepted_finalized_count: int
    invalid_attempt_count: int
    orphan_attempt_count: int
    incomplete_attempt_count: int
    trial_jsonl_sha256: str
    event_log_sha256: str
    raw_evidence_archive_sha256: str
    schema_validation_report_sha256: str
    archive_index_sha256: str
    finalization_status: str
    manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted_attempt_mapping": [
                {"frozen_row_id": frozen_row_id, "attempt_id": attempt_id}
                for frozen_row_id, attempt_id in self.accepted_attempt_mapping
            ],
            "accepted_finalized_count": self.accepted_finalized_count,
            "archive_hash": self.archive_hash,
            "archive_index_sha256": self.archive_index_sha256,
            "attempt_ids": list(self.attempt_ids),
            "batch_id": self.batch_id,
            "count_hash": self.count_hash,
            "dataset_version": self.dataset_version,
            "event_log_sha256": self.event_log_sha256,
            "finalization_status": self.finalization_status,
            "frozen_row_ids": list(self.frozen_row_ids),
            "generated_utc": self.generated_utc,
            "incomplete_attempt_count": self.incomplete_attempt_count,
            "invalid_attempt_count": self.invalid_attempt_count,
            "invalid_attempt_mapping": [
                {"frozen_row_id": frozen_row_id, "attempt_id": attempt_id}
                for frozen_row_id, attempt_id in self.invalid_attempt_mapping
            ],
            "manifest_sha256": self.manifest_sha256,
            "model_runtime_hash": self.model_runtime_hash,
            "model_slot": self.model_slot,
            "orphan_attempt_count": self.orphan_attempt_count,
            "orphan_attempt_mapping": [
                {"frozen_row_id": frozen_row_id, "attempt_id": attempt_id}
                for frozen_row_id, attempt_id in self.orphan_attempt_mapping
            ],
            "phase45_go_hash": self.phase45_go_hash,
            "phase4_lock_hash": self.phase4_lock_hash,
            "raw_evidence_archive_sha256": self.raw_evidence_archive_sha256,
            "run_id": self.run_id,
            "schema_grader_tid_hash": self.schema_grader_tid_hash,
            "schema_validation_report_sha256": self.schema_validation_report_sha256,
            "source_commit": self.source_commit,
            "status": self.status,
            "target_trial_ids": list(self.target_trial_ids),
            "task_id": self.task_id,
            "trial_jsonl_sha256": self.trial_jsonl_sha256,
            "workload": self.workload,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P12 Batch Hash-Bound Integrity Manifest",
            "",
            "## Verdict",
            "",
            f"- Task: `{self.task_id}`",
            f"- Status: `{self.status}`",
            f"- Finalization status: `{self.finalization_status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- Run ID: `{self.run_id}`",
            f"- Batch ID: `{self.batch_id}`",
            f"- Model slot: `{self.model_slot}`",
            f"- Workload: `{self.workload}`",
            "",
            "## Counts",
            "",
            f"- Accepted finalized count: `{self.accepted_finalized_count}`",
            f"- Invalid attempt count: `{self.invalid_attempt_count}`",
            f"- Orphan attempt count: `{self.orphan_attempt_count}`",
            f"- Incomplete attempt count: `{self.incomplete_attempt_count}`",
            "",
            "## Hashes",
            "",
            f"- Source commit: `{self.source_commit}`",
            f"- Phase 4 lock hash: `{self.phase4_lock_hash}`",
            f"- Phase 4.5 GO hash: `{self.phase45_go_hash}`",
            f"- Model/runtime hash: `{self.model_runtime_hash}`",
            f"- Schema/grader/TID hash: `{self.schema_grader_tid_hash}`",
            f"- Archive hash: `{self.archive_hash}`",
            f"- Count hash: `{self.count_hash}`",
            f"- Trial JSONL hash: `{self.trial_jsonl_sha256}`",
            f"- Event log hash: `{self.event_log_sha256}`",
            f"- Raw evidence archive hash: `{self.raw_evidence_archive_sha256}`",
            f"- Schema validation report hash: `{self.schema_validation_report_sha256}`",
            f"- Archive index hash: `{self.archive_index_sha256}`",
            f"- Manifest hash: `{self.manifest_sha256}`",
        ]
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        atomic_write_text(json_path, self.to_json() + "\n")
        if markdown_path is not None:
            atomic_write_text(markdown_path, self.to_markdown())


@dataclass(frozen=True, slots=True)
class RunManifest:
    task_id: str
    status: str
    generated_utc: str
    dataset_version: str
    run_id: str
    source_commit: str
    phase4_lock_hash: str
    phase45_go_hash: str
    model_slot: str
    model_runtime_hash: str
    schema_grader_tid_hash: str
    model_identity: str
    tokenizer_identity: str
    backend_identity: str
    accelerator_identity: str
    device_map_identity: str
    dependency_lock_hash: str
    seal_epoch: int
    official_seal_timestamp: str
    sync_barrier_status: str
    continuation_authorized_after_reverify: bool
    no_more_official_execution_in_session: bool
    batch_ids: tuple[str, ...]
    counts_hash: str
    artifact_hashes: dict[str, str]
    checkpoint_archive_sha256: str
    finalization_status: str
    manifest_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "accelerator_identity": self.accelerator_identity,
            "artifact_hashes": dict(sorted(self.artifact_hashes.items())),
            "batch_ids": list(self.batch_ids),
            "checkpoint_archive_sha256": self.checkpoint_archive_sha256,
            "continuation_authorized_after_reverify": self.continuation_authorized_after_reverify,
            "counts_hash": self.counts_hash,
            "dataset_version": self.dataset_version,
            "device_map_identity": self.device_map_identity,
            "dependency_lock_hash": self.dependency_lock_hash,
            "finalization_status": self.finalization_status,
            "generated_utc": self.generated_utc,
            "manifest_sha256": self.manifest_sha256,
            "model_identity": self.model_identity,
            "model_slot": self.model_slot,
            "model_runtime_hash": self.model_runtime_hash,
            "no_more_official_execution_in_session": self.no_more_official_execution_in_session,
            "official_seal_timestamp": self.official_seal_timestamp,
            "phase45_go_hash": self.phase45_go_hash,
            "phase4_lock_hash": self.phase4_lock_hash,
            "schema_grader_tid_hash": self.schema_grader_tid_hash,
            "run_id": self.run_id,
            "seal_epoch": self.seal_epoch,
            "source_commit": self.source_commit,
            "status": self.status,
            "sync_barrier_status": self.sync_barrier_status,
            "task_id": self.task_id,
            "tokenizer_identity": self.tokenizer_identity,
            "backend_identity": self.backend_identity,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P12 Run Hash-Bound Integrity Manifest",
            "",
            "## Verdict",
            "",
            f"- Task: `{self.task_id}`",
            f"- Status: `{self.status}`",
            f"- Finalization status: `{self.finalization_status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- Run ID: `{self.run_id}`",
            f"- Model slot: `{self.model_slot}`",
            "",
            "## Runtime Identity",
            "",
            f"- Model identity: `{self.model_identity}`",
            f"- Tokenizer identity: `{self.tokenizer_identity}`",
            f"- Backend identity: `{self.backend_identity}`",
            f"- Accelerator identity: `{self.accelerator_identity}`",
            f"- Device map identity: `{self.device_map_identity}`",
            f"- Dependency lock hash: `{self.dependency_lock_hash}`",
            f"- Model/runtime hash: `{self.model_runtime_hash}`",
            f"- Schema/grader/TID hash: `{self.schema_grader_tid_hash}`",
            "",
            "## Session",
            "",
            f"- Seal epoch: `{self.seal_epoch}`",
            f"- Official seal timestamp: `{self.official_seal_timestamp}`",
            f"- Sync barrier status: `{self.sync_barrier_status}`",
            f"- Continuation authorized after reverify: `{self.continuation_authorized_after_reverify}`",
            f"- No more official execution in session: `{self.no_more_official_execution_in_session}`",
            "",
            "## Hashes",
            "",
            f"- Source commit: `{self.source_commit}`",
            f"- Phase 4 lock hash: `{self.phase4_lock_hash}`",
            f"- Phase 4.5 GO hash: `{self.phase45_go_hash}`",
            f"- Counts hash: `{self.counts_hash}`",
            f"- Checkpoint archive hash: `{self.checkpoint_archive_sha256}`",
            f"- Manifest hash: `{self.manifest_sha256}`",
        ]
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        atomic_write_text(json_path, self.to_json() + "\n")
        if markdown_path is not None:
            atomic_write_text(markdown_path, self.to_markdown())


@dataclass(frozen=True, slots=True)
class BatchFinalizationInput:
    dataset_version: str
    run_id: str
    batch_id: str
    model_slot: str
    workload: str
    source_commit: str
    phase4_lock_hash: str
    phase45_go_hash: str
    model_runtime_hash: str
    schema_grader_tid_hash: str
    dependency_lock_hash: str
    model_identity: str
    tokenizer_identity: str
    backend_identity: str
    accelerator_identity: str
    device_map_identity: str
    official_seal_timestamp: str
    seal_epoch: int
    sync_barrier_status: str
    continuation_authorized_after_reverify: bool
    no_more_official_execution_in_session: bool
    expected_remote_head_before_push: str
    trial_jsonl_sha256: str
    event_log_sha256: str
    raw_evidence_archive_sha256: str
    schema_validation_report_sha256: str
    finalization_status: str = FINALIZATION_STATUS_FINALIZED_NOT_SYNCED


@dataclass(frozen=True, slots=True)
class FinalizationBundle:
    accepted_rows_jsonl: str
    archive_index: ArchiveIndex
    batch_manifest: BatchManifest
    run_manifest: RunManifest
    checkpoint_record: CheckpointRecord

    def write(self, output_root: Path, *, before_rename_hook: Callable[[], None] | None = None) -> Path:
        if output_root.exists():
            raise SchemaInvariantError(f"finalization output already exists: {output_root.as_posix()}")
        output_root.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=f".{output_root.name}.") as temp_dir:
            stage_root = Path(temp_dir)
            atomic_write_text(stage_root / "accepted_rows.jsonl", self.accepted_rows_jsonl)
            self.archive_index.write(stage_root / "archive_index.json", stage_root / "archive_index.md")
            self.batch_manifest.write(stage_root / "batch_manifest.json", stage_root / "batch_manifest.md")
            self.run_manifest.write(stage_root / "run_manifest.json", stage_root / "run_manifest.md")
            atomic_write_text(
                stage_root / "checkpoint.json",
                json.dumps(self.checkpoint_record.to_mapping(), sort_keys=True, separators=(",", ":")) + "\n",
            )
            if before_rename_hook is not None:
                before_rename_hook()
            os.replace(stage_root, output_root)
        return output_root


def _validate_finalization_records(
    records: Sequence[AttemptFinalizationRecord],
    *,
    evidence_root: Path,
) -> None:
    for record in records:
        _validate_attempt_record(record.lineage)
        if record.category == "ACCEPTED" and not record.lineage.accepted_attempt:
            raise SchemaInvariantError("accepted finalization records must map to accepted lineage rows")
        if record.category != "ACCEPTED" and record.lineage.accepted_attempt:
            raise SchemaInvariantError("non-accepted records cannot carry accepted lineage rows")
        if record.category == "ORPHAN" and record.archive_entry() is None:
            raise MissingFrozenSettingError("unresolved orphan requires archive metadata")
        if record.evidence_references:
            verify_evidence_references(record.evidence_references, evidence_root=evidence_root)


def build_finalization_bundle(
    input_data: BatchFinalizationInput,
    records: Sequence[AttemptFinalizationRecord],
    *,
    generated_utc: str,
    evidence_root: Path,
) -> FinalizationBundle:
    accepted_records = tuple(record.lineage for record in records if record.category == "ACCEPTED")
    invalid_records = tuple(record.lineage for record in records if record.category == "INVALID")
    orphan_records = tuple(record.lineage for record in records if record.category == "ORPHAN")
    incomplete_records = tuple(record.lineage for record in records if record.category == "INCOMPLETE")
    accepted_records = tuple(sorted(accepted_records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))
    invalid_records = tuple(sorted(invalid_records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))
    orphan_records = tuple(sorted(orphan_records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))
    incomplete_records = tuple(sorted(incomplete_records, key=lambda record: (record.frozen_row_id, record.target_trial_id, record.attempt_id)))
    _validate_cell_reconciliation(
        accepted_records=accepted_records,
        invalid_records=invalid_records,
        orphan_records=orphan_records,
        incomplete_records=incomplete_records,
    )
    _validate_unique_accepted_targets(accepted_records)
    _validate_finalization_records(records, evidence_root=evidence_root)

    accepted_rows_jsonl, accepted_rows_sha256 = build_accepted_row_jsonl(accepted_records)
    archive_entries = [record.archive_entry() for record in records if record.archive_entry() is not None]
    archive_index = build_archive_index(archive_entries, generated_utc=generated_utc)

    counts = {
        "accepted_finalized_count": len(accepted_records),
        "attempt_count": len(records),
        "incomplete_attempt_count": len(incomplete_records),
        "invalid_attempt_count": len(invalid_records),
        "orphan_attempt_count": len(orphan_records),
    }
    count_hash = _sha256_bytes(_canonical_json(counts).encode("utf-8"))
    accepted_attempt_mapping = tuple((record.frozen_row_id, record.attempt_id) for record in accepted_records)
    invalid_attempt_mapping = tuple((record.frozen_row_id, record.attempt_id) for record in invalid_records)
    orphan_attempt_mapping = tuple((record.frozen_row_id, record.attempt_id) for record in orphan_records)
    frozen_row_ids = _sorted_frozen_row_ids(accepted_records + invalid_records + orphan_records)
    target_trial_ids = _sorted_target_trial_ids(accepted_records + invalid_records + orphan_records)
    attempt_ids = _sorted_attempt_ids(accepted_records + invalid_records + orphan_records)
    batch_manifest_hash_payload = {
        "accepted_attempt_mapping": [
            {"attempt_id": attempt_id, "frozen_row_id": frozen_row_id}
            for frozen_row_id, attempt_id in accepted_attempt_mapping
        ],
        "accepted_finalized_count": len(accepted_records),
        "archive_hash": archive_index.archive_index_sha256,
        "archive_index_sha256": archive_index.archive_index_sha256,
        "attempt_ids": list(attempt_ids),
        "batch_id": input_data.batch_id,
        "count_hash": count_hash,
        "dataset_version": input_data.dataset_version,
        "event_log_sha256": input_data.event_log_sha256,
        "finalization_status": input_data.finalization_status,
        "frozen_row_ids": list(frozen_row_ids),
        "generated_utc": generated_utc,
        "incomplete_attempt_count": len(incomplete_records),
        "invalid_attempt_count": len(invalid_records),
        "invalid_attempt_mapping": [
            {"attempt_id": attempt_id, "frozen_row_id": frozen_row_id}
            for frozen_row_id, attempt_id in invalid_attempt_mapping
        ],
        "model_runtime_hash": input_data.model_runtime_hash,
        "model_slot": input_data.model_slot,
        "orphan_attempt_count": len(orphan_records),
        "orphan_attempt_mapping": [
            {"attempt_id": attempt_id, "frozen_row_id": frozen_row_id}
            for frozen_row_id, attempt_id in orphan_attempt_mapping
        ],
        "phase45_go_hash": input_data.phase45_go_hash,
        "phase4_lock_hash": input_data.phase4_lock_hash,
        "raw_evidence_archive_sha256": input_data.raw_evidence_archive_sha256,
        "run_id": input_data.run_id,
        "schema_grader_tid_hash": input_data.schema_grader_tid_hash,
        "schema_validation_report_sha256": input_data.schema_validation_report_sha256,
        "source_commit": input_data.source_commit,
        "status": input_data.finalization_status,
        "target_trial_ids": list(target_trial_ids),
        "task_id": "P12",
        "trial_jsonl_sha256": accepted_rows_sha256,
        "workload": input_data.workload,
    }
    batch_manifest_sha256 = _sha256_bytes(_canonical_json(batch_manifest_hash_payload).encode("utf-8"))
    batch_manifest = BatchManifest(
        task_id="P12",
        status=input_data.finalization_status,
        generated_utc=generated_utc,
        dataset_version=input_data.dataset_version,
        run_id=input_data.run_id,
        batch_id=input_data.batch_id,
        model_slot=input_data.model_slot,
        workload=input_data.workload,
        source_commit=input_data.source_commit,
        phase4_lock_hash=input_data.phase4_lock_hash,
        phase45_go_hash=input_data.phase45_go_hash,
        model_runtime_hash=input_data.model_runtime_hash,
        schema_grader_tid_hash=input_data.schema_grader_tid_hash,
        archive_hash=archive_index.archive_index_sha256,
        count_hash=count_hash,
        accepted_attempt_mapping=accepted_attempt_mapping,
        invalid_attempt_mapping=invalid_attempt_mapping,
        orphan_attempt_mapping=orphan_attempt_mapping,
        frozen_row_ids=frozen_row_ids,
        target_trial_ids=target_trial_ids,
        attempt_ids=attempt_ids,
        accepted_finalized_count=len(accepted_records),
        invalid_attempt_count=len(invalid_records),
        orphan_attempt_count=len(orphan_records),
        incomplete_attempt_count=len(incomplete_records),
        trial_jsonl_sha256=accepted_rows_sha256,
        event_log_sha256=input_data.event_log_sha256,
        raw_evidence_archive_sha256=input_data.raw_evidence_archive_sha256,
        schema_validation_report_sha256=input_data.schema_validation_report_sha256,
        archive_index_sha256=archive_index.archive_index_sha256,
        finalization_status=input_data.finalization_status,
        manifest_sha256=batch_manifest_sha256,
    )
    checkpoint_record = build_checkpoint_record(
        dataset_version=input_data.dataset_version,
        model_slot=input_data.model_slot,
        workload=input_data.workload,
        run_id=input_data.run_id,
        batch_id=input_data.batch_id,
        source_commit=input_data.source_commit,
        phase4_lock_hash=input_data.phase4_lock_hash,
        phase45_go_hash=input_data.phase45_go_hash,
        expected_remote_head_before_push=input_data.expected_remote_head_before_push,
        accepted_finalized_count=len(accepted_records),
        invalid_attempt_count=len(invalid_records),
        orphan_attempt_count=len(orphan_records),
        batch_manifest_sha256=batch_manifest.manifest_sha256,
        evidence_index_sha256=archive_index.archive_index_sha256,
        session_seal_closed=True,
        seal_epoch=input_data.seal_epoch,
        sync_barrier_status=input_data.sync_barrier_status,
        continuation_authorized_after_reverify=input_data.continuation_authorized_after_reverify,
        no_more_official_execution_in_session=input_data.no_more_official_execution_in_session,
        finalization_status=input_data.finalization_status,
    )
    checkpoint_json = json.dumps(checkpoint_record.to_mapping(), sort_keys=True, separators=(",", ":")) + "\n"
    checkpoint_archive_sha256 = _sha256_bytes(checkpoint_json.encode("utf-8"))
    run_manifest_hash_payload = {
        "accelerator_identity": input_data.accelerator_identity,
        "artifact_hashes": {
            "accepted_rows_jsonl": accepted_rows_sha256,
            "archive_index": archive_index.archive_index_sha256,
            "batch_manifest": batch_manifest.manifest_sha256,
            "checkpoint": checkpoint_archive_sha256,
        },
        "batch_ids": [input_data.batch_id],
        "checkpoint_archive_sha256": checkpoint_archive_sha256,
        "continuation_authorized_after_reverify": input_data.continuation_authorized_after_reverify,
        "counts_hash": count_hash,
        "dataset_version": input_data.dataset_version,
        "device_map_identity": input_data.device_map_identity,
        "dependency_lock_hash": input_data.dependency_lock_hash,
        "finalization_status": input_data.finalization_status,
        "generated_utc": generated_utc,
        "model_identity": input_data.model_identity,
        "model_slot": input_data.model_slot,
        "model_runtime_hash": input_data.model_runtime_hash,
        "no_more_official_execution_in_session": input_data.no_more_official_execution_in_session,
        "official_seal_timestamp": input_data.official_seal_timestamp,
        "phase45_go_hash": input_data.phase45_go_hash,
        "phase4_lock_hash": input_data.phase4_lock_hash,
        "schema_grader_tid_hash": input_data.schema_grader_tid_hash,
        "run_id": input_data.run_id,
        "seal_epoch": input_data.seal_epoch,
        "source_commit": input_data.source_commit,
        "status": input_data.finalization_status,
        "sync_barrier_status": input_data.sync_barrier_status,
        "task_id": "P12",
        "tokenizer_identity": input_data.tokenizer_identity,
        "backend_identity": input_data.backend_identity,
    }
    run_manifest_sha256 = _sha256_bytes(_canonical_json(run_manifest_hash_payload).encode("utf-8"))
    run_manifest = RunManifest(
        task_id="P12",
        status=input_data.finalization_status,
        generated_utc=generated_utc,
        dataset_version=input_data.dataset_version,
        run_id=input_data.run_id,
        source_commit=input_data.source_commit,
        phase4_lock_hash=input_data.phase4_lock_hash,
        phase45_go_hash=input_data.phase45_go_hash,
        model_slot=input_data.model_slot,
        model_runtime_hash=input_data.model_runtime_hash,
        schema_grader_tid_hash=input_data.schema_grader_tid_hash,
        model_identity=input_data.model_identity,
        tokenizer_identity=input_data.tokenizer_identity,
        backend_identity=input_data.backend_identity,
        accelerator_identity=input_data.accelerator_identity,
        device_map_identity=input_data.device_map_identity,
        dependency_lock_hash=input_data.dependency_lock_hash,
        seal_epoch=input_data.seal_epoch,
        official_seal_timestamp=input_data.official_seal_timestamp,
        sync_barrier_status=input_data.sync_barrier_status,
        continuation_authorized_after_reverify=input_data.continuation_authorized_after_reverify,
        no_more_official_execution_in_session=input_data.no_more_official_execution_in_session,
        batch_ids=(input_data.batch_id,),
        counts_hash=count_hash,
        artifact_hashes={
            "accepted_rows_jsonl": accepted_rows_sha256,
            "archive_index": archive_index.archive_index_sha256,
            "batch_manifest": batch_manifest.manifest_sha256,
            "checkpoint": checkpoint_archive_sha256,
        },
        checkpoint_archive_sha256=checkpoint_archive_sha256,
        finalization_status=input_data.finalization_status,
        manifest_sha256=run_manifest_sha256,
    )
    return FinalizationBundle(
        accepted_rows_jsonl=accepted_rows_jsonl,
        archive_index=archive_index,
        batch_manifest=batch_manifest,
        run_manifest=run_manifest,
        checkpoint_record=checkpoint_record,
    )
