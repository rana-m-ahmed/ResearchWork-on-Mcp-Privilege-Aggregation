from __future__ import annotations

import pytest

from phase5.domain import (
    ArtifactId,
    AttemptId,
    BatchId,
    DatasetVersion,
    DefenseCondition,
    Density,
    EventId,
    FrozenRowId,
    MetadataSurfaceCondition,
    ModelSlot,
    RunId,
    TrialId,
    TrialPhase,
)
from phase5.domain.errors import IdentifierValidationError


def test_valid_identifiers_round_trip() -> None:
    dataset = DatasetVersion.parse("P5-DV-1.0.0-A7C91E42")
    trial_id = TrialId.parse("kaggle-01")
    frozen_row_id = FrozenRowId.parse("row_001")
    run_id = RunId.build(dataset=str(dataset), model=ModelSlot.M1, utcdate="20260705", session="ABCDEF12")
    batch_id = BatchId.build(
        dataset=str(dataset),
        workload=TrialPhase.PHASE5_ADVERSARIAL_CORE,
        model=ModelSlot.M1,
        density_or_mix=Density.D3,
        surface_or_mix=MetadataSurfaceCondition.POISON_TD,
        defense=DefenseCondition.BASELINE,
        run_token="ABCDEF12",
        slice_token="A1B2",
    )
    attempt_id = AttemptId.build(trial_id, 7, "ABCDEF12")
    event_id = EventId.build(attempt_id, 42)
    artifact_id = ArtifactId.build("A1B2C3D4E5F60708", "checkpoint")

    assert str(dataset) == "P5-DV-1.0.0-A7C91E42"
    assert str(trial_id) == "kaggle-01"
    assert str(frozen_row_id) == "row_001"
    assert str(run_id) == "P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260705-ABCDEF12"
    assert str(batch_id).startswith("P5BAT-P5-DV-1.0.0-A7C91E42")
    assert str(attempt_id) == "P5ATT-kaggle-01-A007-ABCDEF12"
    assert str(event_id) == "P5EVT-P5ATT-kaggle-01-A007-ABCDEF12-0042"
    assert str(artifact_id) == "P5ART-A1B2C3D4E5F60708-checkpoint"


@pytest.mark.parametrize("attempt_index", [0, 1, 7, 42, 999])
def test_identifier_round_trips_over_sample_space(attempt_index: int) -> None:
    trial_id = TrialId.parse("kaggle-01")
    attempt_id = AttemptId.build(trial_id, attempt_index, "ABCDEF12")
    assert AttemptId.parse(str(attempt_id)) == attempt_id

    event_id = EventId.build(attempt_id, attempt_index)
    assert EventId.parse(str(event_id)) == event_id


@pytest.mark.parametrize(
    ("factory", "value"),
    [
        (DatasetVersion.parse, "P5-DV-1.0-A7C91E42"),
        (RunId.parse, "P5RUN-P5-DV-1.0.0-A7C91E42-M9-20260705-ABCDEF12"),
        (TrialId.parse, "bad id"),
        (FrozenRowId.parse, ""),
        (BatchId.parse, "P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D2-POISON_TD-BASELINE-ABCDEF12-A1B2"),
        (AttemptId.parse, "P5ATT-kaggle-01-A7-ABCDEF12"),
        (EventId.parse, "P5EVT-P5ATT-kaggle-01-A007-ABCDEF12-42"),
        (ArtifactId.parse, "P5ART-xyz-checkpoint"),
    ],
)
def test_invalid_identifiers_fail_closed(factory, value) -> None:
    with pytest.raises(IdentifierValidationError):
        factory(value)


def test_attempt_and_event_builders_reject_bad_ranges() -> None:
    with pytest.raises(IdentifierValidationError):
        AttemptId.build("kaggle-01", 1000, "ABCDEF12")
    with pytest.raises(IdentifierValidationError):
        EventId.build("P5ATT-kaggle-01-A007-ABCDEF12", 10000)
