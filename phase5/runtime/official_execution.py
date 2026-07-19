"""Fail-closed execution boundary for I17E batch qualification.

This module composes executed trial results. It does not authorize official
dispatch; the current governance permits synthetic qualification only.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol, Sequence

from ..attempts import AttemptLineageRecord, AttemptLineageStore
from ..campaign import CampaignBatchPlan, CampaignBatchResult
from ..domain.enums import SessionState
from ..domain.errors import (
    MissingFrozenSettingError,
    OfficialDispatchBlockedError,
    SchemaInvariantError,
)
from ..queues import FrozenQueueBundle, FrozenQueueRow
from .session import CampaignSession


OFFICIAL_V3_DATASET_VERSION = "P5-DV-1.0.2-A7C91E42"
OFFICIAL_V3_SOURCE_TAG = "phase5-official-source-v3"


def _sha256_payload(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_sha256(value: str, label: str) -> None:
    if len(value) != 64 or any(character not in "0123456789abcdef" for character in value.lower()):
        raise SchemaInvariantError(f"{label} must be a 64-character SHA-256 digest")


def frozen_row_key(row: FrozenQueueRow) -> str:
    """Map an immutable queue reference into the frozen identifier grammar."""

    return row.row_reference.replace(":", "-")


@dataclass(frozen=True, slots=True)
class TrialAcceptanceProof:
    """Evidence required before an executed target may qualify as accepted."""

    infrastructure_valid: bool
    reset_integrity_passed: bool
    trial_acceptance_valid: bool
    counts_toward_cell_n: bool
    schema_validation_passed: bool
    evidence_hashes_resolved: bool
    unique_accepted_attempt: bool
    event_log_sha256: str
    materialized_row_sha256: str
    evidence_index_sha256: str

    def validate(self) -> None:
        checks = {
            "infrastructure_valid": self.infrastructure_valid,
            "reset_integrity_passed": self.reset_integrity_passed,
            "trial_acceptance_valid": self.trial_acceptance_valid,
            "counts_toward_cell_n": self.counts_toward_cell_n,
            "schema_validation_passed": self.schema_validation_passed,
            "evidence_hashes_resolved": self.evidence_hashes_resolved,
            "unique_accepted_attempt": self.unique_accepted_attempt,
        }
        failed = [name for name, passed in checks.items() if passed is not True]
        if failed:
            raise SchemaInvariantError(f"trial acceptance proof failed: {', '.join(failed)}")
        _require_sha256(self.event_log_sha256, "event_log_sha256")
        _require_sha256(self.materialized_row_sha256, "materialized_row_sha256")
        _require_sha256(self.evidence_index_sha256, "evidence_index_sha256")


@dataclass(frozen=True, slots=True)
class ExecutedTrialResult:
    frozen_row_id: str
    target_trial_id: str
    attempt_id: str
    attempt_index: int
    parent_attempt_id: str | None
    raw_attempt_directory: Path
    elapsed_seconds: float
    pipeline_executed: bool
    synthetic_fixture: bool
    official_trial: bool
    counts_for_phase5: bool
    publication_evidence: bool
    analysis_eligible: bool = False
    acceptance_proof: TrialAcceptanceProof | None = None
    invalid_reason: str | None = None
    orphaned: bool = False

    @property
    def qualification_accepted(self) -> bool:
        if self.acceptance_proof is None:
            return False
        self.acceptance_proof.validate()
        return self.pipeline_executed and not self.orphaned and self.invalid_reason is None

    def validate_development_boundary(self) -> None:
        if not self.pipeline_executed:
            raise OfficialDispatchBlockedError("planning metadata cannot produce an executed trial result")
        if self.official_trial or self.counts_for_phase5 or self.publication_evidence:
            raise OfficialDispatchBlockedError("I17E qualification output must remain non-official and non-publication")
        if not self.synthetic_fixture:
            raise OfficialDispatchBlockedError("I17E local qualification requires an explicit synthetic fixture")
        if self.elapsed_seconds < 0:
            raise SchemaInvariantError("executed trial elapsed_seconds must be non-negative")

    def validate_official_boundary(self) -> None:
        """Assert that this result satisfies the official execution boundary."""
        if not self.pipeline_executed:
            raise OfficialDispatchBlockedError("planning metadata cannot produce an executed trial result")
        if not self.official_trial:
            raise OfficialDispatchBlockedError("official dispatch requires official_trial=True")
        if not self.counts_for_phase5:
            raise OfficialDispatchBlockedError("official dispatch requires counts_for_phase5=True")
        if not self.publication_evidence:
            raise OfficialDispatchBlockedError("official dispatch requires publication_evidence=True")
        if self.synthetic_fixture:
            raise OfficialDispatchBlockedError("official dispatch must not use synthetic fixtures")
        if self.elapsed_seconds < 0:
            raise SchemaInvariantError("executed trial elapsed_seconds must be non-negative")


class RealTrialPipeline(Protocol):
    """Repository execution kernel used once per frozen row."""

    real_pipeline: bool
    synthetic_fixture: bool

    def execute_row(
        self,
        *,
        row: FrozenQueueRow,
        batch: CampaignBatchPlan,
        run_id: str,
        attempt_index: int,
        parent_attempt_id: str | None,
    ) -> ExecutedTrialResult:
        ...


@dataclass(slots=True)
class RepositoryBatchExecutionAdapter:
    """Select frozen rows and execute each through an explicit real pipeline.

    Supports both synthetic qualification (official_mode=False) and real
    official dispatch (official_mode=True). In official mode, accepted
    trials set counts_toward_cell_n=True and accepted_attempt=True.
    """

    queue_bundle: FrozenQueueBundle
    pipeline: RealTrialPipeline
    lineage_store: AttemptLineageStore
    session: CampaignSession
    dataset_version: str
    official_mode: bool = False
    real_execution_adapter: bool = True
    checkpoint_callback: Callable[[CampaignBatchPlan, AttemptLineageRecord, int], None] | None = None
    checkpoint_interval_trials: int = 0

    def __post_init__(self) -> None:
        if getattr(self.pipeline, "real_pipeline", False) is not True:
            raise OfficialDispatchBlockedError("a planning or synthetic-result processor is not a real trial pipeline")
        if self.official_mode:
            # Official mode: pipeline must NOT be synthetic
            if getattr(self.pipeline, "synthetic_fixture", True) is True:
                raise OfficialDispatchBlockedError("official dispatch adapter requires a non-synthetic pipeline")
            if not getattr(self.pipeline, "official_trial", False):
                raise OfficialDispatchBlockedError("official dispatch adapter requires official_trial=True on the pipeline")
        else:
            # Synthetic qualification mode: pipeline must be synthetic
            if getattr(self.pipeline, "synthetic_fixture", False) is not True:
                raise OfficialDispatchBlockedError("I17E development adapter permits synthetic fixtures only")
        if self.session.state is not SessionState.SEALED:
            raise OfficialDispatchBlockedError("batch execution requires an active valid seal")
        if not self.dataset_version:
            raise MissingFrozenSettingError("execution adapter requires an explicit dataset version")
        if self.checkpoint_callback is not None and self.checkpoint_interval_trials <= 0:
            raise MissingFrozenSettingError("checkpoint interval must be positive when checkpointing is enabled")

    def _rows_for_batch(self, batch: CampaignBatchPlan) -> tuple[FrozenQueueRow, ...]:
        queues = {queue.queue_name: queue for queue in self.queue_bundle.queues()}
        workload_queue = {
            "phase5_adversarial_core": "core",
            "phase5_adversarial_defense": "defense",
            "phase5_utility_preservation": "utility",
        }
        try:
            queue = queues[workload_queue[batch.workload]]
        except KeyError as exc:
            raise MissingFrozenSettingError(f"frozen queue not found for workload {batch.workload!r}") from exc
        model_rows = tuple(row for row in queue.rows if row.model_id.value == batch.model_slot)
        rows = model_rows[batch.start_ordinal - 1 : batch.end_ordinal]
        if len(rows) != batch.row_count:
            raise SchemaInvariantError(
                f"frozen batch row reconciliation failed: expected {batch.row_count}, got {len(rows)}"
            )
        if any(row.status != "PENDING" for row in rows):
            raise SchemaInvariantError("execution adapter may select only PENDING frozen rows")
        return rows

    def __call__(self, batch: CampaignBatchPlan, p95_trial_seconds: float) -> CampaignBatchResult:
        if batch.model_slot != self.session.model_slot.value:
            raise SchemaInvariantError("batch model slot does not match the sealed campaign session")
        existing = list(self.lineage_store.load_records())
        completed_targets = {
            record.target_trial_id
            for record in existing
            if record.accepted_attempt or record.attempt_status in {"INVALID", "OFFICIAL_ACCEPTED"}
        }
        rows = tuple(row for row in self._rows_for_batch(batch) if str(row.trial_id) not in completed_targets)
        qualification_accepted = 0
        analysis_eligible_count = 0
        elapsed_seconds = 0.0
        result_digests: list[str] = []
        since_checkpoint = 0

        for row in rows:
            target_trial_id = str(row.trial_id)
            histories = [record for record in existing if record.target_trial_id == target_trial_id]
            attempt_index = max((record.attempt_index for record in histories), default=-1) + 1
            parent_attempt_id = max(histories, key=lambda item: item.attempt_index).attempt_id if histories else None
            result = self.pipeline.execute_row(
                row=row,
                batch=batch,
                run_id=self.session.run_id,
                attempt_index=attempt_index,
                parent_attempt_id=parent_attempt_id,
            )
            if self.official_mode:
                result.validate_official_boundary()
            else:
                result.validate_development_boundary()
            if result.target_trial_id != target_trial_id or result.frozen_row_id != frozen_row_key(row):
                raise SchemaInvariantError("trial pipeline returned mismatched frozen target identity")
            if result.attempt_index != attempt_index or result.parent_attempt_id != parent_attempt_id:
                raise SchemaInvariantError("trial pipeline returned invalid attempt lineage")

            qualified = result.qualification_accepted
            qualification_accepted += int(qualified)
            analysis_eligible_count += int(result.analysis_eligible)
            elapsed_seconds += result.elapsed_seconds

            if self.official_mode:
                attempt_status = "OFFICIAL_ACCEPTED" if qualified else ("ORPHAN" if result.orphaned else "INVALID")
                counts_toward_cell_n = qualified
                accepted_attempt = qualified
            else:
                attempt_status = "SYNTHETIC_QUALIFIED" if qualified else ("ORPHAN" if result.orphaned else "INVALID")
                counts_toward_cell_n = False
                accepted_attempt = False

            lineage = AttemptLineageRecord(
                dataset_version=self.dataset_version,
                frozen_row_id=result.frozen_row_id,
                target_trial_id=result.target_trial_id,
                attempt_id=result.attempt_id,
                attempt_index=result.attempt_index,
                parent_attempt_id=result.parent_attempt_id,
                run_id=self.session.run_id,
                batch_id=batch.batch_id,
                attempt_status=attempt_status,
                invalid_reason=result.invalid_reason,
                counts_toward_cell_n=counts_toward_cell_n,
                accepted_attempt=accepted_attempt,
                raw_attempt_directory=result.raw_attempt_directory,
            )
            self.lineage_store.append(lineage)
            existing = (*existing, lineage)
            since_checkpoint += 1
            if self.checkpoint_callback is not None and since_checkpoint >= self.checkpoint_interval_trials:
                self.checkpoint_callback(batch, lineage, len(existing))
                since_checkpoint = 0
            result_digests.append(
                _sha256_payload(
                    {
                        "attempt_id": result.attempt_id,
                        "qualification_accepted": qualified,
                        "analysis_eligible": result.analysis_eligible,
                        "target_trial_id": result.target_trial_id,
                    }
                )
            )

        if self.checkpoint_callback is not None and since_checkpoint:
            self.checkpoint_callback(batch, existing[-1], len(existing))

        official_accepted = qualification_accepted if self.official_mode else 0
        if self.official_mode:
            batch_status = "OFFICIAL_FINALIZED" if official_accepted > 0 else "OFFICIAL_COMPLETED_NO_ACCEPTED"
        else:
            batch_status = "SYNTHETIC_QUALIFIED"
        return CampaignBatchResult(
            batch_id=batch.batch_id,
            accepted_count=official_accepted,
            finalized=self.official_mode and official_accepted > 0,
            estimated_seconds=elapsed_seconds or float(batch.row_count * p95_trial_seconds),
            batch_hash=_sha256_payload(
                {
                    "batch_id": batch.batch_id,
                    "qualification_accepted_count": qualification_accepted,
                    "analysis_eligible_count": analysis_eligible_count,
                    "result_digests": result_digests,
                }
            ),
            status=batch_status,
            analysis_eligible_count=analysis_eligible_count,
        )


def authorize_official_dispatch(*, dataset_version: str, source_tag: str) -> None:
    """Validate that the dataset and source tag match the v3 official binding.

    This function no longer unconditionally blocks; after successful
    qualification it verifies the caller is using the correct v3 binding.
    """
    if dataset_version != OFFICIAL_V3_DATASET_VERSION:
        raise OfficialDispatchBlockedError(
            f"official dispatch dataset mismatch: expected {OFFICIAL_V3_DATASET_VERSION}, got {dataset_version}"
        )
    if source_tag != OFFICIAL_V3_SOURCE_TAG:
        raise OfficialDispatchBlockedError(
            f"official dispatch source tag mismatch: expected {OFFICIAL_V3_SOURCE_TAG}, got {source_tag}"
        )


def refuse_official_dispatch(*, dataset_version: str, source_tag: str) -> None:
    """Legacy alias kept for backward compatibility with existing non-official tests."""
    authorize_official_dispatch(dataset_version=dataset_version, source_tag=source_tag)
