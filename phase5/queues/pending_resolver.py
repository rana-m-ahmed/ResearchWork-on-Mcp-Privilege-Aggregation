"""Fail-closed resume resolution for frozen targets.

The resolver only reasons about immutable target keys, accepted attempts, and
lineage records. It does not peek at outcomes or alter the frozen ordering.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable, Sequence

from ..domain.errors import SchemaInvariantError


@dataclass(frozen=True, slots=True)
class CheckpointHistory:
    target_key: str
    attempt_index: int
    checkpoint_hash: str
    parent_checkpoint_hash: str | None
    chain_id: str
    accepted: bool = False
    orphaned: bool = False
    batch_artifact_id: str | None = None
    run_id: str | None = None


@dataclass(frozen=True, slots=True)
class OrphanRegistryEntry:
    target_key: str
    next_attempt_index: int
    rerun_link: str
    chain_id: str | None = None


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    target_key: str
    status: str
    next_attempt_index: int
    accepted_attempt_index: int | None
    chain_id: str | None
    note: str | None = None


@dataclass(frozen=True, slots=True)
class PendingResolution:
    resolved_targets: tuple[ResolvedTarget, ...]

    @property
    def accepted_targets(self) -> tuple[ResolvedTarget, ...]:
        return tuple(item for item in self.resolved_targets if item.status == "accepted")

    @property
    def orphan_targets(self) -> tuple[ResolvedTarget, ...]:
        return tuple(item for item in self.resolved_targets if item.status == "orphan")

    @property
    def pending_targets(self) -> tuple[ResolvedTarget, ...]:
        return tuple(item for item in self.resolved_targets if item.status == "pending")

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted_targets": [item.target_key for item in self.accepted_targets],
            "orphan_targets": [item.target_key for item in self.orphan_targets],
            "pending_targets": [item.target_key for item in self.pending_targets],
            "resolved_targets": [
                {
                    "accepted_attempt_index": item.accepted_attempt_index,
                    "chain_id": item.chain_id,
                    "next_attempt_index": item.next_attempt_index,
                    "note": item.note,
                    "status": item.status,
                    "target_key": item.target_key,
                }
                for item in self.resolved_targets
            ],
        }


def _group_histories(histories: Iterable[CheckpointHistory]) -> dict[str, list[CheckpointHistory]]:
    grouped: dict[str, list[CheckpointHistory]] = defaultdict(list)
    for history in histories:
        if not history.target_key:
            raise SchemaInvariantError("checkpoint history target_key cannot be empty")
        if history.attempt_index < 0:
            raise SchemaInvariantError("checkpoint history attempt_index must be non-negative")
        grouped[history.target_key].append(history)
    return grouped


def _validate_histories(histories: Sequence[CheckpointHistory]) -> dict[str, list[CheckpointHistory]]:
    grouped = _group_histories(histories)
    for target_key, records in grouped.items():
        chain_ids = {record.chain_id for record in records}
        if len(chain_ids) > 1:
            raise SchemaInvariantError(f"divergent checkpoint histories detected for target {target_key!r}")
        accepted_count = sum(1 for record in records if record.accepted)
        if accepted_count > 1:
            raise SchemaInvariantError(f"duplicate accepted checkpoint histories detected for target {target_key!r}")
        if len({record.attempt_index for record in records}) != len(records):
            raise SchemaInvariantError(f"duplicate attempt indices detected for target {target_key!r}")
    return grouped


def resolve_pending_targets(
    target_keys: Sequence[str],
    *,
    histories: Sequence[CheckpointHistory] = (),
    orphan_registry: Sequence[OrphanRegistryEntry] = (),
    accepted_target_keys: Iterable[str] = (),
) -> PendingResolution:
    """Resolve each target into accepted, orphan, or pending status.

    The function fails closed if the checkpoint history diverges or if the
    same target is marked accepted more than once.
    """

    target_keys = tuple(target_keys)
    orphan_registry = tuple(orphan_registry)
    accepted_target_keys = tuple(accepted_target_keys)

    if len(set(target_keys)) != len(target_keys):
        raise SchemaInvariantError("target keys must be unique within a batch plan")

    accepted_set = set(accepted_target_keys)
    if len(accepted_set) != len(accepted_target_keys):
        raise SchemaInvariantError("accepted target keys must be unique")

    grouped_histories = _validate_histories(histories)
    orphan_map = {entry.target_key: entry for entry in orphan_registry}
    if len(orphan_map) != len(orphan_registry):
        raise SchemaInvariantError("orphan registry target keys must be unique")

    resolved: list[ResolvedTarget] = []
    for target_key in target_keys:
        target_histories = grouped_histories.get(target_key, [])
        accepted_histories = [record for record in target_histories if record.accepted]
        latest_attempt_index = max((record.attempt_index for record in target_histories), default=-1)
        chain_id = target_histories[0].chain_id if target_histories else None

        if target_key in accepted_set:
            accepted_attempt_index = max(
                (record.attempt_index for record in accepted_histories),
                default=max(latest_attempt_index, 0),
            )
            resolved.append(
                ResolvedTarget(
                    target_key=target_key,
                    status="accepted",
                    next_attempt_index=accepted_attempt_index + 1,
                    accepted_attempt_index=accepted_attempt_index,
                    chain_id=chain_id,
                    note="accepted target preserved and not reselected",
                )
            )
            continue

        orphan_entry = orphan_map.get(target_key)
        if orphan_entry is not None:
            next_attempt_index = max(latest_attempt_index + 1, orphan_entry.next_attempt_index)
            resolved.append(
                ResolvedTarget(
                    target_key=target_key,
                    status="orphan",
                    next_attempt_index=next_attempt_index,
                    accepted_attempt_index=None,
                    chain_id=orphan_entry.chain_id or chain_id,
                    note=orphan_entry.rerun_link,
                )
            )
            continue

        resolved.append(
            ResolvedTarget(
                target_key=target_key,
                status="pending",
                next_attempt_index=max(latest_attempt_index + 1, 0),
                accepted_attempt_index=None,
                chain_id=chain_id,
                note="pending target selected from frozen manifest",
            )
        )

    return PendingResolution(resolved_targets=tuple(resolved))
