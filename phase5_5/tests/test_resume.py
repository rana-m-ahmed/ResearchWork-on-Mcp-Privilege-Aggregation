from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from phase5.attempts import AttemptLineageRecord, AttemptLineageStore
from phase5.attempts.lineage import render_lineage_csv
from phase5.domain.errors import SchemaInvariantError
from phase5_5.resume import ResumeMode, resolve_official_resume


DATASET = "P5-DV-1.1.0-TREATMENT-V3"
RUN_ID = f"P5RUN-{DATASET}-M1-20260722-ABCDEF12"
SOURCE = "a" * 40
BATCH_SHA = "b" * 64
PLAN_SHA = "c" * 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _record(
    tmp_path: Path,
    *,
    status: str = "INVALID",
    dataset_version: str = DATASET,
    attempt_id: str = "P5ATT-T00001-A000-ABCDEF12",
    attempt_index: int = 0,
    parent_attempt_id: str | None = None,
) -> AttemptLineageRecord:
    record = AttemptLineageRecord(
        dataset_version=dataset_version,
        frozen_row_id="core-00001-T00001",
        target_trial_id="T00001",
        attempt_id=attempt_id,
        attempt_index=attempt_index,
        parent_attempt_id=parent_attempt_id,
        run_id=RUN_ID if dataset_version == DATASET else f"P5RUN-{dataset_version}-M1-20260718-HISTORIC",
        batch_id="batch-1",
        attempt_status=status,
        invalid_reason="model output" if status == "INVALID" else None,
        counts_toward_cell_n=False,
        accepted_attempt=False,
        raw_attempt_directory=tmp_path / f"phase5_5/evidence/attempts/{attempt_id}",
    )
    attempt_root = Path(record.raw_attempt_directory)
    attempt_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "attempt_id": record.attempt_id,
        "target_trial_id": record.target_trial_id,
        "run_id": record.run_id,
        "dataset_version": record.dataset_version,
        "batch_id": record.batch_id,
    }
    files = {
        "attempt_manifest.json": json.dumps(manifest, sort_keys=True) + "\n",
        "attempt_events.jsonl": json.dumps({"event_type": "FINALIZED"}) + "\n",
        "grader_evidence.json": json.dumps({"official_trial": True, "analysis_eligible_trial": True}) + "\n",
    }
    for name, content in files.items():
        (attempt_root / name).write_text(content, encoding="utf-8")
    index = []
    for name in sorted(files):
        path = attempt_root / name
        index.append({"bytes": path.stat().st_size, "path": name, "sha256": _sha256(path)})
    (attempt_root / "evidence_hash_index.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in index),
        encoding="utf-8",
    )
    return record


def _write_checkpoint(root: Path, *, artifact: str = "phase5_5_trial_checkpoint_v2") -> Path:
    lineage = root / "phase5_5/evidence/lineage.csv"
    records = AttemptLineageStore(lineage).load_records()
    current = tuple(record for record in records if record.dataset_version == DATASET and record.run_id == RUN_ID)
    last = current[-1]
    path = root / f"phase5_5/evidence/checkpoints/{RUN_ID}/checkpoint-000001.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact": artifact,
                "batch_id": "batch-1",
                "batch_manifest_sha256": BATCH_SHA,
                "checkpoint_sequence": 1,
                "completed_lineage_count": len(records),
                "dataset_version": DATASET,
                "last_attempt_id": last.attempt_id,
                "last_target_trial_id": last.target_trial_id,
                "lineage_sha256": _sha256(lineage),
                "model_slot": "M1",
                "parent_head": "d" * 40,
                "run_id": RUN_ID,
                "run_lineage_count": len(current),
                "run_plan_sha256": PLAN_SHA,
                "source_commit": SOURCE,
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_supersession(root: Path) -> Path:
    store = AttemptLineageStore(root / "phase5_5/evidence/lineage.csv")
    records = tuple(record for record in store.load_records() if record.run_id == RUN_ID)
    checkpoint_root = root / "phase5_5/evidence/checkpoints" / RUN_ID
    checkpoint_hashes = {
        path.relative_to(root / "phase5_5/evidence").as_posix(): _sha256(path)
        for path in sorted(checkpoint_root.glob("checkpoint-*.json"))
    }
    path = root / f"phase5_5/evidence/supersessions/{RUN_ID}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "artifact": "phase5_5_campaign_supersession_v1",
                "authorization_basis": "explicit_user_authorization_2026-07-22",
                "checkpoint_count": len(checkpoint_hashes),
                "checkpoint_sha256": checkpoint_hashes,
                "dataset_version": DATASET,
                "model_slot": "M1",
                "status_counts": {"INVALID": len(records)},
                "superseded_lineage_count": len(records),
                "superseded_lineage_sha256": hashlib.sha256(
                    render_lineage_csv(records).encode("utf-8")
                ).hexdigest(),
                "superseded_run_id": RUN_ID,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _resolve(root: Path):
    return resolve_official_resume(
        root=root,
        model_slot="M1",
        dataset_version=DATASET,
        source_commit=SOURCE,
        batch_manifest_sha256=BATCH_SHA,
        run_plan_sha256=PLAN_SHA,
        proposed_run_id=f"P5RUN-{DATASET}-M1-20260722-EEEEEEEE",
    )


