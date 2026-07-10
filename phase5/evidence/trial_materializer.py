"""Exact frozen-schema row materialization for Phase 5 evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..domain import FROZEN_TRIAL_FIELDS, FrozenTrialRow, FROZEN_TRIAL_FIELD_SET, PROHIBITED_FIELD_ALIASES
from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from ..grading.frozen_grader import GraderPredicateEvidence
from ..grading.tid import TidResult


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_relative_path(path: Path) -> None:
    if path.is_absolute() or any(part == ".." for part in path.parts):
        raise SchemaInvariantError(f"evidence reference must stay within the evidence root: {path.as_posix()}")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    name: str
    relative_path: Path
    sha256: str


@dataclass(frozen=True, slots=True)
class VerifiedEvidenceReference(EvidenceReference):
    absolute_path: Path
    byte_length: int


@dataclass(frozen=True, slots=True)
class MaterializedTrialRow:
    row: dict[str, Any]
    evidence_references: tuple[VerifiedEvidenceReference, ...]
    schema_id: str
    grader_predicate_evidence: GraderPredicateEvidence | None = None
    tid_result: TidResult | None = None


def verify_evidence_reference(reference: EvidenceReference, evidence_root: Path) -> VerifiedEvidenceReference:
    _require_relative_path(reference.relative_path)
    absolute_path = evidence_root / reference.relative_path
    if not absolute_path.is_file():
        raise MissingFrozenSettingError(f"missing evidence reference: {absolute_path.as_posix()}")
    data = absolute_path.read_bytes()
    actual_sha256 = _sha256_bytes(data)
    if actual_sha256 != reference.sha256:
        raise FrozenArtifactHashError(
            f"evidence reference hash mismatch for {absolute_path.as_posix()}: expected {reference.sha256}, got {actual_sha256}"
        )
    return VerifiedEvidenceReference(
        name=reference.name,
        relative_path=reference.relative_path,
        sha256=reference.sha256,
        absolute_path=absolute_path,
        byte_length=len(data),
    )


def verify_evidence_references(
    references: Sequence[EvidenceReference],
    *,
    evidence_root: Path,
) -> tuple[VerifiedEvidenceReference, ...]:
    return tuple(verify_evidence_reference(reference, evidence_root) for reference in references)


def _corrected_queue_schema_path() -> Path:
    return Path(__file__).resolve().parents[2] / "phase4" / "frozen_bundle_v2" / "queue_schema.json"


def _load_corrected_queue_fields() -> tuple[str, ...]:
    path = _corrected_queue_schema_path()
    if not path.is_file():
        return ()
    data = json.loads(path.read_text(encoding="utf-8"))
    fields = data.get("fields")
    if not isinstance(fields, list) or not all(isinstance(item, str) for item in fields):
        raise SchemaInvariantError("corrected queue schema must define string fields")
    return tuple(fields)


def _canonical_official_trial_row(mapping: Mapping[str, Any]) -> dict[str, Any]:
    keys = set(mapping)
    aliases = sorted(key for key in keys if key in PROHIBITED_FIELD_ALIASES)
    if aliases:
        alias_text = ", ".join(f"{alias}->{PROHIBITED_FIELD_ALIASES[alias]}" for alias in aliases)
        raise SchemaInvariantError(f"prohibited field alias used in frozen row materialization: {alias_text}")
    missing = [field for field in FROZEN_TRIAL_FIELDS if field not in mapping]
    extra = [field for field in mapping if field not in FROZEN_TRIAL_FIELD_SET]
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise MissingFrozenSettingError(f"frozen trial row field mismatch: {'; '.join(details)}")
    row = {field: mapping[field] for field in FROZEN_TRIAL_FIELDS}
    FrozenTrialRow.from_mapping(row)
    return row


def _canonical_corrected_queue_row(mapping: Mapping[str, Any]) -> dict[str, Any]:
    fields = _load_corrected_queue_fields()
    if not fields:
        raise MissingFrozenSettingError("corrected queue schema is missing")
    keys = set(mapping)
    missing = [field for field in fields if field not in mapping]
    extra = [field for field in mapping if field not in fields]
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise MissingFrozenSettingError(f"corrected queue row field mismatch: {'; '.join(details)}")
    row = {field: mapping[field] for field in fields}
    if row["status"] != "PENDING":
        raise SchemaInvariantError("corrected queue rows must materialize from PENDING rows")
    if not row["task_id"] or not row["task_hash"]:
        raise SchemaInvariantError("corrected queue materialization must preserve task identity")
    if row["payload_condition"] == "NONE":
        if row["payload_id"] not in {"", None} or row["phase1_payload_hash"] not in {"", None}:
            raise SchemaInvariantError("utility corrected queue rows must preserve null payload semantics")
    elif row["payload_condition"] == "PHASE1_HASH_AUTHORIZED":
        if not row["payload_id"]:
            raise SchemaInvariantError("adversarial corrected queue rows must preserve payload identity")
    else:
        raise SchemaInvariantError(f"unknown corrected queue payload_condition: {row['payload_condition']!r}")
    return row


def _canonical_row(mapping: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    if set(mapping) == FROZEN_TRIAL_FIELD_SET:
        return _canonical_official_trial_row(mapping), "phase5_official_trial_schema"
    corrected_fields = set(_load_corrected_queue_fields())
    if corrected_fields and set(mapping) == corrected_fields:
        return _canonical_corrected_queue_row(mapping), "phase4_corrected_v2_queue_schema"
    official_missing = [field for field in FROZEN_TRIAL_FIELDS if field not in mapping]
    official_extra = [field for field in mapping if field not in FROZEN_TRIAL_FIELD_SET]
    queue_fields = _load_corrected_queue_fields()
    queue_missing = [field for field in queue_fields if field not in mapping]
    queue_extra = [field for field in mapping if field not in set(queue_fields)]
    raise MissingFrozenSettingError(
        "row field mismatch for all materialization schemas: "
        f"official_missing={official_missing}; official_extra={official_extra}; "
        f"queue_missing={queue_missing}; queue_extra={queue_extra}"
    )


def materialize_frozen_trial_row(
    mapping: Mapping[str, Any],
    *,
    evidence_references: Sequence[EvidenceReference] = (),
    evidence_root: Path | None = None,
    grader_predicate_evidence: GraderPredicateEvidence | None = None,
    tid_result: TidResult | None = None,
) -> MaterializedTrialRow:
    if evidence_references and evidence_root is None:
        raise MissingFrozenSettingError("evidence_root is required when evidence references are provided")
    verified_references = (
        verify_evidence_references(evidence_references, evidence_root=evidence_root)
        if evidence_references
        else ()
    )
    row, schema_id = _canonical_row(mapping)
    return MaterializedTrialRow(
        row=row,
        evidence_references=verified_references,
        schema_id=schema_id,
        grader_predicate_evidence=grader_predicate_evidence,
        tid_result=tid_result,
    )
