from __future__ import annotations

from pathlib import Path

from phase5.domain import (
    AcceptedAttemptRecord,
    FrozenRowId,
    Phase5Session,
    SessionState,
    TrialAssessment,
    TrialOutcome,
    TrialPhase,
    Density,
)
from phase5.validation import (
    lint_accepted_attempts,
    lint_execution_allowed,
    lint_hash_immutability,
    lint_primary_outcome,
    lint_required_frozen_inputs,
    lint_session_transition,
    lint_trial_row_mapping,
)


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


def test_protocol_lint_accepts_valid_row_and_registry_labels() -> None:
    assert lint_trial_row_mapping(_base_row()) == []
    assert lint_required_frozen_inputs(["Phase 4 GO report", "Phase 4.5 GO report"]) == []


def test_protocol_lint_rejects_aliases_and_unknown_labels() -> None:
    bad_row = _base_row()
    bad_row.pop("metadata_surface_condition")
    bad_row["metadata_condition"] = "POISON_TD"
    assert lint_trial_row_mapping(bad_row)

    issues = lint_required_frozen_inputs(["missing label"])
    assert issues and "missing label" in issues[0]


def test_protocol_lint_detects_d1_exploit_and_duplicate_acceptance() -> None:
    assert lint_primary_outcome(Density.D1, TrialOutcome.ATTACK_SUCCESS)
    assert lint_accepted_attempts(
        [
            AcceptedAttemptRecord(target_frozen_row_id=FrozenRowId.parse("row_001"), attempt_id="a1", accepted_attempt=True),
            AcceptedAttemptRecord(target_frozen_row_id=FrozenRowId.parse("row_001"), attempt_id="a2", accepted_attempt=True),
        ]
    )


def test_protocol_lint_detects_sync_and_hash_failures() -> None:
    assert lint_execution_allowed(SessionState.UNSEALED_SYNCED)
    assert lint_hash_immutability({"k": "v"}, {"k": "changed"})
    assert lint_session_transition(Phase5Session.initial())
