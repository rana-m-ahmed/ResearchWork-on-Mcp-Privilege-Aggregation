from __future__ import annotations

import os
from pathlib import Path

import pytest

from phase5.domain.errors import FrozenArtifactHashError, SchemaInvariantError
from phase5.kaggle.run_planner import (
    FROZEN_TIMING_EVIDENCE_GENERATED_UTC,
    TimingEvidence,
    _exclusive_p95,
    build_kaggle_run_plan,
    build_default_batch_partition_manifest,
    load_timing_evidence,
)
from phase5.queues.pending_resolver import (
    CheckpointHistory,
    OrphanRegistryEntry,
    resolve_pending_targets,
)


def _synthetic_timing_evidence(
    *,
    p95_seconds: float,
    invalid_attempt_rate: float,
    load_seconds: float,
    status: str = "LOAD_SUCCESS",
) -> TimingEvidence:
    load_map = tuple((model_slot, load_seconds) for model_slot in ("M1", "M2", "M3", "M4"))
    load_status = tuple((model_slot, status) for model_slot in ("M1", "M2", "M3", "M4"))
    evidence_inputs = (("synthetic", "deadbeef"),)
    return TimingEvidence(
        timing_report_path=Path("synthetic_timing_report.md"),
        timing_report_sha256="deadbeef",
        evidence_generated_utc="2026-07-08T00:00:00Z",
        mean_trial_seconds=p95_seconds,
        p50_trial_seconds=p95_seconds,
        p95_trial_seconds=p95_seconds,
        trial_sample_count=8,
        invalid_attempt_rate=invalid_attempt_rate,
        safe_session_hours=7.5,
        checkpoint_frequency_trials=6,
        model_load_seconds=load_map,
        model_load_status=load_status,
        evidence_inputs=evidence_inputs,
    )


def test_default_partition_manifest_is_deterministic_and_covers_expected_targets() -> None:
    manifest = build_default_batch_partition_manifest(
        source_evidence=(("Timing report", "deadbeef"),),
        generated_utc="2026-07-08T00:00:00Z",
    )

    assert manifest.total_targets == 10200
    assert manifest.total_batches == 204
    assert [campaign.model_slot for campaign in manifest.model_campaigns] == ["M1", "M2", "M3", "M4"]
    assert manifest.model_campaigns[0].target_count == 2550
    assert [partition.batch_count for partition in manifest.model_campaigns[0].workload_partitions] == [27, 12, 12]
    assert manifest.to_json() == manifest.to_json()
    assert manifest.to_markdown() == manifest.to_markdown()


def test_immutable_manifest_rejects_changed_content(tmp_path: Path) -> None:
    manifest_path = tmp_path / "batch_partition_manifest.json"
    markdown_path = tmp_path / "batch_partition_manifest.md"
    manifest = build_default_batch_partition_manifest(
        source_evidence=(("Timing report", "deadbeef"),),
        generated_utc="2026-07-08T00:00:00Z",
    )

    manifest.write(manifest_path, markdown_path)
    original = manifest_path.read_text(encoding="utf-8")
    manifest_path.write_text(original.replace('"batch_size": 50', '"batch_size": 51'), encoding="utf-8")

    with pytest.raises(FrozenArtifactHashError):
        manifest.write(manifest_path, markdown_path)


def test_pending_resolver_accepts_orphans_and_rejects_divergent_histories() -> None:
    resolution = resolve_pending_targets(
        ["M1:core:0001", "M1:core:0002"],
        histories=[
            CheckpointHistory(
                target_key="M1:core:0001",
                attempt_index=0,
                checkpoint_hash="aaa",
                parent_checkpoint_hash=None,
                chain_id="chain-1",
                accepted=True,
            ),
            CheckpointHistory(
                target_key="M1:core:0002",
                attempt_index=0,
                checkpoint_hash="bbb",
                parent_checkpoint_hash=None,
                chain_id="chain-2",
            ),
        ],
        orphan_registry=[
            OrphanRegistryEntry(
                target_key="M1:core:0002",
                next_attempt_index=3,
                rerun_link="phase4_5/dryrun_results/kaggle_smoke/local-02.json",
                chain_id="chain-2",
            )
        ],
        accepted_target_keys=["M1:core:0001"],
    )

    assert resolution.accepted_targets[0].target_key == "M1:core:0001"
    assert resolution.accepted_targets[0].next_attempt_index == 1
    assert resolution.orphan_targets[0].target_key == "M1:core:0002"
    assert resolution.orphan_targets[0].next_attempt_index == 3
    assert "not reselected" in (resolution.accepted_targets[0].note or "")

    with pytest.raises(SchemaInvariantError):
        resolve_pending_targets(
            ["M1:core:0003"],
            histories=[
                CheckpointHistory(
                    target_key="M1:core:0003",
                    attempt_index=0,
                    checkpoint_hash="aaa",
                    parent_checkpoint_hash=None,
                    chain_id="chain-a",
                ),
                CheckpointHistory(
                    target_key="M1:core:0003",
                    attempt_index=1,
                    checkpoint_hash="bbb",
                    parent_checkpoint_hash="aaa",
                    chain_id="chain-b",
                ),
            ],
        )


