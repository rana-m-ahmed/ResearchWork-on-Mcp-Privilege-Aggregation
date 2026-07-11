from __future__ import annotations

import json
from pathlib import Path

from phase5.kaggle.phase5_official_qualification import (
    CANDIDATE_REF,
    MODEL_SLOTS,
    NOTEBOOK,
    NONOFFICIAL_BRANCH,
    QUALIFICATION_ID,
    NotebookParameters,
    build_notebook_payload,
    write_notebook,
)


SCRATCH = Path(".test_scratch") / "phase5_local_qualification"


def test_notebook_payload_has_no_placeholders() -> None:
    payload = build_notebook_payload(
        NotebookParameters(
            repo_url="https://example.invalid/repo.git",
            candidate_ref=CANDIDATE_REF,
            expected_source_commit="abc123",
            model_slots=MODEL_SLOTS,
            evidence_branch=NONOFFICIAL_BRANCH,
            qualification_id=QUALIFICATION_ID,
            official_trial=False,
            counts_for_phase5=False,
            publication_evidence=False,
            synthetic_fixture=True,
            checkpoint_threshold=1,
            safe_session_hours=1,
        )
    )
    text = json.dumps(payload)
    assert "<RUN_ID>" not in text
    assert "<YYYYMMDD>" not in text
    assert "<SYNC_MANIFEST_PATH>" not in text
    assert "<SYNC_RECEIPT_PATH>" not in text
    assert "<CANARY_BATCH_ID>" not in text
    assert "Repository commands would be invoked here" not in text
    assert "Thin notebook architecture confirmed" not in text
    assert "c31eecfa1fd05eb6da65c7e4be355c24533183e5" not in text
    assert "20260710" not in text


def test_notebook_payload_is_nonofficial_and_executable() -> None:
    payload = build_notebook_payload(
        NotebookParameters(
            repo_url="https://example.invalid/repo.git",
            candidate_ref=CANDIDATE_REF,
            expected_source_commit="abc123",
            model_slots=MODEL_SLOTS,
            evidence_branch=NONOFFICIAL_BRANCH,
            qualification_id=QUALIFICATION_ID,
            official_trial=False,
            counts_for_phase5=False,
            publication_evidence=False,
            synthetic_fixture=True,
            checkpoint_threshold=1,
            safe_session_hours=1,
        )
    )
    text = json.dumps(payload)
    assert "def run_checked(command" in text
    assert "resolved_model_authority.json" in text
    assert "model_generation_evidence.json" in text
    assert "decoded_generation_transcripts.json" in text
    assert "write_ahead_durability_evidence.json" in text
    assert "source_reverification_receipt.json" in text
    assert "raw_model_output" in text
    assert "parsed_model_request" in text
    assert "UserSecretsClient" in text
    assert "resolve_hf_token" in text
    assert "load_model_with_compat" in text
    assert "torch_dtype" in text
    assert "phase5_i17e_genuine_kaggle_qualification_bundle.zip" in text
    assert "official_trial" in text
    assert "counts_for_phase5" in text
    assert "publication_evidence" in text
    assert "synthetic_fixture" in text


def test_notebook_write_round_trip() -> None:
    SCRATCH.mkdir(parents=True, exist_ok=True)
    notebook = SCRATCH / "phase5.ipynb"
    write_notebook(
        notebook,
        NotebookParameters(
            repo_url="https://example.invalid/repo.git",
            candidate_ref=CANDIDATE_REF,
            expected_source_commit="abc123",
            model_slots=MODEL_SLOTS,
            evidence_branch=NONOFFICIAL_BRANCH,
            qualification_id=QUALIFICATION_ID,
            official_trial=False,
            counts_for_phase5=False,
            publication_evidence=False,
            synthetic_fixture=True,
            checkpoint_threshold=1,
            safe_session_hours=1,
        ),
    )
    data = json.loads(notebook.read_text(encoding="utf-8"))
    assert data["nbformat"] == 4
    assert data["cells"]


def test_notebook_path_defined() -> None:
    assert NOTEBOOK.name == "phase5_official_qualification.ipynb"
