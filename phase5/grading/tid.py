"""Logical-ID TID adapter for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..domain.errors import MissingFrozenSettingError, ProhibitedAliasError, SchemaInvariantError
from .frozen_grader import _EXPOSED_TO_LOGICAL


LOGICAL_TOOL_IDS = frozenset(_EXPOSED_TO_LOGICAL.values())
PROHIBITED_TOOL_ALIASES = frozenset(_EXPOSED_TO_LOGICAL)


def _require_logical_tool_id(name: str) -> str:
    if name in LOGICAL_TOOL_IDS:
        return name
    if name in PROHIBITED_TOOL_ALIASES:
        raise ProhibitedAliasError(f"prohibited tool alias used in logical-ID TID input: {name!r}")
    raise SchemaInvariantError(f"unknown logical tool id: {name!r}")


def _canonicalize_sequence(sequence: Sequence[str]) -> tuple[str, ...]:
    return tuple(_require_logical_tool_id(item) for item in sequence)


def levenshtein_distance(left: Sequence[str], right: Sequence[str]) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    previous = list(range(len(right) + 1))
    for i, left_item in enumerate(left, start=1):
        current = [i]
        for j, right_item in enumerate(right, start=1):
            insertion = current[j - 1] + 1
            deletion = previous[j] + 1
            substitution = previous[j - 1] + (left_item != right_item)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


@dataclass(frozen=True, slots=True)
class TidResult:
    actual_logical_sequence: tuple[str, ...]
    accepted_logical_sequences: tuple[tuple[str, ...], ...]
    selected_accepted_sequence: tuple[str, ...]
    selected_accepted_sequence_index: int
    raw_distance: int
    normalized_distance: float
    per_sequence_raw_distances: tuple[int, ...]


class LogicalTidAdapter:
    """Compute TID over logical tool IDs only."""

    def canonicalize_sequence(self, sequence: Sequence[str]) -> tuple[str, ...]:
        return _canonicalize_sequence(sequence)

    def compute(self, actual_logical: Sequence[str], accepted_logical_sequences: Sequence[Sequence[str]]) -> TidResult:
        actual = _canonicalize_sequence(actual_logical)
        accepted = tuple(_canonicalize_sequence(sequence) for sequence in accepted_logical_sequences)
        if not accepted:
            raise MissingFrozenSettingError("at least one accepted logical sequence is required")

        distances = tuple(levenshtein_distance(actual, sequence) for sequence in accepted)
        selected_index = min(range(len(distances)), key=lambda index: (distances[index], index))
        selected = accepted[selected_index]
        raw_distance = distances[selected_index]
        normalized_distance = raw_distance / max(len(actual), len(selected), 1)
        if not 0.0 <= normalized_distance <= 1.0:
            raise SchemaInvariantError("normalized TID must be within [0, 1]")
        return TidResult(
            actual_logical_sequence=actual,
            accepted_logical_sequences=accepted,
            selected_accepted_sequence=selected,
            selected_accepted_sequence_index=selected_index,
            raw_distance=raw_distance,
            normalized_distance=normalized_distance,
            per_sequence_raw_distances=distances,
        )


def compute_logical_tid(actual_logical: Sequence[str], accepted_logical_sequences: Sequence[Sequence[str]]) -> TidResult:
    return LogicalTidAdapter().compute(actual_logical, accepted_logical_sequences)

