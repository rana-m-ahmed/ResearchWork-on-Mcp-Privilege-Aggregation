"""Frozen Phase 5 enums."""

from __future__ import annotations

from enum import Enum

from .errors import UnknownEnumValueError


class Phase5StrEnum(str, Enum):
    """String enum with fail-closed parsing."""

    @classmethod
    def from_value(cls, value: str) -> "Phase5StrEnum":
        try:
            return cls(value)
        except ValueError as exc:  # pragma: no cover - defensive
            raise UnknownEnumValueError(f"unknown {cls.__name__} value: {value!r}") from exc


class ModelSlot(Phase5StrEnum):
    M1 = "M1"
    M2 = "M2"
    M3 = "M3"
    M4 = "M4"


class Density(Phase5StrEnum):
    D1 = "D1"
    D3 = "D3"
    D5 = "D5"


class TrialPhase(Phase5StrEnum):
    PHASE5_ADVERSARIAL_CORE = "phase5_adversarial_core"
    PHASE5_ADVERSARIAL_DEFENSE = "phase5_adversarial_defense"
    PHASE5_UTILITY_PRESERVATION = "phase5_utility_preservation"


class MetadataSurfaceCondition(Phase5StrEnum):
    CLEAN = "CLEAN"
    POISON_TD = "POISON_TD"
    POISON_CA = "POISON_CA"


class AttackFamily(Phase5StrEnum):
    DIRECT_OVERRIDE = "DIRECT_OVERRIDE"
    CROSS_CAPABILITY_ESCALATION = "CROSS_CAPABILITY_ESCALATION"
    DATA_EXFILTRATION = "DATA_EXFILTRATION"
    NONE = "NONE"


class DefenseCondition(Phase5StrEnum):
    BASELINE = "BASELINE"
    IHR_SPCE = "IHR_SPCE"


class PayloadCondition(Phase5StrEnum):
    NONE = "NONE"
    PHASE1_HASH_AUTHORIZED = "PHASE1_HASH_AUTHORIZED"


class TrialOutcome(Phase5StrEnum):
    CRITICAL_EXPLOIT = "CRITICAL_EXPLOIT"
    ATTACK_SUCCESS = "ATTACK_SUCCESS"
    HIJACK_ATTEMPT = "HIJACK_ATTEMPT"
    BENIGN_RESISTANCE_WITH_TASK_SUCCESS = "BENIGN_RESISTANCE_WITH_TASK_SUCCESS"
    BENIGN_RESISTANCE_WITH_TASK_FAILURE = "BENIGN_RESISTANCE_WITH_TASK_FAILURE"
    MODEL_COMPETENCE_FAILURE = "MODEL_COMPETENCE_FAILURE"
    INFRASTRUCTURE_FAILURE = "INFRASTRUCTURE_FAILURE"
    RESET_FAILURE = "RESET_FAILURE"


class SessionState(Phase5StrEnum):
    PREPARATION = "PREPARATION"
    SEALED = "SEALED"
    CLOSED_AFTER_FINALIZATION = "CLOSED_AFTER_FINALIZATION"
    UNSEALED_SYNCING = "UNSEALED_SYNCING"
    UNSEALED_SYNCED = "UNSEALED_SYNCED"
    REVERIFIED_AFTER_SYNC = "REVERIFIED_AFTER_SYNC"
    QUARANTINED = "QUARANTINED"
    TERMINAL = "TERMINAL"
