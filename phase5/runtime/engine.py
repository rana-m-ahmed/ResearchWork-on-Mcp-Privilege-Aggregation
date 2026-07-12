"""Shared execution engine for Phase 5."""

from __future__ import annotations

import json
import logging
import hashlib
import platform
import subprocess
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..campaign import CampaignBatchPlan
from ..domain.identifiers import AttemptId
from ..evidence import AttemptEventLogWriter, AttemptEventType
from ..evidence.workspace import AttemptWorkspaceMetadata
from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError
from ..domain.invariants import FROZEN_TRIAL_FIELDS, FrozenTrialRow
from ..evidence.trial_materializer import materialize_frozen_trial_row
from ..evidence.io import load_jsonl_records
from ..grading.frozen_grader import FROZEN_GRADER_SHA256, FrozenGraderAdapter
from ..grading.tid import TidResult, compute_logical_tid
from ..queues.frozen_queue_loader import FrozenQueueRow
from .agent_loop import run_frozen_agent_loop, load_frozen_state_machine_controls
from .model_backend_adapter import build_frozen_model_backend_adapter, load_frozen_model_backend_identity
from .official_execution import ExecutedTrialResult, RealTrialPipeline, TrialAcceptanceProof, frozen_row_key
from .reset_controller import ResetController, load_reset_failure_retry_limit
from .token_budget import build_exact_tokenizer, TokenBudgetPolicy
from .workspace_isolation import AttemptWorkspaceIsolation
from .mcp_server_launcher import build_fastmcp_tool_catalog, build_validated_server

logger = logging.getLogger(__name__)

