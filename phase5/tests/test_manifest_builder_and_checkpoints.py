from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from phase5.attempts.lineage import AttemptLineageRecord
from phase5.checkpoints import (
    CheckpointRecord,
    FINALIZATION_STATUS_FINALIZED_NOT_SYNCED,
    build_checkpoint_record,
    load_checkpoint_schema,
    validate_checkpoint_record,
    validate_continuation_authorization,
)
from phase5.domain.errors import DuplicateAcceptedAttemptError, MissingFrozenSettingError, SchemaInvariantError, SyncSafetyError
from phase5.evidence import (
    ArchiveIndexEntry,
    AttemptFinalizationRecord,
    BatchFinalizationInput,
    EvidenceReference,
    build_accepted_row_jsonl,
    build_archive_index,
    build_finalization_bundle,
    verify_evidence_reference,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _lineage(
    attempt_id: str,
    *,
    frozen_row_id: str,
    target_trial_id: str,
    attempt_index: int,
    accepted_attempt: bool,
    counts_toward_cell_n: bool,
    attempt_status: str = "FINALIZED",
    invalid_reason: str | None = None,
    parent_attempt_id: str | None = None,
) -> AttemptLineageRecord:
    return AttemptLineageRecord(
        dataset_version="P5-DV-1.0.0-A7C91E42",
        frozen_row_id=frozen_row_id,
        target_trial_id=target_trial_id,
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        parent_attempt_id=parent_attempt_id,
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        attempt_status=attempt_status,
        invalid_reason=invalid_reason,
        counts_toward_cell_n=counts_toward_cell_n,
        accepted_attempt=accepted_attempt,
        raw_attempt_directory=Path(f"phase5/evidence/attempts/{attempt_id}"),
    )


def _evidence_ref(root: Path, relative_path: str, name: str = "artifact") -> EvidenceReference:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{name}\n", encoding="utf-8")
    return EvidenceReference(name=name, relative_path=Path(relative_path), sha256=_sha256(path))


def _finalization_input() -> BatchFinalizationInput:
    return BatchFinalizationInput(
        dataset_version="P5-DV-1.0.0-A7C91E42",
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        model_slot="M1",
        workload="phase5_adversarial_core",
        source_commit="3a92c2d7e2987290b801cee95ae3c506254ff8f6",
        phase4_lock_hash="09122acabc4ea034aae2ea43adfbfb9b6b370e926db1222861d11d37e87cd11f",
        phase45_go_hash="910fa15b9e60f239a7de1f164f25a5c7b61bafece47e48cda54bae5acc97b5d7",
        model_runtime_hash="runtime-hash",
        schema_grader_tid_hash="schema-grader-tid-hash",
        dependency_lock_hash="dependency-lock-hash",
        model_identity="Qwen/Qwen2.5-7B-Instruct",
        tokenizer_identity="microsoft/Phi-3.5-mini-instruct",
        backend_identity="transformers==5.0.0",
        accelerator_identity="A100-SXM4-80GB",
        device_map_identity="cuda:0",
        official_seal_timestamp="2026-07-08T01:00:00Z",
        seal_epoch=2,
        sync_barrier_status="NOT_SYNCED",
        continuation_authorized_after_reverify=False,
        no_more_official_execution_in_session=False,
        expected_remote_head_before_push="4e329f8cad35770e15a7750883e2b2e96629e71c",
        trial_jsonl_sha256="trial-jsonl-hash",
        event_log_sha256="event-log-hash",
        raw_evidence_archive_sha256="raw-archive-hash",
        schema_validation_report_sha256="schema-report-hash",
    )


def test_finalization_bundle_is_deterministic_and_writes_atomic_bundle(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    accepted_ref = _evidence_ref(evidence_root, "attempts/accepted.txt", "accepted")
    invalid_ref = _evidence_ref(evidence_root, "attempts/invalid.txt", "invalid")
    orphan_ref = _evidence_ref(evidence_root, "attempts/orphan.txt", "orphan")

    accepted_lineage = _lineage(
        "P5ATT-trial-001-A000-ABCDEF12",
        frozen_row_id="row_001",
        target_trial_id="trial-001",
        attempt_index=0,
        accepted_attempt=True,
        counts_toward_cell_n=True,
    )
    invalid_lineage = _lineage(
        "P5ATT-trial-002-A000-ABCDEF12",
        frozen_row_id="row_002",
        target_trial_id="trial-002",
        attempt_index=0,
        accepted_attempt=False,
        counts_toward_cell_n=False,
        invalid_reason="MODEL_FAILURE",
    )
    orphan_lineage = _lineage(
        "P5ATT-trial-003-A001-ABCDEF12",
        frozen_row_id="row_003",
        target_trial_id="trial-003",
        attempt_index=1,
        accepted_attempt=False,
        counts_toward_cell_n=False,
        invalid_reason="ORPHANED",
        parent_attempt_id="P5ATT-trial-003-A000-ABCDEF12",
    )

    records = (
        AttemptFinalizationRecord(
            lineage=accepted_lineage,
            category="ACCEPTED",
            evidence_references=(accepted_ref,),
            archive_uri="s3://phase5/accepted.tar.zst",
            archive_size_bytes=128,
            archive_sha256="a" * 64,
            archive_retrieval_status="AVAILABLE",
        ),
        AttemptFinalizationRecord(
            lineage=invalid_lineage,
            category="INVALID",
            evidence_references=(invalid_ref,),
            archive_uri="s3://phase5/invalid.tar.zst",
            archive_size_bytes=64,
            archive_sha256="b" * 64,
            archive_retrieval_status="AVAILABLE",
        ),
        AttemptFinalizationRecord(
            lineage=orphan_lineage,
            category="ORPHAN",
            evidence_references=(orphan_ref,),
            archive_uri="s3://phase5/orphan.tar.zst",
            archive_size_bytes=32,
            archive_sha256="c" * 64,
            archive_retrieval_status="AVAILABLE",
        ),
    )
    finalization_input = _finalization_input()

    bundle_one = build_finalization_bundle(
        finalization_input,
        records,
        generated_utc="2026-07-08T01:10:00Z",
        evidence_root=evidence_root,
    )
    bundle_two = build_finalization_bundle(
        finalization_input,
        records,
        generated_utc="2026-07-08T01:10:00Z",
        evidence_root=evidence_root,
    )
    accepted_jsonl, accepted_sha256 = build_accepted_row_jsonl((accepted_lineage, invalid_lineage, orphan_lineage))

    assert bundle_one.accepted_rows_jsonl == bundle_two.accepted_rows_jsonl == accepted_jsonl
    assert bundle_one.batch_manifest.trial_jsonl_sha256 == accepted_sha256
    assert bundle_one.batch_manifest.manifest_sha256 == bundle_two.batch_manifest.manifest_sha256
    assert bundle_one.run_manifest.manifest_sha256 == bundle_two.run_manifest.manifest_sha256
    assert bundle_one.archive_index.archive_index_sha256 == bundle_two.archive_index.archive_index_sha256
    assert bundle_one.run_manifest.model_runtime_hash == "runtime-hash"
    assert bundle_one.run_manifest.schema_grader_tid_hash == "schema-grader-tid-hash"
    assert bundle_one.checkpoint_record.finalization_status == FINALIZATION_STATUS_FINALIZED_NOT_SYNCED
    assert bundle_one.checkpoint_record.session_seal_closed is True
    assert bundle_one.checkpoint_record.seal_epoch == 2
    assert bundle_one.checkpoint_record.no_more_official_execution_in_session is False
    assert bundle_one.checkpoint_record.continuation_authorized_after_reverify is False
    assert validate_checkpoint_record(bundle_one.checkpoint_record.to_mapping()) == []
    assert bundle_one.batch_manifest.to_json() == bundle_two.batch_manifest.to_json()
    assert bundle_one.run_manifest.to_json() == bundle_two.run_manifest.to_json()

    output_root = tmp_path / "finalized" / "P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2"
    written = bundle_one.write(output_root)
    assert written == output_root
    assert (output_root / "accepted_rows.jsonl").is_file()
    assert (output_root / "archive_index.json").is_file()
    assert (output_root / "archive_index.md").is_file()
    assert (output_root / "batch_manifest.json").is_file()
    assert (output_root / "batch_manifest.md").is_file()
    assert (output_root / "run_manifest.json").is_file()
    assert (output_root / "run_manifest.md").is_file()
    assert (output_root / "checkpoint.json").is_file()

    checkpoint_json = json.loads((output_root / "checkpoint.json").read_text(encoding="utf-8"))
    assert checkpoint_json["finalization_status"] == FINALIZATION_STATUS_FINALIZED_NOT_SYNCED


def test_missing_or_corrupt_raw_artifact_fails_closed(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    evidence_root.mkdir()
    missing = EvidenceReference(name="missing", relative_path=Path("missing.txt"), sha256="0" * 64)
    with pytest.raises(MissingFrozenSettingError):
        verify_evidence_reference(missing, evidence_root)

    corrupt_path = evidence_root / "payload.txt"
    corrupt_path.parent.mkdir(parents=True, exist_ok=True)
    corrupt_path.write_text("corrupt\n", encoding="utf-8")
    corrupt = EvidenceReference(name="payload", relative_path=Path("payload.txt"), sha256="0" * 64)
    from phase5.domain.errors import FrozenArtifactHashError

    with pytest.raises(FrozenArtifactHashError):
        verify_evidence_reference(corrupt, evidence_root)


def test_duplicate_accepted_target_fails_closed(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    ref_one = _evidence_ref(evidence_root, "attempts/accepted-1.txt", "accepted-1")
    ref_two = _evidence_ref(evidence_root, "attempts/accepted-2.txt", "accepted-2")

    lineage_one = _lineage(
        "P5ATT-trial-010-A000-ABCDEF12",
        frozen_row_id="row_010",
        target_trial_id="trial-010",
        attempt_index=0,
        accepted_attempt=True,
        counts_toward_cell_n=True,
    )
    lineage_two = _lineage(
        "P5ATT-trial-011-A000-ABCDEF12",
        frozen_row_id="row_010",
        target_trial_id="trial-010",
        attempt_index=0,
        accepted_attempt=True,
        counts_toward_cell_n=True,
    )

    records = (
        AttemptFinalizationRecord(lineage=lineage_one, category="ACCEPTED", evidence_references=(ref_one,)),
        AttemptFinalizationRecord(lineage=lineage_two, category="ACCEPTED", evidence_references=(ref_two,)),
    )

    with pytest.raises(DuplicateAcceptedAttemptError):
        build_finalization_bundle(_finalization_input(), records, generated_utc="2026-07-08T01:20:00Z", evidence_root=evidence_root)


def test_unresolved_orphan_fails_closed(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    ref = _evidence_ref(evidence_root, "attempts/orphan.txt", "orphan")
    lineage = _lineage(
        "P5ATT-trial-020-A001-ABCDEF12",
        frozen_row_id="row_020",
        target_trial_id="trial-020",
        attempt_index=1,
        accepted_attempt=False,
        counts_toward_cell_n=False,
        invalid_reason="ORPHANED",
        parent_attempt_id="P5ATT-trial-020-A000-ABCDEF12",
    )

    records = (
        AttemptFinalizationRecord(
            lineage=lineage,
            category="ORPHAN",
            evidence_references=(ref,),
        ),
    )

    with pytest.raises(MissingFrozenSettingError):
        build_finalization_bundle(_finalization_input(), records, generated_utc="2026-07-08T01:30:00Z", evidence_root=evidence_root)


def test_incomplete_attempt_fails_closed(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    ref = _evidence_ref(evidence_root, "attempts/incomplete.txt", "incomplete")
    lineage = _lineage(
        "P5ATT-trial-030-A002-ABCDEF12",
        frozen_row_id="row_030",
        target_trial_id="trial-030",
        attempt_index=2,
        accepted_attempt=False,
        counts_toward_cell_n=False,
        attempt_status="DISPATCHED",
    )

    records = (
        AttemptFinalizationRecord(
            lineage=lineage,
            category="INCOMPLETE",
            evidence_references=(ref,),
        ),
    )

    with pytest.raises(SchemaInvariantError):
        build_finalization_bundle(_finalization_input(), records, generated_utc="2026-07-08T01:40:00Z", evidence_root=evidence_root)


def test_partial_archive_index_fails_closed() -> None:
    with pytest.raises(SchemaInvariantError):
        build_archive_index(
            [
                {
                    "uri": "s3://phase5/partial.tar.zst",
                    "size_bytes": 12,
                    "sha256": "partial",
                    "included_attempt_ids": ["P5ATT-trial-999-A000-ABCDEF12"],
                    "retrieval_status": "AVAILABLE",
                }
            ],
            generated_utc="2026-07-08T01:50:00Z",
        )


def test_manifest_interruption_leaves_no_partial_bundle(tmp_path: Path) -> None:
    evidence_root = tmp_path / "evidence"
    ref = _evidence_ref(evidence_root, "attempts/accepted.txt", "accepted")
    lineage = _lineage(
        "P5ATT-trial-040-A000-ABCDEF12",
        frozen_row_id="row_040",
        target_trial_id="trial-040",
        attempt_index=0,
        accepted_attempt=True,
        counts_toward_cell_n=True,
    )
    records = (
        AttemptFinalizationRecord(
            lineage=lineage,
            category="ACCEPTED",
            evidence_references=(ref,),
            archive_uri="s3://phase5/accepted.tar.zst",
            archive_size_bytes=128,
            archive_sha256="d" * 64,
            archive_retrieval_status="AVAILABLE",
        ),
    )
    bundle = build_finalization_bundle(_finalization_input(), records, generated_utc="2026-07-08T02:00:00Z", evidence_root=evidence_root)
    output_root = tmp_path / "finalized" / "interruptible"

    with pytest.raises(RuntimeError):
        bundle.write(output_root, before_rename_hook=lambda: (_ for _ in ()).throw(RuntimeError("crash")))

    assert not output_root.exists()


def test_checkpoint_schema_requires_seal_epoch_and_sync_fields() -> None:
    schema = load_checkpoint_schema()
    required = set(schema["required"])
    assert "seal_epoch" in required
    assert "sync_barrier_status" in required
    assert "continuation_authorized_after_reverify" in required
    assert "no_more_official_execution_in_session" in required

    checkpoint = CheckpointRecord.from_mapping(
        {
            "accepted_finalized_count": 1,
            "batch_id": "batch-1",
            "batch_manifest_sha256": "1" * 64,
            "continuation_authorized_after_reverify": False,
            "dataset_version": "P5-DV-1.0.0-A7C91E42",
            "evidence_index_sha256": "2" * 64,
            "expected_remote_head_before_push": "3" * 40,
            "finalization_status": FINALIZATION_STATUS_FINALIZED_NOT_SYNCED,
            "invalid_attempt_count": 0,
            "model_slot": "M1",
            "no_more_official_execution_in_session": False,
            "orphan_attempt_count": 0,
            "phase45_go_hash": "4" * 64,
            "phase4_lock_hash": "5" * 64,
            "run_id": "P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
            "seal_epoch": 2,
            "session_seal_closed": True,
            "source_commit": "3a92c2d7e2987290b801cee95ae3c506254ff8f6",
            "sync_barrier_status": "NOT_SYNCED",
            "workload": "phase5_adversarial_core",
        }
    )
    assert checkpoint.seal_epoch == 2
    assert validate_checkpoint_record(checkpoint.to_mapping()) == []


def test_continuation_forbidden_before_reverification() -> None:
    checkpoint = build_checkpoint_record(
        dataset_version="P5-DV-1.0.0-A7C91E42",
        model_slot="M1",
        workload="phase5_adversarial_core",
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        source_commit="3a92c2d7e2987290b801cee95ae3c506254ff8f6",
        phase4_lock_hash="09122acabc4ea034aae2ea43adfbfb9b6b370e926db1222861d11d37e87cd11f",
        phase45_go_hash="910fa15b9e60f239a7de1f164f25a5c7b61bafece47e48cda54bae5acc97b5d7",
        expected_remote_head_before_push="4e329f8cad35770e15a7750883e2b2e96629e71c",
        accepted_finalized_count=1,
        invalid_attempt_count=0,
        orphan_attempt_count=0,
        batch_manifest_sha256="1" * 64,
        evidence_index_sha256="2" * 64,
        session_seal_closed=True,
        seal_epoch=2,
        sync_barrier_status="NOT_SYNCED",
        continuation_authorized_after_reverify=False,
        no_more_official_execution_in_session=False,
    )

    with pytest.raises(SyncSafetyError):
        validate_continuation_authorization(checkpoint)
