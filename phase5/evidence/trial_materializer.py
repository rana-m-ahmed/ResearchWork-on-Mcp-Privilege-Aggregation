"""Exact frozen-schema row materialization for Phase 5 evidence."""

from __future__ import annotations

import hashlib
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


def _canonical_row(mapping: Mapping[str, Any]) -> dict[str, Any]:
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
    row = _canonical_row(mapping)
    return MaterializedTrialRow(
        row=row,
        evidence_references=verified_references,
        grader_predicate_evidence=grader_predicate_evidence,
        tid_result=tid_result,
    )
