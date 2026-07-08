"""Phase 5 evidence primitives."""

from __future__ import annotations

from .archive_index import ArchiveIndex, ArchiveIndexEntry, build_archive_index
from .artifacts import ContentAddressedArtifactWriter, RawArtifactRecord, validate_raw_artifact
from .events import AttemptEvent, AttemptEventLogWriter, AttemptEventType, load_attempt_events
from .manifest_builder import (
    AttemptFinalizationRecord,
    BatchFinalizationInput,
    BatchManifest,
    FinalizationBundle,
    RunManifest,
    build_accepted_row_jsonl,
    build_finalization_bundle,
)
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
    "ArchiveIndex",
    "ArchiveIndexEntry",
    "AttemptEvent",
    "AttemptEventLogWriter",
    "AttemptEventType",
    "AttemptFinalizationRecord",
    "BatchFinalizationInput",
    "BatchManifest",
    "AttemptWorkspaceMetadata",
    "ContentAddressedArtifactWriter",
    "EvidenceReference",
    "FinalizationBundle",
    "MaterializedTrialRow",
    "RawArtifactRecord",
    "RunManifest",
    "VerifiedEvidenceReference",
    "build_accepted_row_jsonl",
    "build_archive_index",
    "build_finalization_bundle",
    "materialize_frozen_trial_row",
    "load_attempt_events",
    "validate_raw_artifact",
    "verify_evidence_reference",
    "verify_evidence_references",
]