def test_no_current_evidence_starts_new_run(tmp_path: Path) -> None:
    result = _resolve(tmp_path)
    assert result.mode is ResumeMode.NEW
    assert result.checkpoint_sequence == 0


def test_source_bound_checkpoint_resumes_same_run_and_sequence(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path)
    result = _resolve(tmp_path)
    assert result.mode is ResumeMode.RESUME
    assert result.run_id == RUN_ID
    assert result.checkpoint_sequence == 1
    assert result.completed_target_count == 1


def test_resume_accepts_explicit_dataset_epoch_boundary(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    historical = _record(
        tmp_path,
        dataset_version="P5-DV-1.0.2-A7C91E42",
        attempt_id="P5ATT-T00001-A000-HISTORIC",
    )
    current = _record(
        tmp_path,
        attempt_id="P5ATT-T00001-A001-ABCDEF12",
        attempt_index=1,
        parent_attempt_id=historical.attempt_id,
    )
    store.append(historical)
    store.append(current)
    _write_checkpoint(tmp_path)

    result = _resolve(tmp_path)

    assert result.mode is ResumeMode.RESUME
    assert result.completed_target_count == 1


def test_tampered_lineage_fails_closed(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path)
    lineage = tmp_path / "phase5_5/evidence/lineage.csv"
    lineage.write_text(
        lineage.read_text(encoding="utf-8").replace("model output", "tampered output"),
        encoding="utf-8",
    )
    with pytest.raises(SchemaInvariantError, match="lineage_sha256 mismatch"):
        _resolve(tmp_path)


def test_legacy_current_dataset_evidence_cannot_be_mixed(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path, artifact="phase5_5_trial_checkpoint_v1")
    with pytest.raises(SchemaInvariantError, match="legacy current-dataset"):
        _resolve(tmp_path)


def test_exact_legacy_campaign_can_be_superseded_without_deleting_evidence(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path, artifact="phase5_5_trial_checkpoint_v1")
    lineage_before = (tmp_path / "phase5_5/evidence/lineage.csv").read_bytes()
    checkpoint_before = (
        tmp_path / f"phase5_5/evidence/checkpoints/{RUN_ID}/checkpoint-000001.json"
    ).read_bytes()
    _write_supersession(tmp_path)

    result = _resolve(tmp_path)

    assert result.mode is ResumeMode.NEW
    assert (tmp_path / "phase5_5/evidence/lineage.csv").read_bytes() == lineage_before
    assert (
        tmp_path / f"phase5_5/evidence/checkpoints/{RUN_ID}/checkpoint-000001.json"
    ).read_bytes() == checkpoint_before


def test_supersession_fails_if_legacy_lineage_changes(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path, artifact="phase5_5_trial_checkpoint_v1")
    _write_supersession(tmp_path)
    lineage = tmp_path / "phase5_5/evidence/lineage.csv"
    lineage.write_text(
        lineage.read_text(encoding="utf-8").replace("model output", "changed"),
        encoding="utf-8",
    )
    with pytest.raises(SchemaInvariantError, match="superseded_lineage_sha256 mismatch"):
        _resolve(tmp_path)


def test_supersession_fails_if_legacy_checkpoint_changes(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    checkpoint = _write_checkpoint(tmp_path, artifact="phase5_5_trial_checkpoint_v1")
    _write_supersession(tmp_path)
    checkpoint.write_text(checkpoint.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(SchemaInvariantError, match="checkpoint_sha256 mismatch"):
        _resolve(tmp_path)


def test_source_bound_v2_campaign_cannot_be_superseded(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path)
    _write_supersession(tmp_path)
    with pytest.raises(SchemaInvariantError, match="cannot supersede a source-bound v2"):
        _resolve(tmp_path)


def test_publication_markers_make_run_complete(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path)
    publication = tmp_path / "phase5_5/evidence/publications" / RUN_ID
    publication.mkdir(parents=True)
    (publication / "official_publication_manifest.json").write_text(json.dumps({"run_id": RUN_ID}), encoding="utf-8")
    (publication / "official_publication_receipt.json").write_text(json.dumps({"run_id": RUN_ID}), encoding="utf-8")
    assert _resolve(tmp_path).mode is ResumeMode.COMPLETE


def test_checkpoint_source_mismatch_fails_closed(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    path = _write_checkpoint(tmp_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_commit"] = "f" * 40
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SchemaInvariantError, match="source_commit mismatch"):
        _resolve(tmp_path)


def test_tampered_attempt_evidence_fails_closed(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    record = _record(tmp_path)
    store.append(record)
    _write_checkpoint(tmp_path)
    grader = Path(record.raw_attempt_directory) / "grader_evidence.json"
    grader.write_text(json.dumps({"official_trial": True, "analysis_eligible_trial": False}), encoding="utf-8")
    with pytest.raises(SchemaInvariantError, match="evidence hash mismatch"):
        _resolve(tmp_path)


def test_historical_other_dataset_does_not_become_resume_candidate(tmp_path: Path) -> None:
    old_dataset = "P5-DV-1.0.2-A7C91E42"
    old_run = f"P5RUN-{old_dataset}-M1-20260718-ABCDEF12"
    record = _record(tmp_path)
    old_record = AttemptLineageRecord(
        dataset_version=old_dataset,
        frozen_row_id=record.frozen_row_id,
        target_trial_id=record.target_trial_id,
        attempt_id=record.attempt_id,
        attempt_index=record.attempt_index,
        parent_attempt_id=None,
        run_id=old_run,
        batch_id=record.batch_id,
        attempt_status="INVALID",
        invalid_reason="historical",
        counts_toward_cell_n=False,
        accepted_attempt=False,
        raw_attempt_directory=record.raw_attempt_directory,
    )
    AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv").append(old_record)
    result = _resolve(tmp_path)
    assert result.mode is ResumeMode.NEW


def test_multiple_current_v2_runs_fail_closed(tmp_path: Path) -> None:
    store = AttemptLineageStore(tmp_path / "phase5_5/evidence/lineage.csv")
    store.append(_record(tmp_path))
    _write_checkpoint(tmp_path)
    second_run = f"P5RUN-{DATASET}-M1-20260722-FFFFFFFF"
    second = tmp_path / f"phase5_5/evidence/checkpoints/{second_run}/checkpoint-000001.json"
    second.parent.mkdir(parents=True)
    payload = json.loads(
        (tmp_path / f"phase5_5/evidence/checkpoints/{RUN_ID}/checkpoint-000001.json").read_text(encoding="utf-8")
    )
    payload["run_id"] = second_run
    second.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(SchemaInvariantError, match="multiple source-bound"):
        _resolve(tmp_path)
