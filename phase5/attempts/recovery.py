"""Orphan discovery and replacement planning."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..domain.errors import SchemaInvariantError
from ..domain.identifiers import AttemptId
from ..evidence.events import AttemptEventType, load_attempt_events
from ..evidence.workspace import AttemptWorkspaceMetadata
from .lineage import AttemptLineageRecord


@dataclass(frozen=True, slots=True)
class OrphanAttempt:
    workspace: AttemptWorkspaceMetadata
    last_event_type: AttemptEventType
    last_event_sequence: int

    @property
    def attempt_id(self) -> str:
        return self.workspace.attempt_id


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    orphan_attempts: tuple[OrphanAttempt, ...]
    replacement_workspaces: tuple[AttemptWorkspaceMetadata, ...]
    replacement_lineage_records: tuple[AttemptLineageRecord, ...]


def discover_orphan_attempts(workspaces: Sequence[AttemptWorkspaceMetadata]) -> tuple[OrphanAttempt, ...]:
    orphaned: list[OrphanAttempt] = []
    for workspace in workspaces:
        events = load_attempt_events(workspace.event_log_path)
        if not events:
            continue
        last_event = events[-1]
        if any(event.event_type is AttemptEventType.DISPATCHED for event in events) and all(
            event.event_type is not AttemptEventType.FINALIZED for event in events
        ):
            orphaned.append(
                OrphanAttempt(
                    workspace=workspace,
                    last_event_type=last_event.event_type,
                    last_event_sequence=last_event.event_sequence,
                )
            )
    return tuple(orphaned)


def build_replacement_workspace(
    orphan: OrphanAttempt,
    *,
    base_attempts_root: Path,
    base_evidence_root: Path,
    session_token: str,
    created_utc: str,
    attempt_status: str = "PENDING",
) -> AttemptWorkspaceMetadata:
    next_attempt_index = orphan.workspace.attempt_index + 1
    replacement_attempt_id = str(AttemptId.build(orphan.workspace.target_trial_id, next_attempt_index, session_token))
    return AttemptWorkspaceMetadata.build(
        base_attempts_root=base_attempts_root,
        base_evidence_root=base_evidence_root,
        dataset_version=orphan.workspace.dataset_version,
        frozen_row_id=orphan.workspace.frozen_row_id,
        target_trial_id=orphan.workspace.target_trial_id,
        attempt_id=replacement_attempt_id,
        attempt_index=next_attempt_index,
        parent_attempt_id=orphan.workspace.attempt_id,
        run_id=orphan.workspace.run_id,
        batch_id=orphan.workspace.batch_id,
        attempt_status=attempt_status,
        created_utc=created_utc,
    )


def build_replacement_lineage_record(
    workspace: AttemptWorkspaceMetadata,
    *,
    attempt_status: str = "PENDING",
    invalid_reason: str | None = None,
    counts_toward_cell_n: bool = False,
    accepted_attempt: bool = False,
) -> AttemptLineageRecord:
    if not workspace.parent_attempt_id:
        raise SchemaInvariantError("replacement attempts require a parent_attempt_id")
    return AttemptLineageRecord(
        dataset_version=workspace.dataset_version,
        frozen_row_id=workspace.frozen_row_id,
        target_trial_id=workspace.target_trial_id,
        attempt_id=workspace.attempt_id,
        attempt_index=workspace.attempt_index,
        parent_attempt_id=workspace.parent_attempt_id,
        run_id=workspace.run_id,
        batch_id=workspace.batch_id,
        attempt_status=attempt_status,
        invalid_reason=invalid_reason,
        counts_toward_cell_n=counts_toward_cell_n,
        accepted_attempt=accepted_attempt,
        raw_attempt_directory=workspace.raw_attempt_directory,
    )


def build_recovery_plan(
    workspaces: Sequence[AttemptWorkspaceMetadata],
    *,
    base_attempts_root: Path,
    base_evidence_root: Path,
    session_token: str,
    created_utc: str,
) -> RecoveryPlan:
    orphans = discover_orphan_attempts(workspaces)
    replacement_workspaces = tuple(
        build_replacement_workspace(
            orphan,
            base_attempts_root=base_attempts_root,
            base_evidence_root=base_evidence_root,
            session_token=session_token,
            created_utc=created_utc,
        )
        for orphan in orphans
    )
    replacement_lineage_records = tuple(build_replacement_lineage_record(workspace) for workspace in replacement_workspaces)
    return RecoveryPlan(
        orphan_attempts=orphans,
        replacement_workspaces=replacement_workspaces,
        replacement_lineage_records=replacement_lineage_records,
    )