def test_timing_formula_uses_real_phase45_evidence() -> None:
    evidence = load_timing_evidence(root=Path.cwd())
    manifest = build_default_batch_partition_manifest(
        source_evidence=evidence.evidence_inputs,
        generated_utc="2026-07-08T00:00:00Z",
    )
    plan = build_kaggle_run_plan(timing_evidence=evidence, batch_manifest=manifest)

    assert evidence.p95_trial_seconds == 7.14
    assert evidence.invalid_attempt_rate == 0.0
    assert manifest.total_targets == 10200
    assert plan.total_targets == 10200
    assert plan.projected_total_sessions == 4
    assert all(model.projected_sessions == 1 for model in plan.model_plans)
    assert all(model.batches_per_session == 51 for model in plan.model_plans)
    assert plan.projected_total_gpu_hours > 0


def test_timing_evidence_timestamp_ignores_checkout_mtime(tmp_path: Path) -> None:
    source = Path("phase4_5/validation/phase45_kaggle_quota_feasibility_report.md")
    timing_report = tmp_path / source.name
    timing_report.write_bytes(source.read_bytes())
    os.utime(timing_report, (0, 0))

    evidence = load_timing_evidence(root=Path.cwd(), timing_report_path=timing_report)

    assert evidence.evidence_generated_utc == FROZEN_TIMING_EVIDENCE_GENERATED_UTC


def test_synthetic_timing_plans_one_and_multiple_sessions_per_model() -> None:
    one_session_evidence = _synthetic_timing_evidence(
        p95_seconds=7.14,
        invalid_attempt_rate=0.0,
        load_seconds=100.0,
    )
    manifest = build_default_batch_partition_manifest(
        source_evidence=one_session_evidence.evidence_inputs,
        generated_utc="2026-07-08T00:00:00Z",
    )
    one_session_plan = build_kaggle_run_plan(
        timing_evidence=one_session_evidence,
        batch_manifest=manifest,
    )
    assert all(model.projected_sessions == 1 for model in one_session_plan.model_plans)
    assert one_session_plan.projected_total_sessions == 4

    multiple_session_evidence = _synthetic_timing_evidence(
        p95_seconds=12.0,
        invalid_attempt_rate=0.0,
        load_seconds=3600.0,
    )
    multiple_session_plan = build_kaggle_run_plan(
        timing_evidence=multiple_session_evidence,
        batch_manifest=manifest,
    )
    assert all(model.projected_sessions == 2 for model in multiple_session_plan.model_plans)
    assert multiple_session_plan.projected_total_sessions == 8


def test_zero_or_invalid_timing_data_fails_closed() -> None:
    manifest = build_default_batch_partition_manifest(
        source_evidence=(("Timing report", "deadbeef"),),
        generated_utc="2026-07-08T00:00:00Z",
    )

    with pytest.raises(SchemaInvariantError):
        build_kaggle_run_plan(
            timing_evidence=_synthetic_timing_evidence(
                p95_seconds=0.0,
                invalid_attempt_rate=0.0,
                load_seconds=100.0,
            ),
            batch_manifest=manifest,
        )

    with pytest.raises(SchemaInvariantError):
        build_kaggle_run_plan(
            timing_evidence=_synthetic_timing_evidence(
                p95_seconds=7.14,
                invalid_attempt_rate=1.0,
                load_seconds=100.0,
            ),
            batch_manifest=manifest,
        )


def test_exclusive_p95_requires_samples() -> None:
    with pytest.raises(SchemaInvariantError):
        _exclusive_p95([])
