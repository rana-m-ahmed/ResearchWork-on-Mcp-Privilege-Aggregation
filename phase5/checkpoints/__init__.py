"""Checkpoint contracts for Phase 5 finalization."""

from __future__ import annotations

from .schema import (
    CHECKPOINT_SCHEMA_PATH,
    CheckpointRecord,
    FINALIZATION_STATUS_FINALIZED_NOT_SYNCED,
    build_checkpoint_record,
    load_checkpoint_schema,
    validate_checkpoint_record,
    validate_continuation_authorization,
)

__all__ = [
    "CHECKPOINT_SCHEMA_PATH",
    "CheckpointRecord",
    "FINALIZATION_STATUS_FINALIZED_NOT_SYNCED",
    "build_checkpoint_record",
    "load_checkpoint_schema",
    "validate_checkpoint_record",
    "validate_continuation_authorization",
]
