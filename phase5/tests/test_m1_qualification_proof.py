from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from phase5.domain.errors import SchemaInvariantError
from phase5.domain.identifiers import AttemptId
from phase5.runtime.official_execution import frozen_row_key
from phase5.runtime.qualification_proof import run_m1_shared_engine_proof


DATASET = "P5-DV-1.0.1-A7C91E42"
RUN_ID = f"P5RUN-{DATASET}-M1-20260712-ABCDEF12"


def _root_with_authority(tmp_path: Path) -> Path:
    source = Path(__file__).resolve().parents[1] / "configs/synthetic_m1_proof_v1.json"
    target = tmp_path / "phase5/configs/synthetic_m1_proof_v1.json"
    target.parent.mkdir(parents=True)
    shutil.copyfile(source, target)
    (tmp_path / "phase5/fixtures").mkdir(parents=True)
    return tmp_path


class _FakeEngine:
    init: dict[str, object] = {}

    def __init__(self, **kwargs: object) -> None:
        type(self).init = kwargs
        self.evidence_root = Path(kwargs["evidence_root"])

    def execute_row(self, *, row, batch, run_id, attempt_index, parent_attempt_id):
        attempt_id = str(AttemptId.build(row.trial_id, attempt_index, batch.run_token))
        attempt_root = self.evidence_root / "attempts" / attempt_id
        attempt_root.mkdir(parents=True)
        tool_path = row.task_id.endswith("TOOL")
        events = [
            "PREPARED", "DISPATCHED", "MODEL_OUTPUT_CAPTURED", "PARSE_COMPLETED",
            "TURN_COMPLETED", "TERMINATED", "RESET_CHECKED", "GRADED",
            "TRIAL_ROW_MATERIALIZED", "FINALIZED",
        ]
        if tool_path:
            events[4:4] = ["TOOL_EVENT", "TOOL_RESULT_CAPTURED"]
        (attempt_root / "attempt_events.jsonl").write_text(
            "".join(json.dumps({
                "event_id": f"P5EVT-{attempt_id}-{index:04d}", "dataset_version": DATASET,
                "frozen_row_id": frozen_row_key(row), "target_trial_id": str(row.trial_id),
                "attempt_id": attempt_id, "run_id": run_id, "batch_id": batch.batch_id,
                "event_sequence": index, "event_type": event, "timestamp_utc": "2026-07-12T00:00:00+00:00",
                "artifact_ref": None, "artifact_sha256": None, "details": {},
            }) + "\n" for index, event in enumerate(events, 1)), encoding="utf-8",
        )
        outputs = 2 if tool_path else 1
        (attempt_root / "model_outputs.jsonl").write_text(
            "".join(json.dumps({"generation_receipt": {"generated_token_ids": [1]}}) + "\n" for _ in range(outputs)),
            encoding="utf-8",
        )
        (attempt_root / "tool_transcript.jsonl").write_text(
            json.dumps({"exposed_tool_name": "read_internal_notes"}) + "\n" if tool_path else "",
            encoding="utf-8",
        )
        for name in ("hardware_snapshot.json", "model_load_placement.json", "grader_evidence.json", "tid_evidence.json"):
            (attempt_root / name).write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            acceptance_proof=object(), qualification_accepted=True, invalid_reason=None,
            raw_attempt_directory=attempt_root, frozen_row_id=frozen_row_key(row),
            target_trial_id=str(row.trial_id), attempt_id=attempt_id,
            attempt_index=attempt_index, parent_attempt_id=parent_attempt_id,
        )


def test_proof_isolated_nonofficial_and_links_orphan_replacement(tmp_path: Path) -> None:
    root = _root_with_authority(tmp_path)
    receipt = run_m1_shared_engine_proof(
        root=root, dataset_version=DATASET, run_id=RUN_ID, engine_factory=_FakeEngine,
    )
    assert receipt["status"] == "PASS"
    assert receipt["official_trials"] == receipt["official_accepted_trials"] == 0
    assert receipt["replacement_attempt_id"].endswith("-A001-ABCDEF12")
    assert _FakeEngine.init["official_trial"] is False
    assert "proof_runs" in str(_FakeEngine.init["evidence_root"])


def test_proof_rejects_dataset_authority_mismatch(tmp_path: Path) -> None:
    root = _root_with_authority(tmp_path)
    with pytest.raises(SchemaInvariantError, match="authority does not match"):
        run_m1_shared_engine_proof(
            root=root, dataset_version="P5-DV-1.0.2-A7C91E42", run_id=RUN_ID,
            engine_factory=_FakeEngine,
        )
