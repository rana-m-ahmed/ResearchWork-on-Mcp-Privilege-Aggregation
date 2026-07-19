from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from phase5.attempts import AttemptLineageStore
from phase5.campaign import load_campaign_plan, run_campaign
from phase5.domain import AttemptId, ModelSlot
from phase5.domain.errors import OfficialDispatchBlockedError, SchemaInvariantError
from phase5.queues import load_frozen_queue_bundle
from phase5.runtime.official_execution import (
    ExecutedTrialResult,
    RepositoryBatchExecutionAdapter,
    TrialAcceptanceProof,
    frozen_row_key,
    authorize_official_dispatch,
)
from phase5.runtime.session import CampaignSession


SHA = hashlib.sha256(b"I17E synthetic evidence").hexdigest()


def _proof(**overrides: object) -> TrialAcceptanceProof:
    values = {
        "infrastructure_valid": True,
        "reset_integrity_passed": True,
        "trial_acceptance_valid": True,
        "counts_toward_cell_n": True,
        "schema_validation_passed": True,
        "evidence_hashes_resolved": True,
        "unique_accepted_attempt": True,
        "event_log_sha256": SHA,
        "materialized_row_sha256": SHA,
        "evidence_index_sha256": SHA,
    }
    values.update(overrides)
    return TrialAcceptanceProof(**values)


class SyntheticRealPipeline:
    real_pipeline = True
    synthetic_fixture = True

    def __init__(self, root: Path, *, orphan_first: bool = False) -> None:
        self.root = root
        self.orphan_first = orphan_first
        self.calls: list[tuple[str, int, str | None]] = []

    def execute_row(self, *, row, batch, run_id, attempt_index, parent_attempt_id):
        self.calls.append((str(row.trial_id), attempt_index, parent_attempt_id))
        attempt_id = str(AttemptId.build(row.trial_id, attempt_index, "ABCDEF12"))
        attempt_root = self.root / attempt_id
        attempt_root.mkdir(parents=True, exist_ok=False)
        orphaned = self.orphan_first and attempt_index == 0
        return ExecutedTrialResult(
            frozen_row_id=frozen_row_key(row),
            target_trial_id=str(row.trial_id),
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            parent_attempt_id=parent_attempt_id,
            raw_attempt_directory=attempt_root,
            elapsed_seconds=0.01,
            pipeline_executed=True,
            synthetic_fixture=True,
            official_trial=False,
            counts_for_phase5=False,
            publication_evidence=False,
            acceptance_proof=None if orphaned else _proof(),
            invalid_reason="synthetic interruption" if orphaned else None,
            orphaned=orphaned,
        )

class OfficialRealPipeline:
    real_pipeline = True
    synthetic_fixture = False
    official_trial = True

    def __init__(self, root: Path, *, orphan_first: bool = False, invalid_reason: str | None = None) -> None:
        self.root = root
        self.orphan_first = orphan_first
        self.invalid_reason = invalid_reason
        self.calls: list[tuple[str, int, str | None]] = []

    def execute_row(self, *, row, batch, run_id, attempt_index, parent_attempt_id):
        self.calls.append((str(row.trial_id), attempt_index, parent_attempt_id))
        attempt_id = str(AttemptId.build(row.trial_id, attempt_index, "ABCDEF12"))
        attempt_root = self.root / attempt_id
        attempt_root.mkdir(parents=True, exist_ok=False)
        orphaned = self.orphan_first and attempt_index == 0
        return ExecutedTrialResult(
            frozen_row_id=frozen_row_key(row),
            target_trial_id=str(row.trial_id),
            attempt_id=attempt_id,
            attempt_index=attempt_index,
            parent_attempt_id=parent_attempt_id,
            raw_attempt_directory=attempt_root,
            elapsed_seconds=0.01,
            pipeline_executed=True,
            synthetic_fixture=False,
            official_trial=True,
            counts_for_phase5=True,
            publication_evidence=True,
            analysis_eligible=self.invalid_reason is not None,
            acceptance_proof=None if orphaned else _proof(),
            invalid_reason=self.invalid_reason or ("official interruption" if orphaned else None),
            orphaned=orphaned,
        )


def _sealed_session() -> CampaignSession:
    return CampaignSession.open(
        model_slot=ModelSlot.M1,
        run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260711-ABCDEF12",
        utcdate="20260711",
    ).seal()


def test_missing_or_unmarked_processor_blocks_campaign_dispatch() -> None:
    with pytest.raises(OfficialDispatchBlockedError):
        run_campaign(model_slot=ModelSlot.M1, until_safety_horizon=True)

    with pytest.raises(OfficialDispatchBlockedError):
        run_campaign(
            model_slot=ModelSlot.M1,
            until_safety_horizon=True,
            batch_processor=lambda batch, p95: None,
        )


def test_plan_only_cannot_create_accepted_or_finalized_counts() -> None:
    session, report = run_campaign(
        model_slot=ModelSlot.M1,
        until_safety_horizon=True,
        max_batches=1,
        plan_only=True,
    )
    assert session.accepted_finalized_count == 0
    assert session.finalized_batch_count == 0
    assert report.batch_results[0].accepted_count == 0
    assert report.batch_results[0].finalized is False
    assert report.batch_results[0].status == "PLAN_ONLY"


def test_acceptance_proof_fails_closed_on_schema_or_evidence_failure() -> None:
    with pytest.raises(SchemaInvariantError, match="schema_validation_passed"):
        _proof(schema_validation_passed=False).validate()
    with pytest.raises(SchemaInvariantError, match="event_log_sha256"):
        _proof(event_log_sha256="missing").validate()


