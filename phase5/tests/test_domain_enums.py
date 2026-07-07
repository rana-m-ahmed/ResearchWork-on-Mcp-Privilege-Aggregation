from __future__ import annotations

import pytest

from phase5.domain import AttackFamily, DefenseCondition, Density, MetadataSurfaceCondition, ModelSlot, PayloadCondition, SessionState, TrialOutcome, TrialPhase
from phase5.domain.errors import UnknownEnumValueError


@pytest.mark.parametrize(
    ("enum_cls", "value"),
    [
        (ModelSlot, "M1"),
        (Density, "D3"),
        (TrialPhase, "phase5_utility_preservation"),
        (MetadataSurfaceCondition, "POISON_CA"),
        (AttackFamily, "NONE"),
        (DefenseCondition, "IHR_SPCE"),
        (PayloadCondition, "PHASE1_HASH_AUTHORIZED"),
        (TrialOutcome, "MODEL_COMPETENCE_FAILURE"),
        (SessionState, "UNSEALED_SYNCED"),
    ],
)
def test_known_enum_values_parse(enum_cls, value) -> None:
    assert enum_cls.from_value(value).value == value


@pytest.mark.parametrize(
    ("enum_cls", "value"),
    [
        (ModelSlot, "M9"),
        (Density, "D2"),
        (TrialPhase, "phase5_unknown"),
        (MetadataSurfaceCondition, "SURFACE_X"),
        (AttackFamily, "TOOLING"),
        (DefenseCondition, "FORCED"),
        (PayloadCondition, "NONE_PHASE3_BENIGN"),
        (TrialOutcome, "ATTACK_CONFIRMED"),
        (SessionState, "SYNCED"),
    ],
)
def test_unknown_enum_values_fail_closed(enum_cls, value) -> None:
    with pytest.raises(UnknownEnumValueError):
        enum_cls.from_value(value)
