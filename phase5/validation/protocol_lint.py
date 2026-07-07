"""Protocol lint checks for the Phase 5 scaffold."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..domain.config import ArtifactRegistry, load_upstream_artifact_registry
from ..domain.enums import Density, SessionState, TrialOutcome
from ..domain.errors import Phase5Error, SchemaInvariantError
from ..domain.invariants import (
    AcceptedAttemptRecord,
    FrozenTrialRow,
    TrialAssessment,
    validate_hash_immutability,
    validate_primary_outcome,
    validate_session_execution_allowed,
    validate_single_accepted_attempt,
)
from ..domain.session import Phase5Session


def _coerce_density(value: Density | str) -> Density:
    return value if isinstance(value, Density) else Density.from_value(value)


def _coerce_outcome(value: TrialOutcome | str) -> TrialOutcome:
    return value if isinstance(value, TrialOutcome) else TrialOutcome.from_value(value)


def lint_trial_row_mapping(mapping: Mapping[str, Any]) -> list[str]:
    try:
        FrozenTrialRow.from_mapping(mapping)
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def lint_primary_outcome(density: Density | str, outcome: TrialOutcome | str) -> list[str]:
    try:
        validate_primary_outcome(TrialAssessment(density=_coerce_density(density), outcome=_coerce_outcome(outcome)))
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def lint_session_transition(session: Phase5Session, *, hashes_match: bool = True) -> list[str]:
    try:
        validate_session_execution_allowed(session.state)
        session.require_can_run_batch()
        if session.state is SessionState.UNSEALED_SYNCED:
            session.reverify_after_sync(hashes_match=hashes_match)
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def lint_required_frozen_inputs(
    labels: Iterable[str],
    *,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    expected_sha256: str | None = None,
) -> list[str]:
    try:
        current_registry = registry or load_upstream_artifact_registry(
            registry_path, expected_sha256=expected_sha256
        )
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]

    issues: list[str] = []
    for label in labels:
        try:
            current_registry.require(label)
        except Phase5Error as exc:
            issues.append(f"{label}: {exc.__class__.__name__}: {exc}")
    return issues


def lint_accepted_attempts(records: Sequence[AcceptedAttemptRecord]) -> list[str]:
    try:
        validate_single_accepted_attempt(records)
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def lint_hash_immutability(reference: Mapping[str, str], candidate: Mapping[str, str]) -> list[str]:
    try:
        validate_hash_immutability(reference, candidate)
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []


def lint_execution_allowed(state: SessionState) -> list[str]:
    try:
        validate_session_execution_allowed(state)
    except Phase5Error as exc:
        return [f"{exc.__class__.__name__}: {exc}"]
    return []
