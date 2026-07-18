"""Append-only forensic closure for historical Phase 5 parser orphans."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


ORPHANED_INVALID = "ORPHANED_INVALID"


class EvidenceHashMismatchError(ValueError):
    """Historical evidence cannot be closed against an invalid hash index."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ClosureRecord:
    source_branch: str
    attempt_id: str
    dataset_version: str
    frozen_row_id: str
    target_trial_id: str
    run_id: str
    batch_id: str
    original_status: str
    forensic_status: str
    parser_reason: str
    raw_attempt_directory: str
    artifact_hashes: Mapping[str, str]
    closed_utc: str

    def to_mapping(self) -> dict[str, object]:
        return {
            "artifact_hashes": dict(self.artifact_hashes),
            "attempt_id": self.attempt_id,
            "batch_id": self.batch_id,
            "closed_utc": self.closed_utc,
            "dataset_version": self.dataset_version,
            "forensic_status": self.forensic_status,
            "frozen_row_id": self.frozen_row_id,
            "original_status": self.original_status,
            "parser_reason": self.parser_reason,
            "raw_attempt_directory": self.raw_attempt_directory,
            "run_id": self.run_id,
            "source_branch": self.source_branch,
            "target_trial_id": self.target_trial_id,
        }


def _parser_reason(attempt_dir: Path, fallback: str) -> str:
    parser_events = attempt_dir / "parser_events.jsonl"
    if not parser_events.exists():
        return fallback
    for line in parser_events.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event_type") == "PARSE_FAILURE":
            return str(event.get("details") or event.get("reason") or fallback)
    return fallback


def _artifact_hashes(attempt_dir: Path) -> dict[str, str]:
    """Use the attempt's hash index and independently verify critical files."""

    index_path = attempt_dir / "evidence_hash_index.jsonl"
    indexed: dict[str, str] = {}
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").splitlines():
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            path = item.get("path")
            digest = item.get("sha256")
            if isinstance(path, str) and isinstance(digest, str):
                indexed[path] = digest
        actual = {
            path.name: _sha256(path)
            for path in sorted(attempt_dir.iterdir())
            if path.is_file() and path.name != "evidence_hash_index.jsonl"
        }
        for name, expected in indexed.items():
            if name not in actual or actual[name] != expected:
                raise EvidenceHashMismatchError(
                    f"historical evidence hash mismatch for {attempt_dir / name}"
                )
        actual["evidence_hash_index.jsonl"] = _sha256(index_path)
        return actual
    return {
        path.name: _sha256(path)
        for path in sorted(attempt_dir.iterdir())
        if path.is_file()
    }


def discover_orphan_closures(
    evidence_root: Path,
    *,
    source_branch: str,
    allowed_model_slots: tuple[str, ...] = ("M2", "M3"),
    closed_utc: str | None = None,
) -> tuple[ClosureRecord, ...]:
    """Build closure records without writing to the historical evidence root."""

    lineage_path = evidence_root / "lineage.csv"
    if not lineage_path.exists():
        return ()
    now = closed_utc or datetime.now(timezone.utc).isoformat()
    records: list[ClosureRecord] = []
    with lineage_path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            batch_id = row.get("batch_id", "")
            if row.get("attempt_status") != "INVALID":
                continue
            if row.get("counts_toward_cell_n", "").lower() == "true" or row.get("accepted_attempt", "").lower() == "true":
                continue
            if not any(f"-{slot}-" in batch_id for slot in allowed_model_slots):
                continue
            attempt_dir = Path(row.get("raw_attempt_directory", ""))
            if not attempt_dir.exists():
                attempt_id = row.get("attempt_id", "")
                attempt_dir = evidence_root / "attempts" / attempt_id
            if not attempt_dir.exists():
                raise FileNotFoundError(f"historical orphan attempt directory is missing: {attempt_dir}")
            artifact_hashes = _artifact_hashes(attempt_dir)
            records.append(
                ClosureRecord(
                    source_branch=source_branch,
                    attempt_id=row.get("attempt_id", ""),
                    dataset_version=row.get("dataset_version", ""),
                    frozen_row_id=row.get("frozen_row_id", ""),
                    target_trial_id=row.get("target_trial_id", ""),
                    run_id=row.get("run_id", ""),
                    batch_id=batch_id,
                    original_status=row.get("attempt_status", ""),
                    forensic_status=ORPHANED_INVALID,
                    parser_reason=_parser_reason(attempt_dir, row.get("invalid_reason", "parser failure")),
                    raw_attempt_directory=f"phase5/evidence/attempts/{row.get('attempt_id', '')}",
                    artifact_hashes=artifact_hashes,
                    closed_utc=now,
                )
            )
    return tuple(records)


def write_append_only_closure(records: Iterable[ClosureRecord], output: Path) -> None:
    """Write JSONL once, or append an identical-prefix extension only."""

    encoded = "".join(
        json.dumps(record.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for record in records
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    if not encoded:
        return
    if output.exists():
        existing = output.read_text(encoding="utf-8")
        if encoded == existing or encoded.startswith(existing):
            if encoded != existing:
                output.write_text(encoded, encoding="utf-8")
            return
        raise ValueError(f"closure ledger rewrite would remove existing history: {output}")
    output.write_text(encoded, encoding="utf-8")


def reconcile_closures(
    records: Iterable[ClosureRecord],
    *,
    expected_attempt_ids: Iterable[str] | None = None,
) -> dict[str, object]:
    rows = tuple(records)
    ids = [row.attempt_id for row in rows]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    expected = set(expected_attempt_ids or ())
    actual = set(ids)
    missing = sorted(expected - actual)
    extra = sorted(actual - expected) if expected else []
    return {
        "closure_count": len(rows),
        "duplicate_attempt_ids": duplicates,
        "missing_expected_attempt_ids": missing,
        "unexpected_attempt_ids": extra,
        "all_orphaned_invalid": all(row.forensic_status == ORPHANED_INVALID for row in rows),
        "all_originally_invalid": all(row.original_status == "INVALID" for row in rows),
        "accepted_count": 0,
        "finalized_count": 0,
        "publication_evidence_count": 0,
        "reconciliation_pass": (
            not duplicates
            and not missing
            and not extra
            and all(row.forensic_status == ORPHANED_INVALID for row in rows)
            and all(row.original_status == "INVALID" for row in rows)
        ),
    }
