"""Unified long-running campaign orchestration for Phase 5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .domain.errors import (
    FrozenArtifactHashError,
    MissingFrozenSettingError,
    OfficialDispatchBlockedError,
    SchemaInvariantError,
)
from .domain.enums import Density, ModelSlot, SessionState, TrialPhase
from .guards import repo_root
from .kaggle.run_planner import DEFAULT_RUN_PLAN_JSON
from .runtime.session import CampaignSession
from .seal import BarrierDecision, CampaignBarrierController, SealEpochRecord, perform_sync_barrier


DEFAULT_CAMPAIGN_OUTPUT = Path("phase5/validation/campaign_run_report.json")
DEFAULT_DASHBOARD_OUTPUT = Path("phase5/validation/checkpoint_status.json")
DEFAULT_RESUME_OUTPUT = Path("phase5/validation/campaign_resume_plan.json")
DEFAULT_SESSION_OUTPUT = Path("phase5/validation/session_report.json")
DEFAULT_BATCH_MANIFEST = Path("phase5/manifests/batch_partition_manifest_v3.json")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: Mapping[str, Any] | Sequence[Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MissingFrozenSettingError(f"required frozen file is missing: {path.as_posix()}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError(f"{path.as_posix()} must contain a JSON object")
    return data


def _write_if_unchanged(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise FrozenArtifactHashError(f"immutable report refusal for {path.as_posix()}")
        return
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True, slots=True)
class CampaignBatchPlan:
    model_slot: str
    workload: str
    batch_index: int
    row_count: int
    start_ordinal: int
    end_ordinal: int
    run_token: str
    slice_token: str
    density_scope: str
    surface_scope: str
    defense_scope: str
    batch_artifact_id: str
    scope_digest: str
    batch_id: str

    @property
    def estimated_seconds(self) -> float:
        return float(self.row_count)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "batch_artifact_id": self.batch_artifact_id,
            "batch_id": self.batch_id,
            "batch_index": self.batch_index,
            "density_scope": self.density_scope,
            "defense_scope": self.defense_scope,
            "end_ordinal": self.end_ordinal,
            "model_slot": self.model_slot,
            "row_count": self.row_count,
            "run_token": self.run_token,
            "scope_digest": self.scope_digest,
            "slice_token": self.slice_token,
            "start_ordinal": self.start_ordinal,
            "surface_scope": self.surface_scope,
            "workload": self.workload,
        }


@dataclass(frozen=True, slots=True)
class CampaignPlan:
    dataset_version: str
    model_slot: str
    model_load_status: str
    total_batches: int
    batches_per_session: int
    projected_sessions: int
    projected_session_hours: float
    projected_gpu_hours: float
    load_overhead_seconds: float
    p50_trial_seconds: float
    p95_trial_seconds: float
    invalid_attempt_rate: float
    safe_session_seconds: float
    checkpoint_barrier_interval_trials: int
    batch_manifest_path: Path
    batch_manifest_sha256: str
    run_plan_path: Path
    run_plan_sha256: str
    batches: tuple[CampaignBatchPlan, ...]
    source_evidence: tuple[tuple[str, str], ...] = ()

    def to_mapping(self) -> dict[str, Any]:
        return {
            "batch_manifest_path": self.batch_manifest_path.as_posix(),
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "batches": [batch.to_mapping() for batch in self.batches],
            "batches_per_session": self.batches_per_session,
            "checkpoint_barrier_interval_trials": self.checkpoint_barrier_interval_trials,
            "dataset_version": self.dataset_version,
            "invalid_attempt_rate": self.invalid_attempt_rate,
            "load_overhead_seconds": self.load_overhead_seconds,
            "model_load_status": self.model_load_status,
            "model_slot": self.model_slot,
            "p50_trial_seconds": self.p50_trial_seconds,
            "p95_trial_seconds": self.p95_trial_seconds,
            "projected_gpu_hours": self.projected_gpu_hours,
            "projected_session_hours": self.projected_session_hours,
            "projected_sessions": self.projected_sessions,
            "run_plan_path": self.run_plan_path.as_posix(),
            "run_plan_sha256": self.run_plan_sha256,
            "safe_session_seconds": self.safe_session_seconds,
            "source_evidence": [
                {"label": label, "sha256": sha256} for label, sha256 in self.source_evidence
            ],
            "total_batches": self.total_batches,
        }


@dataclass(frozen=True, slots=True)
class CampaignBatchResult:
    batch_id: str
    accepted_count: int
    finalized: bool
    estimated_seconds: float
    batch_hash: str
    status: str = "FINALIZED"
    analysis_eligible_count: int = 0

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_count": self.accepted_count,
            "analysis_eligible_count": self.analysis_eligible_count,
            "batch_hash": self.batch_hash,
            "batch_id": self.batch_id,
            "estimated_seconds": self.estimated_seconds,
            "finalized": self.finalized,
            "status": self.status,
        }


@dataclass(frozen=True, slots=True)
class CampaignRunReport:
    run_id: str
    model_slot: str
    dataset_version: str
    state: str
    seal_epoch: int
    processed_batch_ids: tuple[str, ...]
    remaining_batch_ids: tuple[str, ...]
    finalized_batch_count: int
    accepted_finalized_count: int
    invalid_attempt_count: int
    orphan_attempt_count: int
    elapsed_seconds: float
    safe_session_seconds: float
    sync_margin_seconds: float
    checkpoint_barrier_interval_trials: int
    stop_reason: str
    interrupted: bool
    resume_required: bool
    seal_epoch_hashes: tuple[str, ...]
    barrier_records: tuple[SealEpochRecord, ...]
    batch_results: tuple[CampaignBatchResult, ...]
    batch_manifest_sha256: str
    run_plan_sha256: str
    local_commit_sha: str | None = None
    remote_commit_sha: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_finalized_count": self.accepted_finalized_count,
            "barrier_records": [record.to_digest_mapping() for record in self.barrier_records],
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "batch_results": [result.to_mapping() for result in self.batch_results],
            "checkpoint_barrier_interval_trials": self.checkpoint_barrier_interval_trials,
            "dataset_version": self.dataset_version,
            "elapsed_seconds": self.elapsed_seconds,
            "finalized_batch_count": self.finalized_batch_count,
            "interrupted": self.interrupted,
            "invalid_attempt_count": self.invalid_attempt_count,
            "local_commit_sha": self.local_commit_sha,
            "model_slot": self.model_slot,
            "orphan_attempt_count": self.orphan_attempt_count,
            "processed_batch_ids": list(self.processed_batch_ids),
            "remaining_batch_ids": list(self.remaining_batch_ids),
            "remote_commit_sha": self.remote_commit_sha,
            "resume_required": self.resume_required,
            "run_id": self.run_id,
            "run_plan_sha256": self.run_plan_sha256,
            "safe_session_seconds": self.safe_session_seconds,
            "seal_epoch": self.seal_epoch,
            "seal_epoch_hashes": list(self.seal_epoch_hashes),
            "state": self.state,
            "stop_reason": self.stop_reason,
            "sync_margin_seconds": self.sync_margin_seconds,
        }

    def to_markdown(self) -> str:
        lines = [
            "# P14 Campaign Run Report",
            "",
            "## Verdict",
            "",
            f"- Run ID: `{self.run_id}`",
            f"- Model slot: `{self.model_slot}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- State: `{self.state}`",
            f"- Seal epoch: `{self.seal_epoch}`",
            f"- Finalized batches: `{self.finalized_batch_count}`",
            f"- Accepted finalized count: `{self.accepted_finalized_count}`",
            f"- Stop reason: `{self.stop_reason}`",
            f"- Interrupted: `{self.interrupted}`",
            f"- Resume required: `{self.resume_required}`",
            f"- Safe session seconds: `{self.safe_session_seconds:.2f}`",
            f"- Sync margin seconds: `{self.sync_margin_seconds:.2f}`",
            "",
            "## Batches",
        ]
        lines.extend(f"- `{batch_id}`" for batch_id in self.processed_batch_ids)
        if not self.processed_batch_ids:
            lines.append("- none")
        lines.extend(["", "## Remaining Batches"])
        lines.extend(f"- `{batch_id}`" for batch_id in self.remaining_batch_ids)
        if not self.remaining_batch_ids:
            lines.append("- none")
        lines.extend(["", "## Seal Epoch Hashes"])
        lines.extend(f"- `{seal_hash}`" for seal_hash in self.seal_epoch_hashes)
        if not self.seal_epoch_hashes:
            lines.append("- none")
        lines.extend(["", "## Batch Results"])
        for result in self.batch_results:
            lines.append(
                f"- `{result.batch_id}`: accepted={result.accepted_count}, seconds={result.estimated_seconds:.2f}, "
                f"hash={result.batch_hash}"
            )
        if not self.batch_results:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        _write_if_unchanged(json_path, json.dumps(self.to_mapping(), indent=2, sort_keys=True) + "\n")
        if markdown_path is not None:
            _write_if_unchanged(markdown_path, self.to_markdown())


@dataclass(frozen=True, slots=True)
class CampaignDashboardReport:
    run_id: str | None
    model_slot: str
    dataset_version: str
    state: str
    seal_epoch: int
    pending_batch_count: int
    finalized_batch_count: int
    accepted_finalized_count: int
    invalid_attempt_count: int
    orphan_attempt_count: int
    checkpoint_sync_status: str
    local_commit_sha: str | None
    remote_commit_sha: str | None
    batch_manifest_sha256: str
    run_plan_sha256: str
    seal_epoch_hashes: tuple[str, ...]
    time_to_safety_horizon_seconds: float | None
    max_observed_token_count: int | None
    next_batch_id: str | None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_finalized_count": self.accepted_finalized_count,
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "checkpoint_sync_status": self.checkpoint_sync_status,
            "dataset_version": self.dataset_version,
            "finalized_batch_count": self.finalized_batch_count,
            "invalid_attempt_count": self.invalid_attempt_count,
            "local_commit_sha": self.local_commit_sha,
            "max_observed_token_count": self.max_observed_token_count,
            "model_slot": self.model_slot,
            "next_batch_id": self.next_batch_id,
            "orphan_attempt_count": self.orphan_attempt_count,
            "pending_batch_count": self.pending_batch_count,
            "remote_commit_sha": self.remote_commit_sha,
            "run_id": self.run_id,
            "run_plan_sha256": self.run_plan_sha256,
            "seal_epoch": self.seal_epoch,
            "seal_epoch_hashes": list(self.seal_epoch_hashes),
            "state": self.state,
            "time_to_safety_horizon_seconds": self.time_to_safety_horizon_seconds,
        }

    def to_markdown(self) -> str:
        lines = [
            "# P14 Operational Dashboard",
            "",
            "## Health",
            "",
            f"- Run ID: `{self.run_id}`",
            f"- Model slot: `{self.model_slot}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- State: `{self.state}`",
            f"- Seal epoch: `{self.seal_epoch}`",
            f"- Pending batches: `{self.pending_batch_count}`",
            f"- Finalized batches: `{self.finalized_batch_count}`",
            f"- Accepted finalized count: `{self.accepted_finalized_count}`",
            f"- Invalid attempts: `{self.invalid_attempt_count}`",
            f"- Orphan attempts: `{self.orphan_attempt_count}`",
            f"- Checkpoint sync status: `{self.checkpoint_sync_status}`",
            f"- Next batch ID: `{self.next_batch_id}`",
            f"- Time to safety horizon: `{self.time_to_safety_horizon_seconds}`",
            f"- Max observed token count: `{self.max_observed_token_count}`",
            "",
            "## Hashes",
            f"- Batch manifest: `{self.batch_manifest_sha256}`",
            f"- Run plan: `{self.run_plan_sha256}`",
        ]
        lines.extend(["", "## Seal Epoch Hashes"])
        lines.extend(f"- `{seal_hash}`" for seal_hash in self.seal_epoch_hashes)
        if not self.seal_epoch_hashes:
            lines.append("- none")
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        _write_if_unchanged(json_path, json.dumps(self.to_mapping(), indent=2, sort_keys=True) + "\n")
        if markdown_path is not None:
            _write_if_unchanged(markdown_path, self.to_markdown())


@dataclass(frozen=True, slots=True)
class CampaignResumePlan:
    run_id: str | None
    model_slot: str
    dataset_version: str
    state: str
    seal_epoch: int
    next_batch_id: str | None
    remaining_batch_ids: tuple[str, ...]
    pending_batch_count: int
    resume_required: bool
    resume_reason: str
    checkpoint_sync_status: str
    time_to_safety_horizon_seconds: float | None
    batch_manifest_sha256: str
    run_plan_sha256: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "checkpoint_sync_status": self.checkpoint_sync_status,
            "dataset_version": self.dataset_version,
            "model_slot": self.model_slot,
            "next_batch_id": self.next_batch_id,
            "pending_batch_count": self.pending_batch_count,
            "remaining_batch_ids": list(self.remaining_batch_ids),
            "resume_reason": self.resume_reason,
            "resume_required": self.resume_required,
            "run_id": self.run_id,
            "run_plan_sha256": self.run_plan_sha256,
            "seal_epoch": self.seal_epoch,
            "state": self.state,
            "time_to_safety_horizon_seconds": self.time_to_safety_horizon_seconds,
        }

    def to_markdown(self) -> str:
        lines = [
            "# P14 Campaign Resume Plan",
            "",
            f"- Run ID: `{self.run_id}`",
            f"- Model slot: `{self.model_slot}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- State: `{self.state}`",
            f"- Seal epoch: `{self.seal_epoch}`",
            f"- Pending batches: `{self.pending_batch_count}`",
            f"- Next batch ID: `{self.next_batch_id}`",
            f"- Resume required: `{self.resume_required}`",
            f"- Resume reason: `{self.resume_reason}`",
            f"- Checkpoint sync status: `{self.checkpoint_sync_status}`",
            f"- Time to safety horizon: `{self.time_to_safety_horizon_seconds}`",
            "",
            "## Remaining Batches",
        ]
        lines.extend(f"- `{batch_id}`" for batch_id in self.remaining_batch_ids)
        if not self.remaining_batch_ids:
            lines.append("- none")
        lines.extend(["", "## Hashes", f"- Batch manifest: `{self.batch_manifest_sha256}`", f"- Run plan: `{self.run_plan_sha256}`"])
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        _write_if_unchanged(json_path, json.dumps(self.to_mapping(), indent=2, sort_keys=True) + "\n")
        if markdown_path is not None:
            _write_if_unchanged(markdown_path, self.to_markdown())


def _load_run_plan(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("status") != "PASS":
        raise SchemaInvariantError("kaggle run plan must be PASS")
    return data


def _load_batch_manifest(path: Path) -> dict[str, Any]:
    data = _load_json(path)
    if data.get("status") != "PASS":
        raise SchemaInvariantError("batch partition manifest must be PASS")
    return data


def _select_model_plan(run_plan: Mapping[str, Any], model_slot: str) -> Mapping[str, Any]:
    for item in run_plan.get("model_plans", []):
        if isinstance(item, dict) and item.get("model_slot") == model_slot:
            return item
    raise MissingFrozenSettingError(f"model plan not found for {model_slot!r}")


def _select_model_campaign(batch_manifest: Mapping[str, Any], model_slot: str) -> Mapping[str, Any]:
    for item in batch_manifest.get("model_campaigns", []):
        if isinstance(item, dict) and item.get("model_slot") == model_slot:
            return item
    raise MissingFrozenSettingError(f"batch campaign not found for {model_slot!r}")


def _build_batch_id(model_slot: str, dataset_version: str, batch: Mapping[str, Any]) -> str:
    workload = TrialPhase.from_value(str(batch["workload"]))
    model = ModelSlot.from_value(model_slot)
    density = str(batch["density_scope"])
    surface = str(batch["surface_scope"])
    defense = str(batch["defense_scope"])
    run_token = str(batch["run_token"])
    slice_token = str(batch["slice_token"])
    return f"P5BAT-{dataset_version}-{workload.value}-{model.value}-{density}-{surface}-{defense}-{run_token}-{slice_token}"


def _parse_batches(model_slot: str, dataset_version: str, model_campaign: Mapping[str, Any]) -> tuple[CampaignBatchPlan, ...]:
    batches: list[CampaignBatchPlan] = []
    for workload_partition in model_campaign.get("workload_partitions", []):
        if not isinstance(workload_partition, dict):
            raise SchemaInvariantError("workload partition must be a JSON object")
        workload = str(workload_partition.get("workload"))
        for batch in workload_partition.get("batches", []):
            if not isinstance(batch, dict):
                raise SchemaInvariantError("batch slice must be a JSON object")
            batch_id = _build_batch_id(model_slot, dataset_version, {**batch, "workload": workload})
            batches.append(
                CampaignBatchPlan(
                    model_slot=model_slot,
                    workload=workload,
                    batch_index=int(batch["batch_index"]),
                    row_count=int(batch["row_count"]),
                    start_ordinal=int(batch["start_ordinal"]),
                    end_ordinal=int(batch["end_ordinal"]),
                    run_token=str(batch["run_token"]),
                    slice_token=str(batch["slice_token"]),
                    density_scope=str(batch["density_scope"]),
                    surface_scope=str(batch["surface_scope"]),
                    defense_scope=str(batch["defense_scope"]),
                    batch_artifact_id=str(batch["batch_artifact_id"]),
                    scope_digest=str(batch["scope_digest"]),
                    batch_id=batch_id,
                )
            )
    batches.sort(key=lambda item: (item.workload, item.batch_index))
    seen = {batch.batch_id for batch in batches}
    if len(seen) != len(batches):
        raise SchemaInvariantError("duplicate batch identifiers detected in campaign manifest")
    return tuple(batches)


def load_campaign_plan(
    *,
    model_slot: str,
    run_plan_path: Path | None = None,
    batch_manifest_path: Path | None = None,
    root: Path | None = None,
) -> CampaignPlan:
    repository_root = (root or repo_root()).resolve()
    run_plan_path = run_plan_path or (repository_root / DEFAULT_RUN_PLAN_JSON)
    batch_manifest_path = batch_manifest_path or (repository_root / DEFAULT_BATCH_MANIFEST)
    run_plan = _load_run_plan(run_plan_path)
    batch_manifest = _load_batch_manifest(batch_manifest_path)
    model_plan = _select_model_plan(run_plan, model_slot)
    model_campaign = _select_model_campaign(batch_manifest, model_slot)
    if model_plan.get("model_load_status") != "LOAD_SUCCESS":
        raise SchemaInvariantError(f"model {model_slot} is not available for campaign execution: {model_plan.get('model_load_status')}")
    if run_plan.get("dataset_version") != batch_manifest.get("dataset_version"):
        raise SchemaInvariantError("run plan and batch manifest dataset versions do not match")
    batch_manifest_sha256 = _sha256_bytes(batch_manifest_path.read_bytes())
    if str(run_plan.get("batch_manifest_sha256")) != str(batch_manifest.get("manifest_sha256")):
        raise FrozenArtifactHashError("run plan batch manifest hash does not match the frozen batch manifest")
    batches = _parse_batches(model_slot, str(run_plan["dataset_version"]), model_campaign)
    if int(model_campaign.get("batch_count", -1)) != len(batches):
        raise SchemaInvariantError("batch manifest batch_count does not reconcile with parsed batches")
    if int(model_plan.get("total_batches", -1)) != len(batches):
        raise SchemaInvariantError("model plan total_batches does not reconcile with parsed batches")

    run_plan_sha256 = _sha256_bytes(run_plan_path.read_bytes())
    source_evidence = tuple(
        (
            str(item["label"]),
            str(item["sha256"]),
        )
        for item in run_plan.get("source_evidence", [])
        if isinstance(item, dict)
    )
    return CampaignPlan(
        dataset_version=str(run_plan["dataset_version"]),
        model_slot=model_slot,
        model_load_status=str(model_plan["model_load_status"]),
        total_batches=len(batches),
        batches_per_session=int(model_plan["batches_per_session"]),
        projected_sessions=int(model_plan["projected_sessions"]),
        projected_session_hours=float(model_plan["projected_session_hours"]),
        projected_gpu_hours=float(model_plan["projected_gpu_hours"]),
        load_overhead_seconds=float(model_plan["load_overhead_seconds"]),
        p50_trial_seconds=float(model_plan["p50_trial_seconds"]),
        p95_trial_seconds=float(model_plan["p95_trial_seconds"]),
        invalid_attempt_rate=float(model_plan["invalid_attempt_rate"]),
        safe_session_seconds=float(run_plan["safe_session_seconds"]),
        checkpoint_barrier_interval_trials=int(run_plan["checkpoint_barrier_interval_trials"]),
        batch_manifest_path=batch_manifest_path,
        batch_manifest_sha256=batch_manifest_sha256,
        run_plan_path=run_plan_path,
        run_plan_sha256=run_plan_sha256,
        batches=batches,
        source_evidence=source_evidence,
    )


def planning_batch_result(batch: CampaignBatchPlan, *, p95_trial_seconds: float) -> CampaignBatchResult:
    """Render a non-official estimate that can never represent finalized work."""

    payload = json.dumps(batch.to_mapping(), sort_keys=True, separators=(",", ":"))
    return CampaignBatchResult(
        batch_id=batch.batch_id,
        accepted_count=0,
        finalized=False,
        estimated_seconds=float(batch.row_count * p95_trial_seconds),
        batch_hash=_sha256_bytes(payload.encode("utf-8")),
        status="PLAN_ONLY",
    )


def run_campaign(
    *,
    model_slot: str,
    run_id: str | None = None,
    utcdate: str | None = None,
    until_safety_horizon: bool = False,
    batch_manifest_path: Path | None = None,
    run_plan_path: Path | None = None,
    root: Path | None = None,
    session: CampaignSession | None = None,
    max_batches: int | None = None,
    batch_processor: Callable[[CampaignBatchPlan, float], CampaignBatchResult] | None = None,
    plan_only: bool = False,
    target_batch_id: str | None = None,
) -> tuple[CampaignSession, CampaignRunReport]:
    if max_batches is not None and max_batches <= 0:
        raise SchemaInvariantError("max_batches must be positive when provided")
    plan = load_campaign_plan(
        model_slot=model_slot,
        run_plan_path=run_plan_path,
        batch_manifest_path=batch_manifest_path,
        root=root,
    )
    if not until_safety_horizon:
        raise MissingFrozenSettingError("run-campaign requires --until-safety-horizon")

    operational_session = session or CampaignSession.open(
        model_slot=model_slot,
        run_id=run_id,
        utcdate=utcdate,
        batch_id=plan.batches[0].batch_id if plan.batches else None,
        batch_manifest_sha256=plan.batch_manifest_sha256,
        run_plan_sha256=plan.run_plan_sha256,
        time_to_safety_horizon_seconds=plan.safe_session_seconds,
    )
    if operational_session.state is not SessionState.SEALED:
        operational_session = operational_session.seal()

    controller = CampaignBarrierController(
        safe_session_seconds=plan.safe_session_seconds,
        checkpoint_barrier_interval_trials=plan.checkpoint_barrier_interval_trials,
        p95_trial_seconds=plan.p95_trial_seconds,
        load_overhead_seconds=plan.load_overhead_seconds,
    )

    if plan_only and batch_processor is not None:
        raise OfficialDispatchBlockedError("plan-only mode cannot accept a batch execution processor")
    if not plan_only and batch_processor is None:
        raise OfficialDispatchBlockedError(
            "run-campaign requires an explicitly configured real execution adapter; "
            "use plan-only mode only for non-official estimates"
        )
    if not plan_only and getattr(batch_processor, "real_execution_adapter", False) is not True:
        raise OfficialDispatchBlockedError(
            "campaign batch processor is not a qualified real execution adapter"
        )
    processor = batch_processor or (lambda batch, p95: planning_batch_result(batch, p95_trial_seconds=p95))
    elapsed_seconds = plan.load_overhead_seconds
    processed_results: list[CampaignBatchResult] = []
    barrier_records: list[SealEpochRecord] = []
    stop_reason = "complete"
    interrupted = False
    remaining_batches = list(plan.batches)
    if target_batch_id is not None:
        if target_batch_id not in {batch.batch_id for batch in remaining_batches}:
            raise MissingFrozenSettingError(f"requested frozen batch is not present in the active plan: {target_batch_id}")
        remaining_batches = [batch for batch in remaining_batches if batch.batch_id == target_batch_id]
    if operational_session.processed_batch_ids:
        remaining_batches = [batch for batch in remaining_batches if batch.batch_id not in operational_session.processed_batch_ids]

    for index, batch in enumerate(remaining_batches, start=1):
        if max_batches is not None and len(processed_results) >= max_batches:
            stop_reason = "interrupted"
            interrupted = True
            break
        if controller.should_stop_before_batch(elapsed_seconds=elapsed_seconds, next_batch_row_count=batch.row_count):
            stop_reason = "safety-horizon"
            break

        result = processor(batch, controller.p95_trial_seconds)
        if result.batch_id != batch.batch_id:
            raise SchemaInvariantError("batch processor returned a mismatched batch identifier")
        if plan_only and (result.accepted_count != 0 or result.finalized or result.status != "PLAN_ONLY"):
            raise OfficialDispatchBlockedError("plan-only processor attempted to create accepted or finalized work")
        if not plan_only and result.status == "PLAN_ONLY":
            raise OfficialDispatchBlockedError("planning results cannot enter an execution campaign")
        processed_results.append(result)
        if not plan_only:
            operational_session = operational_session.record_batch(
                batch_id=batch.batch_id,
                accepted_count=result.accepted_count,
                finalized=result.finalized,
                estimated_seconds=result.estimated_seconds,
            )
        elapsed_seconds += result.estimated_seconds
        if plan_only:
            continue

        decision = controller.decide(
            elapsed_seconds=elapsed_seconds,
            accepted_count=operational_session.accepted_finalized_count,
            finalized_batch_count=operational_session.finalized_batch_count,
        )
        should_continue = index < len(remaining_batches)
        if decision.should_sync or not should_continue:
            reseal = should_continue and not controller.should_stop_before_batch(
                elapsed_seconds=elapsed_seconds,
                next_batch_row_count=remaining_batches[index].row_count if should_continue and index < len(remaining_batches) else batch.row_count,
            )
            operational_session, barrier_record = perform_sync_barrier(
                operational_session,
                reason=decision.reason,
                hashes_match=True,
                credential_purged=True,
                reseal=reseal and should_continue,
                elapsed_seconds=elapsed_seconds,
            )
            barrier_records.append(barrier_record)
            if not reseal or not should_continue:
                stop_reason = "complete" if not should_continue else "safety-horizon"
                break

    remaining_after_run = tuple(batch.batch_id for batch in remaining_batches[len(processed_results) :])
    resume_required = bool(remaining_after_run)
    if interrupted:
        resume_required = True
    report = CampaignRunReport(
        run_id=operational_session.run_id,
        model_slot=operational_session.model_slot.value,
        dataset_version=plan.dataset_version,
        state=operational_session.state.value,
        seal_epoch=operational_session.seal_epoch,
        processed_batch_ids=(
            tuple(result.batch_id for result in processed_results)
            if plan_only
            else operational_session.processed_batch_ids
        ),
        remaining_batch_ids=remaining_after_run,
        finalized_batch_count=operational_session.finalized_batch_count,
        accepted_finalized_count=operational_session.accepted_finalized_count,
        invalid_attempt_count=operational_session.invalid_attempt_count,
        orphan_attempt_count=operational_session.orphan_attempt_count,
        elapsed_seconds=elapsed_seconds,
        safe_session_seconds=plan.safe_session_seconds,
        sync_margin_seconds=controller.sync_margin_seconds,
        checkpoint_barrier_interval_trials=plan.checkpoint_barrier_interval_trials,
        stop_reason=stop_reason,
        interrupted=interrupted,
        resume_required=resume_required,
        seal_epoch_hashes=operational_session.seal_epoch_hashes,
        barrier_records=tuple(barrier_records),
        batch_results=tuple(processed_results),
        batch_manifest_sha256=plan.batch_manifest_sha256,
        run_plan_sha256=plan.run_plan_sha256,
        local_commit_sha=operational_session.local_commit_sha,
        remote_commit_sha=operational_session.remote_commit_sha,
    )
    return operational_session, report


def build_dashboard(
    *,
    model_slot: str,
    session: CampaignSession | None = None,
    run_id: str | None = None,
    run_plan_path: Path | None = None,
    batch_manifest_path: Path | None = None,
    root: Path | None = None,
) -> CampaignDashboardReport:
    plan = load_campaign_plan(
        model_slot=model_slot,
        run_plan_path=run_plan_path,
        batch_manifest_path=batch_manifest_path,
        root=root,
    )
    current_session = session or CampaignSession.open(
        model_slot=model_slot,
        run_id=run_id,
        batch_id=plan.batches[0].batch_id if plan.batches else None,
        batch_manifest_sha256=plan.batch_manifest_sha256,
        run_plan_sha256=plan.run_plan_sha256,
        time_to_safety_horizon_seconds=plan.safe_session_seconds,
    )
    processed_count = len(current_session.processed_batch_ids)
    pending_count = max(0, len(plan.batches) - processed_count)
    next_batch_id = None
    for batch in plan.batches:
        if batch.batch_id not in current_session.processed_batch_ids:
            next_batch_id = batch.batch_id
            break
    return CampaignDashboardReport(
        run_id=current_session.run_id,
        model_slot=current_session.model_slot.value,
        dataset_version=plan.dataset_version,
        state=current_session.state.value,
        seal_epoch=current_session.seal_epoch,
        pending_batch_count=pending_count,
        finalized_batch_count=current_session.finalized_batch_count,
        accepted_finalized_count=current_session.accepted_finalized_count,
        invalid_attempt_count=current_session.invalid_attempt_count,
        orphan_attempt_count=current_session.orphan_attempt_count,
        checkpoint_sync_status=current_session.checkpoint_sync_status,
        local_commit_sha=current_session.local_commit_sha,
        remote_commit_sha=current_session.remote_commit_sha,
        batch_manifest_sha256=plan.batch_manifest_sha256,
        run_plan_sha256=plan.run_plan_sha256,
        seal_epoch_hashes=current_session.seal_epoch_hashes,
        time_to_safety_horizon_seconds=current_session.time_to_safety_horizon_seconds,
        max_observed_token_count=current_session.max_observed_token_count,
        next_batch_id=next_batch_id,
    )


def build_resume_plan(
    *,
    model_slot: str,
    session: CampaignSession | None = None,
    run_id: str | None = None,
    run_plan_path: Path | None = None,
    batch_manifest_path: Path | None = None,
    root: Path | None = None,
) -> CampaignResumePlan:
    dashboard = build_dashboard(
        model_slot=model_slot,
        session=session,
        run_id=run_id,
        run_plan_path=run_plan_path,
        batch_manifest_path=batch_manifest_path,
        root=root,
    )
    plan = load_campaign_plan(
        model_slot=model_slot,
        run_plan_path=run_plan_path,
        batch_manifest_path=batch_manifest_path,
        root=root,
    )
    processed = session.processed_batch_ids if session else ()
    remaining_batch_ids = tuple(batch.batch_id for batch in plan.batches if batch.batch_id not in processed)
    resume_required = bool(remaining_batch_ids) or dashboard.state not in {"REVERIFIED_AFTER_SYNC", "TERMINAL"}
    resume_reason = "remaining-batches" if remaining_batch_ids else "session-ready"
    return CampaignResumePlan(
        run_id=dashboard.run_id,
        model_slot=dashboard.model_slot,
        dataset_version=dashboard.dataset_version,
        state=dashboard.state,
        seal_epoch=dashboard.seal_epoch,
        next_batch_id=dashboard.next_batch_id,
        remaining_batch_ids=remaining_batch_ids,
        pending_batch_count=dashboard.pending_batch_count,
        resume_required=resume_required,
        resume_reason=resume_reason,
        checkpoint_sync_status=dashboard.checkpoint_sync_status,
        time_to_safety_horizon_seconds=dashboard.time_to_safety_horizon_seconds,
        batch_manifest_sha256=dashboard.batch_manifest_sha256,
        run_plan_sha256=dashboard.run_plan_sha256,
    )