class SharedExecutionEngine(RealTrialPipeline):
    """The real shared execution engine used by qualification and official modes."""

    def __init__(
        self,
        *,
        official_trial: bool,
        counts_for_phase5: bool,
        publication_evidence: bool,
        synthetic_fixture: bool,
        dataset_version: str,
        root: Path | None = None,
        attempts_root: Path | None = None,
        evidence_root: Path | None = None,
    ) -> None:
        self.real_pipeline = True
        self.official_trial = official_trial
        self.counts_for_phase5 = counts_for_phase5
        self.publication_evidence = publication_evidence
        self.synthetic_fixture = synthetic_fixture
        self.dataset_version = dataset_version
        self.root = root or Path.cwd()
        self.attempts_root = attempts_root or self.root / "phase5" / "attempts"
        self.evidence_root = evidence_root or self.root / "phase5" / "evidence"

        # Official boundaries assertions
        if self.official_trial:
            assert self.counts_for_phase5 is True
            assert self.publication_evidence is True
            assert self.synthetic_fixture is False
        else:
            assert self.official_trial is False
            assert self.counts_for_phase5 is False
            assert self.publication_evidence is False
            assert self.synthetic_fixture is True

        self.controls = load_frozen_state_machine_controls(self.root)
        self.model_identity = load_frozen_model_backend_identity(self.root)
        
        # In a real environment, we instantiate the real backend. But for tests, we may skip actual loading
        # unless actually executing.
        self.backend = None
        self.tokenizer = None

    def _ensure_loaded(self) -> None:
        if self.backend is None:
            self.backend = build_frozen_model_backend_adapter(root=self.root)
            self.tokenizer = build_exact_tokenizer(
                root=self.root,
                revision=self.model_identity.huggingface_commit_sha,
            )
            self.backend.attach_tokenizer(self.tokenizer)
        prepare_runtime = getattr(self.backend, "prepare_runtime", None)
        if callable(prepare_runtime):
            prepare_runtime()

    def _load_task_content(self, row: FrozenQueueRow) -> dict[str, Any]:
        if self.synthetic_fixture and row.task_id.startswith("P5SYN-"):
            fixture_path = self.root / "phase5" / "configs" / "synthetic_m1_proof_v1.json"
            if not fixture_path.is_file():
                raise MissingFrozenSettingError(f"synthetic proof fixture registry is missing: {fixture_path.as_posix()}")
            document = json.loads(fixture_path.read_text(encoding="utf-8"))
            if document.get("dataset_version") != self.dataset_version or document.get("model_slot") != "M1":
                raise SchemaInvariantError("synthetic proof fixture authority does not match the active engine")
            matches = [item for item in document.get("fixtures", []) if item.get("fixture_id") == row.task_id]
            if len(matches) != 1:
                raise SchemaInvariantError(f"synthetic proof fixture must contain exactly one entry for {row.task_id!r}")
            content = matches[0].get("task_content")
            if not isinstance(content, dict):
                raise SchemaInvariantError(f"synthetic task content is invalid for {row.task_id!r}")
            actual_hash = hashlib.sha256(
                json.dumps(content, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if matches[0].get("task_hash") != row.task_hash or actual_hash != row.task_hash:
                raise SchemaInvariantError(f"synthetic task hash mismatch for {row.task_id!r}")
            return content
        registry_path = self.root / "phase5" / "manifests" / "frozen_task_content_registry_v2.json"
        if not registry_path.is_file():
            raise MissingFrozenSettingError(f"frozen task content registry is missing: {registry_path.as_posix()}")
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        matches = [entry for entry in registry if entry.get("task_id") == row.task_id]
        if len(matches) != 1:
            raise SchemaInvariantError(f"frozen task registry must contain exactly one entry for {row.task_id!r}")
        entry = matches[0]
        content = entry.get("canonical_task_content")
        if not isinstance(content, dict) or content.get("task_hash") != row.task_hash:
            raise SchemaInvariantError(f"frozen canonical task hash mismatch for {row.task_id!r}")
        description = content.get("description")
        if not isinstance(description, str) or not description.strip():
            raise SchemaInvariantError(f"frozen task description is missing for {row.task_id!r}")
        expected_sequence = content.get("expected_sequence")
        if not isinstance(expected_sequence, list) or not all(isinstance(item, str) and item for item in expected_sequence):
            raise SchemaInvariantError(f"frozen expected sequence is invalid for {row.task_id!r}")
        return content

    def _load_task_description(self, row: FrozenQueueRow) -> str:
        return str(self._load_task_content(row)["description"])

    @staticmethod
    def _schema_variant(row: FrozenQueueRow) -> str:
        condition = {
            "CLEAN": "CLEAN",
            "POISON_TD": "POISON-TD",
            "POISON_CA": "POISON-CA",
        }.get(row.metadata_surface_condition.value)
        if condition is None:
            raise SchemaInvariantError(f"unsupported metadata surface: {row.metadata_surface_condition.value!r}")
        return f"{row.density.value}-{condition}"

    def _build_runtime_row(self, row: FrozenQueueRow, *, run_id: str) -> FrozenTrialRow:
        phase_by_queue = {
            "core": "phase5_adversarial_core",
            "defense": "phase5_adversarial_defense",
            "utility": "phase5_utility_preservation",
        }
        try:
            phase = phase_by_queue[row.queue_name]
        except KeyError as exc:
            raise SchemaInvariantError(f"unknown frozen queue name: {row.queue_name!r}") from exc
        is_utility = row.queue_name == "utility"
        git_commit = subprocess.check_output(
            ["git", "-C", str(self.root), "rev-parse", "HEAD"], text=True
        ).strip()
        mapping = {
            "phase": phase,
            "official_trial": self.official_trial,
            "trial_id": str(row.trial_id),
            "run_id": run_id,
            "branch": "main" if self.synthetic_fixture else "phase5-official-source-v3",
            "git_commit_hash": git_commit,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "model_id": self.model_identity.model_id,
            "exact_model_identifier": self.model_identity.exact_model_identifier,
            "model_digest": self.model_identity.model_digest,
            "quantization": self.model_identity.quantization,
            "backend": self.model_identity.backend,
            "backend_version": self.model_identity.backend_version,
            "ollama_version": self.model_identity.ollama_version,
            "density": row.density.value,
            "metadata_surface_condition": row.metadata_surface_condition.value,
            "attack_family": row.attack_family.value,
            "defense_condition": row.defense_condition.value,
            "payload_id": "NONE" if is_utility else row.payload_id,
            "phase1_payload_hash": None if is_utility else row.phase1_payload_hash,
            "payload_hash": None if is_utility else row.phase1_payload_hash,
            "adversarial_payload_present": not is_utility,
            "payload_condition": row.payload_condition.value,
        }
        return FrozenTrialRow.from_mapping(mapping)

    @staticmethod
    def _runtime_row_mapping(row: FrozenTrialRow) -> dict[str, Any]:
        return {
            field: (value.value if hasattr(value, "value") else value)
            for field in FROZEN_TRIAL_FIELDS
            for value in (getattr(row, field),)
        }

    def execute_row(
        self,
        *,
        row: FrozenQueueRow,
        batch: CampaignBatchPlan,
        run_id: str,
        attempt_index: int,
        parent_attempt_id: str | None,
    ) -> ExecutedTrialResult:
        """Execute a single frozen queue row through the full shared engine."""
        self._ensure_loaded()
        runtime_row = self._build_runtime_row(row, run_id=run_id)
        
        attempt_id = AttemptId.build(row.trial_id, attempt_index, batch.run_token)
        metadata = AttemptWorkspaceMetadata.build(
            base_attempts_root=self.attempts_root,
            base_evidence_root=self.evidence_root,
            dataset_version=self.dataset_version,
            frozen_row_id=frozen_row_key(row),
            target_trial_id=str(row.trial_id),
            attempt_id=str(attempt_id),
            attempt_index=attempt_index,
            parent_attempt_id=parent_attempt_id,
            run_id=run_id,
            batch_id=batch.batch_id,
            attempt_status="DISPATCHED",
            created_utc=datetime.now(timezone.utc).isoformat(),
        )
        fixture_root = self.root / "phase5" / "fixtures"
        fixture_root.mkdir(parents=True, exist_ok=True)
        workspace = AttemptWorkspaceIsolation.build(metadata, read_only_fixture_root=fixture_root)
        workspace.materialize()
        load_memory_plan = getattr(self.backend, "load_memory_plan", None)
        if load_memory_plan is not None:
            workspace.write_json_snapshot("model_load_placement.json", load_memory_plan)
        hardware_snapshot: dict[str, Any] = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "official_trial": self.official_trial,
            "counts_for_phase5": self.counts_for_phase5,
            "publication_evidence": self.publication_evidence,
            "synthetic_fixture": self.synthetic_fixture,
        }
        try:
            import torch

            hardware_snapshot["cuda_available"] = torch.cuda.is_available()
            hardware_snapshot["cuda_device_count"] = torch.cuda.device_count()
            hardware_snapshot["cuda_device_names"] = [
                torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())
            ]
        except Exception as exc:
            hardware_snapshot["cuda_available"] = False
            hardware_snapshot["cuda_probe_error"] = f"{type(exc).__name__}: {exc}"
        hardware_snapshot["nvidia_smi"] = subprocess.run(
            ["nvidia-smi"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False
        ).stdout if hardware_snapshot.get("cuda_available") else ""
        workspace.write_json_snapshot("hardware_snapshot.json", hardware_snapshot)

        mcp_verification = build_validated_server(
            variant_id=self._schema_variant(row),
            workspace=workspace,
        )
        workspace.write_json_snapshot(
            "fastmcp_discovery.json",
            {
                "host": mcp_verification.host,
                "port": mcp_verification.port,
                "tool_names": list(mcp_verification.tool_names),
                "reset_hidden": mcp_verification.reset_hidden,
                "reset_dispatch_rejected": mcp_verification.reset_dispatch.rejected,
            },
        )
        tool_catalog = build_fastmcp_tool_catalog(mcp_verification)
        task_content = self._load_task_content(row)
        expected_sequence = tuple(task_content["expected_sequence"])
        
        reset_executor = ResetController(
            workspace=workspace,
            retry_limit=load_reset_failure_retry_limit(self.root),
        )
        
        grader = FrozenGraderAdapter()
        grade_state: dict[str, Any] = {}
        tid_state: dict[str, TidResult] = {}

        def actual_exposed_sequence() -> tuple[str, ...]:
            return tuple(
                str(item["exposed_tool_name"])
                for item in load_jsonl_records(workspace.workspace_root / "tool_transcript.jsonl")
            )

        def grade_callable() -> None:
            matched, actual_logical = grader.grade_sequence(expected_sequence, actual_exposed_sequence())
            grade_state.update({"matched": matched, "actual_logical": actual_logical})
            workspace.write_json_snapshot(
                "grader_evidence.json",
                {
                    "grader_sha256": FROZEN_GRADER_SHA256,
                    "expected_logical_sequence": list(expected_sequence),
                    "actual_exposed_sequence": list(actual_exposed_sequence()),
                    "actual_logical_sequence": list(actual_logical),
                    "sequence_match": matched,
                    "official_trial": self.official_trial,
                    "synthetic_fixture": self.synthetic_fixture,
                },
            )
            
        def tid_callable() -> None:
            actual_logical = tuple(grade_state.get("actual_logical", ()))
            result = compute_logical_tid(actual_logical, (expected_sequence,))
            tid_state["result"] = result
            workspace.write_json_snapshot("tid_evidence.json", asdict(result))
            
        def materialize_callable() -> None:
            materialized = materialize_frozen_trial_row(
                self._runtime_row_mapping(runtime_row),
                tid_result=tid_state.get("result"),
            )
            workspace.write_json_snapshot("materialized_trial_row.json", materialized.row)
            
        def validate_callable() -> None:
            FrozenTrialRow.from_mapping(self._runtime_row_mapping(runtime_row))
            
        def finalize_callable() -> None:
            workspace.write_json_snapshot("finalization_prepared.json", {"status": "PREPARED"})

        def seal_evidence_index() -> None:
            records = []
            for path in sorted(workspace.workspace_root.iterdir()):
                if path.is_file() and path != workspace.metadata.artifact_index_path:
                    records.append({
                        "path": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "bytes": path.stat().st_size,
                    })
            workspace.write_text_snapshot(
                workspace.metadata.artifact_index_path.name,
                "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in records),
            )
            
        def lineage_callable() -> None:
            workspace.metadata.write_manifest()

        record = run_frozen_agent_loop(
            workspace=workspace,
            frozen_row=runtime_row,
            task_description=str(task_content["description"]),
            controls=self.controls,
            backend=self.backend,
            tokenizer=self.tokenizer,
            budget_policy=TokenBudgetPolicy(),
            tool_catalog=tool_catalog,
            reset_executor=reset_executor,
            retrieved_content=None,
            root=self.root,
            allow_grading=True,
            grade_callable=grade_callable,
            tid_callable=tid_callable,
            materialize_callable=materialize_callable,
            validate_callable=validate_callable,
            finalize_callable=finalize_callable,
            lineage_callable=lineage_callable,
        )

        # Seal the write-once index after the loop has finalized every artifact.
        seal_evidence_index()
        event_log_sha256 = hashlib.sha256(workspace.metadata.event_log_path.read_bytes()).hexdigest()
        materialized_row_path = workspace.workspace_root / "materialized_trial_row.json"
        materialized_row_sha256 = hashlib.sha256(materialized_row_path.read_bytes()).hexdigest()
        evidence_index_sha256 = hashlib.sha256(workspace.metadata.artifact_index_path.read_bytes()).hexdigest()
        
        qualified = record.status == "PASS" and grade_state.get("matched") is True
        proof = (
            TrialAcceptanceProof(
                infrastructure_valid=True,
                reset_integrity_passed=True,
                trial_acceptance_valid=True,
                counts_toward_cell_n=True,
                schema_validation_passed=True,
                evidence_hashes_resolved=True,
                unique_accepted_attempt=True,
                event_log_sha256=event_log_sha256,
                materialized_row_sha256=materialized_row_sha256,
                evidence_index_sha256=evidence_index_sha256,
            )
            if qualified
            else None
        )
        
        invalid_reason = None
        if not qualified:
            detail = "; ".join(record.notes) if record.notes else "no additional parser detail"
            invalid_reason = f"{record.termination_reason} at {record.termination_state}: {detail}"

        return ExecutedTrialResult(
            frozen_row_id=frozen_row_key(row),
            target_trial_id=str(row.trial_id),
            attempt_id=str(attempt_id),
            attempt_index=attempt_index,
            parent_attempt_id=parent_attempt_id,
            raw_attempt_directory=workspace.workspace_root,
            elapsed_seconds=record.elapsed_seconds,
            pipeline_executed=True,
            synthetic_fixture=self.synthetic_fixture,
            official_trial=self.official_trial,
            counts_for_phase5=self.counts_for_phase5,
            publication_evidence=self.publication_evidence,
            acceptance_proof=proof,
            invalid_reason=invalid_reason,
            orphaned=False,
        )
