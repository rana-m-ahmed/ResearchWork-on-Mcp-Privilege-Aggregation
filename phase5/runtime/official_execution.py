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
    DuplicateAcceptedAttemptError,
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
    """Select frozen rows and execute each through an explicit real pipeline."""

    queue_bundle: FrozenQueueBundle
    pipeline: RealTrialPipeline
    lineage_store: AttemptLineageStore
    session: CampaignSession
    dataset_version: str
    real_execution_adapter: bool = True

    def __post_init__(self) -> None:
        if getattr(self.pipeline, "real_pipeline", False) is not True:
            raise OfficialDispatchBlockedError("a planning or synthetic-result processor is not a real trial pipeline")
        if getattr(self.pipeline, "synthetic_fixture", False) is not True:
            raise OfficialDispatchBlockedError("I17E development adapter permits synthetic fixtures only")
        if self.session.state is not SessionState.SEALED:
            raise OfficialDispatchBlockedError("batch execution requires an active valid seal")
        if not self.dataset_version:
            raise MissingFrozenSettingError("execution adapter requires an explicit dataset version")

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
        existing = self.lineage_store.load_records()
        accepted_targets = {record.target_trial_id for record in existing if record.accepted_attempt}
        qualification_accepted = 0
        elapsed_seconds = 0.0
        result_digests: list[str] = []

        for row in self._rows_for_batch(batch):
            target_trial_id = str(row.trial_id)
            if target_trial_id in accepted_targets:
                raise DuplicateAcceptedAttemptError(f"finalized accepted target must not be rerun: {target_trial_id}")
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
            result.validate_development_boundary()
            if result.target_trial_id != target_trial_id or result.frozen_row_id != frozen_row_key(row):
                raise SchemaInvariantError("trial pipeline returned mismatched frozen target identity")
            if result.attempt_index != attempt_index or result.parent_attempt_id != parent_attempt_id:
                raise SchemaInvariantError("trial pipeline returned invalid attempt lineage")

            qualified = result.qualification_accepted
            qualification_accepted += int(qualified)
            elapsed_seconds += result.elapsed_seconds
            lineage = AttemptLineageRecord(
                dataset_version=self.dataset_version,
                frozen_row_id=result.frozen_row_id,
                target_trial_id=result.target_trial_id,
                attempt_id=result.attempt_id,
                attempt_index=result.attempt_index,
                parent_attempt_id=result.parent_attempt_id,
                run_id=self.session.run_id,
                batch_id=batch.batch_id,
                attempt_status="SYNTHETIC_QUALIFIED" if qualified else ("ORPHAN" if result.orphaned else "INVALID"),
                invalid_reason=result.invalid_reason,
                counts_toward_cell_n=False,
                accepted_attempt=False,
                raw_attempt_directory=result.raw_attempt_directory,
            )
            self.lineage_store.append(lineage)
            existing = (*existing, lineage)
            result_digests.append(
                _sha256_payload(
                    {
                        "attempt_id": result.attempt_id,
                        "qualification_accepted": qualified,
                        "target_trial_id": result.target_trial_id,
                    }
                )
            )

        return CampaignBatchResult(
            batch_id=batch.batch_id,
            accepted_count=0,
            finalized=False,
            estimated_seconds=elapsed_seconds or float(batch.row_count * p95_trial_seconds),
            batch_hash=_sha256_payload(
                {
                    "batch_id": batch.batch_id,
                    "qualification_accepted_count": qualification_accepted,
                    "result_digests": result_digests,
                }
            ),
            status="SYNTHETIC_QUALIFIED",
        )


def refuse_official_dispatch(*, dataset_version: str, source_tag: str) -> None:
    """Keep official dispatch locked until post-qualification authorization exists."""

    if dataset_version != OFFICIAL_V3_DATASET_VERSION or source_tag != OFFICIAL_V3_SOURCE_TAG:
        raise OfficialDispatchBlockedError("official dispatch source or dataset does not match the required v3 binding")
    raise OfficialDispatchBlockedError(
        "official dispatch remains prohibited during I17E development and qualification"
    )
