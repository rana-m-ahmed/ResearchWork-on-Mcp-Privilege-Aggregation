from __future__ import annotations

import copy

import pytest

from phase5.domain import (
    AcceptedAttemptRecord,
    AttackFamily,
    DefenseCondition,
    Density,
    FrozenRowId,
    FrozenTrialRow,
    MetadataSurfaceCondition,
    ModelSlot,
    PayloadCondition,
    SessionState,
    TrialAssessment,
    TrialOutcome,
    TrialPhase,
    validate_hash_immutability,
    validate_primary_outcome,
    validate_session_execution_allowed,
    validate_single_accepted_attempt,
    validate_trial_row,
)
from phase5.domain.errors import DuplicateAcceptedAttemptError, FrozenArtifactHashError, ProhibitedAliasError, SchemaInvariantError


def _base_row() -> dict[str, object]:
    return {
        "phase": "phase5_adversarial_core",
        "official_trial": False,
        "trial_id": "kaggle-01",
        "run_id": "phase4_5_kaggle_real_smoke_run",
        "branch": "phase5-model-1",
        "git_commit_hash": "3a92c2d7e2987290b801cee95ae3c506254ff8f6",
        "timestamp_utc": "2026-07-05T12:40:35.067749+00:00",
        "model_id": "M1",
        "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
        "model_digest": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "quantization": "float16",
        "backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "ollama_version": None,
        "density": "D3",
        "metadata_surface_condition": "POISON_TD",
        "attack_family": "DIRECT_OVERRIDE",
        "defense_condition": "BASELINE",
        "payload_id": "kaggle_smoke_01",
        "phase1_payload_hash": "b913d5ae30d568588539ee592a978420358a31f42263b8d7571e31ef0e7ab4c6",
        "payload_hash": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "adversarial_payload_present": True,
        "payload_condition": "PHASE1_HASH_AUTHORIZED",
    }


def test_frozen_trial_row_parses_valid_mapping() -> None:
    row = FrozenTrialRow.from_mapping(_base_row())
    assert row.model_id is ModelSlot.M1
    assert row.density is Density.D3
    assert row.metadata_surface_condition is MetadataSurfaceCondition.POISON_TD
    assert row.payload_condition is PayloadCondition.PHASE1_HASH_AUTHORIZED
    validate_trial_row(row)


def test_prohibited_aliases_fail_closed() -> None:
    mapping = _base_row()
    mapping.pop("metadata_surface_condition")
    mapping["metadata_condition"] = "POISON_TD"

    with pytest.raises(ProhibitedAliasError):
        FrozenTrialRow.from_mapping(mapping)


def test_utility_null_semantics_pass_and_fail() -> None:
    utility = _base_row()
    utility.update(
        {
            "phase": "phase5_utility_preservation",
            "density": "D5",
            "metadata_surface_condition": "CLEAN",
            "attack_family": "NONE",
            "adversarial_payload_present": False,
            "phase1_payload_hash": None,
            "payload_hash": None,
            "payload_condition": "NONE",
        }
    )
    row = FrozenTrialRow.from_mapping(utility)
    assert row.phase is TrialPhase.PHASE5_UTILITY_PRESERVATION
    assert row.attack_family is AttackFamily.NONE
    assert row.metadata_surface_condition is MetadataSurfaceCondition.CLEAN
    assert row.phase1_payload_hash is None
    assert row.payload_hash is None

    broken = copy.deepcopy(utility)
    broken["payload_hash"] = "sha256:AUTHENTIC_KAGGLE_EXECUTION"
    with pytest.raises(SchemaInvariantError):
        FrozenTrialRow.from_mapping(broken)


def test_d1_primary_outcome_invariant_blocks_exploit_labels() -> None:
    validate_primary_outcome(TrialAssessment(density=Density.D3, outcome=TrialOutcome.ATTACK_SUCCESS))

    with pytest.raises(SchemaInvariantError):
        validate_primary_outcome(TrialAssessment(density=Density.D1, outcome=TrialOutcome.ATTACK_SUCCESS))

    with pytest.raises(SchemaInvariantError):
        validate_primary_outcome(TrialAssessment(density=Density.D1, outcome=TrialOutcome.CRITICAL_EXPLOIT))


def test_single_accepted_attempt_invariant_rejects_duplicates() -> None:
    records = [
        AcceptedAttemptRecord(target_frozen_row_id=FrozenRowId.parse("row_001"), attempt_id="a1", accepted_attempt=True),
        AcceptedAttemptRecord(target_frozen_row_id=FrozenRowId.parse("row_001"), attempt_id="a2", accepted_attempt=True),
    ]

    with pytest.raises(DuplicateAcceptedAttemptError):
        validate_single_accepted_attempt(records)


def test_hash_immutability_blocks_mutation() -> None:
    reference = {"phase4_go": "97927A12B707D65985C3DB66890DD1C8BE28D94009B5469F8A93379878DD729A"}
    validate_hash_immutability(reference, dict(reference))

    with pytest.raises(FrozenArtifactHashError):
        validate_hash_immutability(reference, {"phase4_go": "0" * 64})


def test_execution_allowed_only_in_sealed_state() -> None:
    validate_session_execution_allowed(SessionState.SEALED)

    with pytest.raises(SchemaInvariantError):
        validate_session_execution_allowed(SessionState.UNSEALED_SYNCED)
