"""Bounded non-official M1 shared-engine qualification proof."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..attempts import AttemptLineageRecord, AttemptLineageStore, build_recovery_plan
from ..campaign import CampaignBatchPlan
from ..domain.enums import (
    AttackFamily,
    DefenseCondition,
    Density,
    MetadataSurfaceCondition,
    ModelSlot,
    PayloadCondition,
    TrialPhase,
)
from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError
from ..domain.identifiers import AttemptId, BatchId, EventId, RunId, TrialId
from ..evidence import AttemptEvent, AttemptEventLogWriter, AttemptEventType
from ..evidence.events import load_attempt_events
from ..evidence.io import load_jsonl_records
from ..evidence.workspace import AttemptWorkspaceMetadata
from ..queues.frozen_queue_loader import FrozenQueueRow
from .engine import SharedExecutionEngine
from .official_execution import frozen_row_key
from .workspace_isolation import AttemptWorkspaceIsolation

PROOF_CONFIG = Path("phase5/configs/synthetic_m1_proof_v1.json")
PROOF_RECEIPT = Path("phase5/validation/m1_shared_engine_proof_run.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_authority(root: Path, dataset_version: str) -> tuple[dict[str, Any], str]:
    path = root / PROOF_CONFIG
    if not path.is_file():
        raise MissingFrozenSettingError(f"synthetic proof authority is missing: {path.as_posix()}")
    document = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "dataset_version": dataset_version,
        "model_slot": "M1",
        "official_trial": False,
        "counts_for_phase5": False,
        "publication_evidence": False,
        "synthetic_fixture": True,
    }
    if any(document.get(key) != value for key, value in required.items()):
        raise SchemaInvariantError("synthetic proof authority does not match the requested boundary")
    fixtures = document.get("fixtures")
    if not isinstance(fixtures, list) or {item.get("fixture_id") for item in fixtures} != {
        "P5SYN-M1-TERMINAL", "P5SYN-M1-TOOL"
    }:
        raise SchemaInvariantError("synthetic proof authority must contain exactly the terminal and tool fixtures")
    return document, _sha256(path)


def _build_row(item: dict[str, Any], config_path: Path, config_sha256: str, order: int) -> FrozenQueueRow:
    return FrozenQueueRow(
        queue_name="utility",
        order_index=order,
        trial_id=TrialId.parse(str(item["fixture_id"])),
        model_id=ModelSlot.M1,
        density=Density.D3,
        metadata_surface_condition=MetadataSurfaceCondition.CLEAN,
        attack_family=AttackFamily.NONE,
        defense_condition=DefenseCondition.BASELINE,
        payload_id="",
        phase1_payload_hash=None,
        task_id=str(item["fixture_id"]),
        task_hash=str(item["task_hash"]),
        payload_condition=PayloadCondition.NONE,
        status="PENDING",
        source_path=config_path,
        source_sha256=config_sha256,
    )


def _event(metadata: AttemptWorkspaceMetadata, sequence: int, event_type: AttemptEventType) -> AttemptEvent:
    return AttemptEvent(
        event_id=EventId.build(metadata.attempt_id, sequence),
        dataset_version=metadata.dataset_version,
        frozen_row_id=metadata.frozen_row_id,
        target_trial_id=metadata.target_trial_id,
        attempt_id=metadata.attempt_id,
        run_id=metadata.run_id,
        batch_id=metadata.batch_id,
        event_sequence=sequence,
        event_type=event_type,
        timestamp_utc=_utc_now(),
        artifact_ref=None,
        artifact_sha256=None,
        details={"synthetic_fixture": True},
    )


def _event_types(path: Path) -> list[str]:
    return [event.event_type.value for event in load_attempt_events(path)]


def _require_attempt(result: Any, *, tool_path: bool) -> None:
    if result.acceptance_proof is None or result.qualification_accepted is not True:
        raise SchemaInvariantError(f"synthetic proof attempt did not qualify: {result.invalid_reason}")
    root = result.raw_attempt_directory
    events = _event_types(root / "attempt_events.jsonl")
    required = {
        "PREPARED", "DISPATCHED", "MODEL_OUTPUT_CAPTURED", "PARSE_COMPLETED",
        "TURN_COMPLETED", "TERMINATED", "RESET_CHECKED", "GRADED",
        "TRIAL_ROW_MATERIALIZED", "FINALIZED",
    }
    if tool_path:
        required.update({"TOOL_EVENT", "TOOL_RESULT_CAPTURED"})
        if len(load_jsonl_records(root / "tool_transcript.jsonl")) != 1:
            raise SchemaInvariantError("synthetic tool proof requires exactly one genuine FastMCP dispatch")
        if len(load_jsonl_records(root / "model_outputs.jsonl")) < 2:
            raise SchemaInvariantError("synthetic tool proof did not produce multi-turn model output")
    elif load_jsonl_records(root / "tool_transcript.jsonl"):
        raise SchemaInvariantError("synthetic terminal proof unexpectedly dispatched a tool")
    if not required.issubset(events):
        raise SchemaInvariantError(f"synthetic proof attempt is missing events: {sorted(required - set(events))}")
    for name in ("hardware_snapshot.json", "model_load_placement.json", "grader_evidence.json", "tid_evidence.json"):
        if not (root / name).is_file():
            raise SchemaInvariantError(f"synthetic proof attempt is missing {name}")
    outputs = load_jsonl_records(root / "model_outputs.jsonl")
    if any(not item.get("generation_receipt", {}).get("generated_token_ids") for item in outputs):
        raise SchemaInvariantError("synthetic proof model output is missing real generated token IDs")


def run_m1_shared_engine_proof(
    *,
    root: Path,
    dataset_version: str,
    run_id: str,
    engine_factory: Callable[..., SharedExecutionEngine] = SharedExecutionEngine,
) -> dict[str, Any]:
    """Execute the two bounded fixtures and a controlled orphan replacement."""
    parsed_run = RunId.parse(run_id)
    if parsed_run.value.split("-")[-1] == "":
        raise SchemaInvariantError("run_id has no session token")
    document, config_sha256 = _load_authority(root, dataset_version)
    config_path = root / PROOF_CONFIG
    fixtures = {item["fixture_id"]: item for item in document["fixtures"]}
    terminal_row = _build_row(fixtures["P5SYN-M1-TERMINAL"], config_path, config_sha256, 1)
    tool_row = _build_row(fixtures["P5SYN-M1-TOOL"], config_path, config_sha256, 2)
    run_token = run_id.rsplit("-", 1)[1]
    slice_token = "SYN1"
    batch_id = str(BatchId.build(
        dataset_version, TrialPhase.PHASE5_UTILITY_PRESERVATION, ModelSlot.M1,
        Density.D3, MetadataSurfaceCondition.CLEAN, DefenseCondition.BASELINE,
        run_token, slice_token,
    ))
    batch = CampaignBatchPlan(
        model_slot="M1", workload=TrialPhase.PHASE5_UTILITY_PRESERVATION.value,
        batch_index=1, row_count=2, start_ordinal=1, end_ordinal=2,
        run_token=run_token, slice_token=slice_token, density_scope="D3",
        surface_scope="CLEAN", defense_scope="BASELINE", batch_artifact_id="synthetic-m1-proof-v1",
        scope_digest=config_sha256, batch_id=batch_id,
    )
    # Keep attempt paths below Windows' legacy path ceiling while retaining the
    # complete run identity in manifests and the top-level receipt.
    proof_root = root / "phase5" / "proof_runs" / run_token
    attempts_root = proof_root / "attempts"
    evidence_root = proof_root / "evidence"
    lineage = AttemptLineageStore(attempts_root / "attempt_lineage.csv")

    orphan_id = str(AttemptId.build(terminal_row.trial_id, 0, run_token))
    orphan_meta = AttemptWorkspaceMetadata.build(
        base_attempts_root=attempts_root, base_evidence_root=evidence_root,
        dataset_version=dataset_version, frozen_row_id=frozen_row_key(terminal_row),
        target_trial_id=str(terminal_row.trial_id), attempt_id=orphan_id, attempt_index=0,
        parent_attempt_id=None, run_id=run_id, batch_id=batch_id,
        attempt_status="DISPATCHED", created_utc=_utc_now(),
    )
    orphan_workspace = AttemptWorkspaceIsolation.build(
        orphan_meta, read_only_fixture_root=root / "phase5" / "fixtures"
    )
    orphan_workspace.materialize()
    orphan_meta.write_manifest()
    writer = AttemptEventLogWriter(orphan_meta.event_log_path)
    writer.append(_event(orphan_meta, 1, AttemptEventType.PREPARED))
    writer.append(_event(orphan_meta, 2, AttemptEventType.DISPATCHED))
    recovery = build_recovery_plan(
        (orphan_meta,), base_attempts_root=attempts_root, base_evidence_root=evidence_root,
        session_token=run_token, created_utc=_utc_now(),
    )
    if len(recovery.orphan_attempts) != 1 or recovery.replacement_workspaces[0].parent_attempt_id != orphan_id:
        raise SchemaInvariantError("controlled orphan was not recovered into a linked replacement")
    lineage.append(AttemptLineageRecord(
        dataset_version=dataset_version, frozen_row_id=frozen_row_key(terminal_row),
        target_trial_id=str(terminal_row.trial_id), attempt_id=orphan_id, attempt_index=0,
        parent_attempt_id=None, run_id=run_id, batch_id=batch_id, attempt_status="ORPHAN",
        invalid_reason="DISPATCHED_WITHOUT_FINALIZED", counts_toward_cell_n=False,
        accepted_attempt=False, raw_attempt_directory=orphan_meta.raw_attempt_directory,
    ))

    engine = engine_factory(
        official_trial=False, counts_for_phase5=False, publication_evidence=False,
        synthetic_fixture=True, dataset_version=dataset_version, root=root,
        attempts_root=attempts_root, evidence_root=evidence_root,
    )
    terminal_result = engine.execute_row(
        row=terminal_row, batch=batch, run_id=run_id, attempt_index=1, parent_attempt_id=orphan_id,
    )
    tool_result = engine.execute_row(
        row=tool_row, batch=batch, run_id=run_id, attempt_index=0, parent_attempt_id=None,
    )
    _require_attempt(terminal_result, tool_path=False)
    _require_attempt(tool_result, tool_path=True)
    for result in (terminal_result, tool_result):
        lineage.append(AttemptLineageRecord(
            dataset_version=dataset_version, frozen_row_id=result.frozen_row_id,
            target_trial_id=result.target_trial_id, attempt_id=result.attempt_id,
            attempt_index=result.attempt_index, parent_attempt_id=result.parent_attempt_id,
            run_id=run_id, batch_id=batch_id, attempt_status="SYNTHETIC_QUALIFIED",
            invalid_reason=None, counts_toward_cell_n=False, accepted_attempt=False,
            raw_attempt_directory=result.raw_attempt_directory,
        ))

    receipt = {
        "schema_version": "1.0", "status": "PASS", "run_id": run_id,
        "dataset_version": dataset_version, "model_slot": "M1",
        "official_trial": False, "counts_for_phase5": False,
        "publication_evidence": False, "synthetic_fixture": True,
        "official_trials": 0, "official_accepted_trials": 0,
        "shared_engine": f"{SharedExecutionEngine.__module__}.{SharedExecutionEngine.__name__}",
        "qualification_seal": "CLOSED_AFTER_FINALIZATION",
        "orphan_attempt_id": orphan_id,
        "replacement_attempt_id": terminal_result.attempt_id,
        "tool_attempt_id": tool_result.attempt_id,
        "lineage_path": lineage.path.relative_to(root).as_posix(),
        "proof_root": proof_root.relative_to(root).as_posix(),
        "source_authority_sha256": config_sha256,
    }
    output = root / PROOF_RECEIPT
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt
