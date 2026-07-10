from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase5.campaign import (
    CampaignBatchResult,
    CampaignBarrierController,
    build_dashboard,
    build_resume_plan,
    load_campaign_plan,
    run_campaign,
)
from phase5.domain import (
    BatchId,
    DefenseCondition,
    Density,
    MetadataSurfaceCondition,
    ModelSlot,
    Phase5Session,
    SessionState,
    TrialPhase,
)
from phase5.domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, Phase5Error, SessionTransitionError
from phase5.seal import perform_sync_barrier
from phase5.guards import scan_text_for_forbidden_analysis
from phase5.runtime.session import CampaignSession


class FakeExecutedBatchProcessor:
    real_execution_adapter = True

    def __init__(self, *, estimated_seconds: float | None = None) -> None:
        self.estimated_seconds = estimated_seconds

    def __call__(self, batch, p95_seconds):
        return CampaignBatchResult(
            batch_id=batch.batch_id,
            accepted_count=batch.row_count,
            finalized=True,
            estimated_seconds=self.estimated_seconds or float(batch.row_count * p95_seconds),
            batch_hash="f" * 64,
        )


def _batch_id() -> BatchId:
    return BatchId.build(
        "P5-DV-1.0.0-A7C91E42",
        TrialPhase.PHASE5_ADVERSARIAL_CORE,
        ModelSlot.M1,
        Density.D3,
        MetadataSurfaceCondition.POISON_TD,
        DefenseCondition.BASELINE,
        "ABCDEF12",
        "1A2B",
    )


def test_campaign_session_transitions_and_resume_guardrails() -> None:
    session = CampaignSession.open(
        model_slot=ModelSlot.M1,
        batch_id=_batch_id(),
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        time_to_safety_horizon_seconds=27000.0,
    )

    assert session.state is SessionState.PREPARATION
    sealed = session.seal()
    assert sealed.state is SessionState.SEALED
    assert sealed.seal_epoch == 1

    with pytest.raises(SessionTransitionError):
        session.reverify_after_sync(hashes_match=True)

    closed = sealed.close_after_finalization()
    syncing = closed.begin_sync()
    synced = syncing.finish_sync()
    reverified = synced.reverify_after_sync(hashes_match=True)
    assert reverified.state is SessionState.REVERIFIED_AFTER_SYNC

    resealed = reverified.seal()
    assert resealed.state is SessionState.SEALED
    assert resealed.seal_epoch == 2


def test_campaign_post_sync_reverify_failure_fails_closed() -> None:
    session = CampaignSession.open(
        model_slot=ModelSlot.M1,
        batch_id=_batch_id(),
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        time_to_safety_horizon_seconds=27000.0,
    ).seal()

    with pytest.raises(FrozenArtifactHashError):
        perform_sync_barrier(session, reason="barrier", hashes_match=False)


def test_campaign_barrier_controller_decides_by_count_and_time_and_fails_closed() -> None:
    with pytest.raises(MissingFrozenSettingError):
        CampaignBarrierController(0, 6, 7.14)

    controller = CampaignBarrierController(
        safe_session_seconds=27000.0,
        checkpoint_barrier_interval_trials=6,
        p95_trial_seconds=7.14,
        load_overhead_seconds=112.42,
    )

    decision = controller.decide(elapsed_seconds=250.0, accepted_count=6, finalized_batch_count=1)
    assert decision.should_sync is True
    assert "accepted-count-threshold" in decision.reason

    assert controller.should_stop_before_batch(elapsed_seconds=26900.0, next_batch_row_count=50) is True


def test_campaign_plan_loads_frozen_batches_and_reconciles_hashes() -> None:
    plan = load_campaign_plan(model_slot="M1")
    assert plan.dataset_version == "P5-DV-1.0.1-A7C91E42"
    assert plan.model_load_status == "LOAD_SUCCESS"
    assert plan.total_batches == 51
    assert len(plan.batches) == 51
    assert plan.batches[0].batch_id.startswith("P5BAT-P5-DV-1.0.1-A7C91E42-phase5_adversarial_core-M1-")
    assert plan.batch_manifest_sha256
    assert plan.run_plan_sha256


def test_campaign_run_processes_multiple_batches_and_reseals() -> None:
    session, report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        until_safety_horizon=True,
        max_batches=3,
        batch_processor=FakeExecutedBatchProcessor(),
    )

    assert session.state in {SessionState.SEALED, SessionState.REVERIFIED_AFTER_SYNC}
    assert report.stop_reason == "interrupted"
    assert len(report.processed_batch_ids) == 3
    assert len(report.seal_epoch_hashes) >= 1
    assert report.remaining_batch_ids
    assert report.processed_batch_ids == tuple(batch.batch_id for batch in load_campaign_plan(model_slot="M1").batches[:3])


def test_campaign_run_resume_is_duplicate_safe() -> None:
    first_session, first_report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        until_safety_horizon=True,
        max_batches=2,
        batch_processor=FakeExecutedBatchProcessor(),
    )

    resumed_session, resumed_report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id=first_session.run_id,
        until_safety_horizon=True,
        session=first_session,
        batch_processor=FakeExecutedBatchProcessor(),
    )

    assert resumed_session.processed_batch_ids[:2] == first_report.processed_batch_ids
    assert len(set(resumed_report.processed_batch_ids)) == len(resumed_report.processed_batch_ids)
    assert resumed_report.processed_batch_ids[:2] == first_report.processed_batch_ids


def test_campaign_run_stops_before_safety_horizon() -> None:
    session, report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        until_safety_horizon=True,
        batch_processor=FakeExecutedBatchProcessor(estimated_seconds=27000.0),
    )

    assert report.stop_reason == "safety-horizon"
    assert len(report.processed_batch_ids) == 1
    assert session.state in {SessionState.REVERIFIED_AFTER_SYNC, SessionState.SEALED}


def test_campaign_rejects_load_failure_model() -> None:
    with pytest.raises(Phase5Error):
        run_campaign(
            model_slot=ModelSlot.M4,
            run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M4-20260708-ABCDEF12",
            utcdate="20260708",
            until_safety_horizon=True,
            batch_manifest_path=Path("phase5/manifests/batch_partition_manifest.json"),
            run_plan_path=Path("phase5/validation/kaggle_run_plan.json"),
        )


def test_dashboard_and_resume_reports_hide_outcome_fields() -> None:
    dashboard = build_dashboard(model_slot=ModelSlot.M1, run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12")
    resume = build_resume_plan(model_slot=ModelSlot.M1, run_id="P5RUN-P5-DV-1.0.1-A7C91E42-M1-20260708-ABCDEF12")

    dashboard_text = dashboard.to_markdown()
    resume_text = resume.to_markdown()
    combined = dashboard_text + resume_text + json.dumps(dashboard.to_mapping(), sort_keys=True)

    assert scan_text_for_forbidden_analysis(combined) == []
    for forbidden in ("outcome distribution", "ASR", "model ranking", "D3/D5", "p-values", "confidence intervals"):
        assert forbidden.lower() not in combined.lower()
