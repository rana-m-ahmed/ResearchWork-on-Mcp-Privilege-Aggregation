"""Phase 5 evidence primitives."""

from __future__ import annotations

from .artifacts import ContentAddressedArtifactWriter, RawArtifactRecord, validate_raw_artifact
from .events import AttemptEvent, AttemptEventLogWriter, AttemptEventType, load_attempt_events
from .trial_materializer import (
    EvidenceReference,
    MaterializedTrialRow,
    VerifiedEvidenceReference,
    materialize_frozen_trial_row,
    verify_evidence_reference,
    verify_evidence_references,
)
from .workspace import AttemptWorkspaceMetadata

__all__ = [
    "AttemptEvent",
    "AttemptEventLogWriter",
    "AttemptEventType",
    "AttemptWorkspaceMetadata",
    "ContentAddressedArtifactWriter",
    "EvidenceReference",
    "MaterializedTrialRow",
    "RawArtifactRecord",
    "VerifiedEvidenceReference",
    "materialize_frozen_trial_row",
    "load_attempt_events",
    "validate_raw_artifact",
    "verify_evidence_reference",
    "verify_evidence_references",
]