def test_development_result_rejects_official_or_nonexecuted_output(tmp_path: Path) -> None:
    base = dict(
        frozen_row_id="core:00001:T04470",
        target_trial_id="T04470",
        attempt_id="P5ATT-T04470-A000-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
        raw_attempt_directory=tmp_path,
        elapsed_seconds=0.1,
        synthetic_fixture=True,
        official_trial=False,
        counts_for_phase5=False,
        publication_evidence=False,
        acceptance_proof=_proof(),
    )
    with pytest.raises(OfficialDispatchBlockedError, match="planning metadata"):
        ExecutedTrialResult(**base, pipeline_executed=False).validate_development_boundary()
    with pytest.raises(OfficialDispatchBlockedError, match="non-official"):
        ExecutedTrialResult(**{**base, "official_trial": True}, pipeline_executed=True).validate_development_boundary()


def test_repository_adapter_executes_frozen_rows_but_never_creates_official_counts(tmp_path: Path) -> None:
    plan = load_campaign_plan(model_slot="M1")
    pipeline = SyntheticRealPipeline(tmp_path / "attempts")
    store = AttemptLineageStore(tmp_path / "lineage.csv")
    adapter = RepositoryBatchExecutionAdapter(
        queue_bundle=load_frozen_queue_bundle(),
        pipeline=pipeline,
        lineage_store=store,
        session=_sealed_session(),
        dataset_version=plan.dataset_version,
    )

    result = adapter(plan.batches[0], plan.p95_trial_seconds)

    assert len(pipeline.calls) == plan.batches[0].row_count
    assert result.status == "SYNTHETIC_QUALIFIED"
    assert result.accepted_count == 0
    assert result.finalized is False
    records = store.load_records()
    assert len(records) == plan.batches[0].row_count
    assert all(not record.accepted_attempt and not record.counts_toward_cell_n for record in records)


def test_repository_adapter_in_official_mode_creates_accepted_counts(tmp_path: Path) -> None:
    plan = load_campaign_plan(model_slot="M1")
    pipeline = OfficialRealPipeline(tmp_path / "attempts")
    store = AttemptLineageStore(tmp_path / "lineage.csv")
    adapter = RepositoryBatchExecutionAdapter(
        queue_bundle=load_frozen_queue_bundle(),
        pipeline=pipeline,
        lineage_store=store,
        session=_sealed_session(),
        dataset_version=plan.dataset_version,
        official_mode=True,
    )

    result = adapter(plan.batches[0], plan.p95_trial_seconds)

    assert len(pipeline.calls) == plan.batches[0].row_count
    assert result.status == "OFFICIAL_FINALIZED"
    assert result.accepted_count == plan.batches[0].row_count
    assert result.finalized is True
    records = store.load_records()
    assert len(records) == plan.batches[0].row_count
    assert all(record.accepted_attempt and record.counts_toward_cell_n for record in records)


def test_official_invalid_batch_is_not_labeled_synthetic(tmp_path: Path) -> None:
    plan = load_campaign_plan(model_slot="M1")
    pipeline = OfficialRealPipeline(tmp_path / "attempts", invalid_reason="parser failure")
    store = AttemptLineageStore(tmp_path / "lineage.csv")
    adapter = RepositoryBatchExecutionAdapter(
        queue_bundle=load_frozen_queue_bundle(),
        pipeline=pipeline,
        lineage_store=store,
        session=_sealed_session(),
        dataset_version=plan.dataset_version,
        official_mode=True,
    )

    result = adapter(plan.batches[0], plan.p95_trial_seconds)

    assert result.status == "OFFICIAL_FINALIZED_NO_ACCEPTED"
    assert result.accepted_count == 0
    assert result.finalized is True
    assert all(record.attempt_status == "INVALID" for record in store.load_records())


def test_orphan_replacement_uses_new_attempt_and_parent_lineage(tmp_path: Path) -> None:
    plan = load_campaign_plan(model_slot="M1")
    pipeline = SyntheticRealPipeline(tmp_path / "attempts", orphan_first=True)
    store = AttemptLineageStore(tmp_path / "lineage.csv")
    adapter = RepositoryBatchExecutionAdapter(
        queue_bundle=load_frozen_queue_bundle(),
        pipeline=pipeline,
        lineage_store=store,
        session=_sealed_session(),
        dataset_version=plan.dataset_version,
    )
    single = plan.batches[0]
    adapter(single, plan.p95_trial_seconds)
    adapter(single, plan.p95_trial_seconds)

    first_target_calls = [call for call in pipeline.calls if call[0] == pipeline.calls[0][0]]
    assert first_target_calls[0][1:] == (0, None)
    assert first_target_calls[1][1] == 1
    assert first_target_calls[1][2] == str(AttemptId.build(first_target_calls[0][0], 0, "ABCDEF12"))


def test_unsealed_adapter_and_official_v3_dispatch_remain_blocked(tmp_path: Path) -> None:
    plan = load_campaign_plan(model_slot="M1")
    with pytest.raises(OfficialDispatchBlockedError, match="active valid seal"):
        RepositoryBatchExecutionAdapter(
            queue_bundle=load_frozen_queue_bundle(),
            pipeline=SyntheticRealPipeline(tmp_path),
            lineage_store=AttemptLineageStore(tmp_path / "lineage.csv"),
            session=CampaignSession.open(model_slot=ModelSlot.M1),
            dataset_version=plan.dataset_version,
        )
    with pytest.raises(OfficialDispatchBlockedError, match="mismatch"):
        authorize_official_dispatch(
            dataset_version="invalid-version",
            source_tag="phase5-official-source-v3",
        )
