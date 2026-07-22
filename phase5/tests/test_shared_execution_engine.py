from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from phase5.queues.frozen_queue_loader import load_frozen_queue_bundle
from phase5.runtime.engine import SharedExecutionEngine


def test_execute_row_builds_frozen_workspace_and_resolves_task(monkeypatch, tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    row = next(
        row
        for queue in load_frozen_queue_bundle(root=repository_root).queues()
        for row in queue.rows
        if row.model_id.value == "M1"
    )
    source_registry = json.loads(
        (repository_root / "phase5/manifests/frozen_task_content_registry_v2.json").read_text(encoding="utf-8")
    )
    task_entry = next(entry for entry in source_registry if entry["task_id"] == row.task_id)
    registry_path = tmp_path / "phase5/manifests/frozen_task_content_registry_v2.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps([task_entry]), encoding="utf-8")

    engine = object.__new__(SharedExecutionEngine)
    engine.root = tmp_path
    engine.attempts_root = tmp_path / "phase5/attempts"
    engine.evidence_root = tmp_path / "phase5/evidence"
    engine.dataset_version = "P5-DV-1.0.2-A7C91E42"
    engine.synthetic_fixture = True
    engine.official_trial = False
    engine.counts_for_phase5 = False
    engine.publication_evidence = False
    engine.controls = object()
    engine.model_identity = SimpleNamespace(
        model_id="M1",
        exact_model_identifier="Qwen/Qwen2.5-7B-Instruct",
        model_digest="sha256:SYNTHETIC_FIXTURE",
        quantization="float16",
        backend="transformers",
        backend_version="transformers==5.0.0",
        ollama_version=None,
    )
    engine.backend = object()
    engine.tokenizer = object()
    monkeypatch.setattr(engine, "_ensure_loaded", lambda: None)

    captured: dict[str, object] = {}

    def fake_loop(**kwargs):
        captured.update(kwargs)
        expected_tool = task_entry["canonical_task_content"]["expected_sequence"][0]
        (kwargs["workspace"].workspace_root / "tool_transcript.jsonl").write_text(
            json.dumps({"exposed_tool_name": expected_tool}) + "\n",
            encoding="utf-8",
        )
        for name in (
            "grade_callable",
            "tid_callable",
            "materialize_callable",
            "validate_callable",
            "finalize_callable",
            "lineage_callable",
        ):
            kwargs[name]()
        kwargs["workspace"].metadata.event_log_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(elapsed_seconds=1.0, status="PASS", termination_reason="accept")

    monkeypatch.setattr("phase5.runtime.engine.run_frozen_agent_loop", fake_loop)
    monkeypatch.setattr("phase5.runtime.engine.load_reset_failure_retry_limit", lambda root: 0)
    monkeypatch.setattr(
        "phase5.runtime.engine.subprocess.check_output",
        lambda *args, **kwargs: "a" * 40 + "\n",
    )
    batch = SimpleNamespace(
        run_token="ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.2-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
    )
    result = engine.execute_row(
        row=row,
        batch=batch,
        run_id="P5RUN-P5-DV-1.0.2-A7C91E42-M1-20260711-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
    )

    workspace = captured["workspace"]
    reset_executor = captured["reset_executor"]
    assert reset_executor.workspace is workspace
    assert captured["task_description"] == task_entry["canonical_task_content"]["description"]
    assert captured["frozen_row"].phase.value == "phase5_adversarial_core"
    assert captured["frozen_row"].trial_id == row.trial_id
    assert workspace.metadata.dataset_version == engine.dataset_version
    assert result.raw_attempt_directory == workspace.workspace_root
    assert result.target_trial_id == str(row.trial_id)
    assert isinstance(result.target_trial_id, str)
    assert result.acceptance_proof.event_log_sha256 != "0" * 64
    manifest = json.loads(workspace.metadata.manifest_path.read_text(encoding="utf-8"))
    assert manifest["attempt_status"] == "SYNTHETIC_QUALIFIED"


def test_failed_pretrial_manifest_is_finalized_before_hash_sealing(monkeypatch, tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[2]
    row = next(
        row
        for queue in load_frozen_queue_bundle(root=repository_root).queues()
        for row in queue.rows
        if row.model_id.value == "M1"
    )
    source_registry = json.loads(
        (repository_root / "phase5/manifests/frozen_task_content_registry_v2.json").read_text(encoding="utf-8")
    )
    task_entry = next(entry for entry in source_registry if entry["task_id"] == row.task_id)
    registry_path = tmp_path / "phase5/manifests/frozen_task_content_registry_v2.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(json.dumps([task_entry]), encoding="utf-8")
    bindings_path = tmp_path / "phase5_5/configs/task_argument_bindings_v1.json"
    bindings_path.parent.mkdir(parents=True)
    bindings_path.write_bytes(
        (repository_root / "phase5_5/configs/task_argument_bindings_v1.json").read_bytes()
    )

    engine = object.__new__(SharedExecutionEngine)
    engine.root = tmp_path
    engine.attempts_root = tmp_path / "phase5_5/attempts"
    engine.evidence_root = tmp_path / "phase5_5/evidence"
    engine.dataset_version = "P5-DV-1.0.2-A7C91E42"
    engine.synthetic_fixture = False
    engine.pretrial_mode = True
    engine.official_trial = False
    engine.counts_for_phase5 = False
    engine.publication_evidence = False
    engine.controls = object()
    engine.model_identity = SimpleNamespace(
        model_id="M1",
        exact_model_identifier="Qwen/Qwen2.5-7B-Instruct",
        model_digest="sha256:SYNTHETIC_FIXTURE",
        quantization="float16",
        backend="transformers",
        backend_version="transformers==5.0.0",
        ollama_version=None,
    )
    engine.backend = object()
    engine.tokenizer = object()
    monkeypatch.setattr(engine, "_ensure_loaded", lambda: None)

    captured: dict[str, object] = {}

    def fake_loop(**kwargs):
        captured.update(kwargs)
        (kwargs["workspace"].workspace_root / "tool_transcript.jsonl").write_text("", encoding="utf-8")
        for name in (
            "grade_callable",
            "tid_callable",
            "materialize_callable",
            "validate_callable",
            "finalize_callable",
            "lineage_callable",
        ):
            kwargs[name]()
        kwargs["workspace"].metadata.event_log_path.write_text("{}\n", encoding="utf-8")
        return SimpleNamespace(
            elapsed_seconds=1.0,
            status="FAIL",
            termination_reason="reject",
            termination_state="S12",
            evidence_ready=True,
            notes=("NO_INVOCATION_FOUND",),
        )

    monkeypatch.setattr("phase5.runtime.engine.run_frozen_agent_loop", fake_loop)
    monkeypatch.setattr("phase5.runtime.engine.load_reset_failure_retry_limit", lambda root: 0)
    monkeypatch.setattr(
        "phase5.runtime.engine.subprocess.check_output",
        lambda *args, **kwargs: "a" * 40 + "\n",
    )
    batch = SimpleNamespace(
        run_token="ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.2-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
    )

    result = engine.execute_row(
        row=row,
        batch=batch,
        run_id="P5RUN-P5-DV-1.0.2-A7C91E42-M1-20260711-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
    )

    workspace = captured["workspace"]
    manifest = json.loads(workspace.metadata.manifest_path.read_text(encoding="utf-8"))
    assert result.analysis_eligible is True
    assert result.qualification_accepted is False
    assert manifest["attempt_status"] == "PRETRIAL_INVALID"
    hash_index = [json.loads(line) for line in workspace.metadata.artifact_index_path.read_text(encoding="utf-8").splitlines()]
    manifest_hash = next(item["sha256"] for item in hash_index if item["path"] == "attempt_manifest.json")
    assert manifest_hash == hashlib.sha256(workspace.metadata.manifest_path.read_bytes()).hexdigest()
