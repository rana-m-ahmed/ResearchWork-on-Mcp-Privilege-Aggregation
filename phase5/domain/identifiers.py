"""Typed Phase 5 identifier primitives."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from .errors import IdentifierValidationError
from .enums import DefenseCondition, Density, MetadataSurfaceCondition, ModelSlot, TrialPhase


_SESSION_TOKEN_PATTERN = re.compile(r"^[A-Z0-9]{8}$")
_SHORT_TOKEN_PATTERN = re.compile(r"^[A-Z0-9]{4}$")
_ARTIFACT_TYPE_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_TRIAL_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_FROZEN_ROW_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_DATASET_VERSION_PATTERN = re.compile(r"^P5-DV-\d+\.\d+\.\d+-[A-F0-9]{8}$")
_RUN_ID_PATTERN = re.compile(
    r"^P5RUN-(?P<dataset>.+)-(?P<model>M[1-4])-(?P<utcdate>\d{8})-(?P<session>[A-Z0-9]{8})$"
)
_BATCH_ID_PATTERN = re.compile(
    r"^P5BAT-(?P<dataset>.+)-(?P<workload>phase5_adversarial_core|phase5_adversarial_defense|phase5_utility_preservation)-"
    r"(?P<model>M[1-4])-(?P<density>D1|D3|D5|MIX)-(?P<surface>CLEAN|POISON_TD|POISON_CA|MIX)-"
    r"(?P<defense>BASELINE|IHR_SPCE)-(?P<run>[A-Z0-9]{8})-(?P<slice>[A-Z0-9]{4})$"
)
_ATTEMPT_ID_PATTERN = re.compile(
    r"^P5ATT-(?P<trial_id>[A-Za-z0-9][A-Za-z0-9_.-]{0,127})-A(?P<attempt_index>\d{3})-(?P<session>[A-Z0-9]{8})$"
)
_EVENT_ID_PATTERN = re.compile(r"^P5EVT-(?P<attempt_id>.+)-(?P<sequence>\d{4})$")
_ARTIFACT_ID_PATTERN = re.compile(r"^P5ART-(?P<prefix>[A-F0-9]{16})-(?P<artifact_type>[a-z0-9][a-z0-9_-]{0,31})$")


def _require_match(pattern: re.Pattern[str], value: str, kind: str) -> re.Match[str]:
    match = pattern.fullmatch(value)
    if match is None:
        raise IdentifierValidationError(f"{kind} does not match the frozen grammar: {value!r}")
    return match


@dataclass(frozen=True, slots=True)
class DatasetVersion:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _DATASET_VERSION_PATTERN

    @classmethod
    def parse(cls, value: str) -> "DatasetVersion":
        _require_match(cls._pattern, value, "dataset_version")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class TrialId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _TRIAL_ID_PATTERN

    @classmethod
    def parse(cls, value: str) -> "TrialId":
        _require_match(cls._pattern, value, "trial_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class FrozenRowId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _FROZEN_ROW_ID_PATTERN

    @classmethod
    def parse(cls, value: str) -> "FrozenRowId":
        _require_match(cls._pattern, value, "frozen_row_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class RunId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _RUN_ID_PATTERN

    @classmethod
    def build(cls, dataset: str, model: ModelSlot, utcdate: str, session: str) -> "RunId":
        if not _SESSION_TOKEN_PATTERN.fullmatch(session):
            raise IdentifierValidationError(f"run_id session token must be 8 uppercase alphanumeric characters: {session!r}")
        value = f"P5RUN-{dataset}-{model.value}-{utcdate}-{session}"
        _require_match(cls._pattern, value, "run_id")
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> "RunId":
        _require_match(cls._pattern, value, "run_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class BatchId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _BATCH_ID_PATTERN

    @classmethod
    def build(
        cls,
        dataset: str,
        workload: TrialPhase,
        model: ModelSlot,
        density_or_mix: Density | str,
        surface_or_mix: MetadataSurfaceCondition | str,
        defense: DefenseCondition,
        run_token: str,
        slice_token: str,
    ) -> "BatchId":
        density_value = density_or_mix.value if isinstance(density_or_mix, Density) else density_or_mix
        surface_value = surface_or_mix.value if isinstance(surface_or_mix, MetadataSurfaceCondition) else surface_or_mix
        if not _SESSION_TOKEN_PATTERN.fullmatch(run_token):
            raise IdentifierValidationError(f"batch_id run token must be 8 uppercase alphanumeric characters: {run_token!r}")
        if not _SHORT_TOKEN_PATTERN.fullmatch(slice_token):
            raise IdentifierValidationError(f"batch_id slice token must be 4 uppercase alphanumeric characters: {slice_token!r}")
        value = (
            f"P5BAT-{dataset}-{workload.value}-{model.value}-{density_value}-{surface_value}-"
            f"{defense.value}-{run_token}-{slice_token}"
        )
        _require_match(cls._pattern, value, "batch_id")
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> "BatchId":
        _require_match(cls._pattern, value, "batch_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class AttemptId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _ATTEMPT_ID_PATTERN

    @classmethod
    def build(cls, trial_id: TrialId | str, attempt_index: int, session: str) -> "AttemptId":
        trial_value = trial_id.value if isinstance(trial_id, TrialId) else trial_id
        if attempt_index < 0 or attempt_index > 999:
            raise IdentifierValidationError(f"attempt_index must be between 0 and 999 inclusive: {attempt_index!r}")
        if not _SESSION_TOKEN_PATTERN.fullmatch(session):
            raise IdentifierValidationError(f"attempt_id session token must be 8 uppercase alphanumeric characters: {session!r}")
        value = f"P5ATT-{trial_value}-A{attempt_index:03d}-{session}"
        _require_match(cls._pattern, value, "attempt_id")
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> "AttemptId":
        _require_match(cls._pattern, value, "attempt_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class EventId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _EVENT_ID_PATTERN

    @classmethod
    def build(cls, attempt_id: AttemptId | str, sequence: int) -> "EventId":
        attempt_value = attempt_id.value if isinstance(attempt_id, AttemptId) else attempt_id
        if sequence < 0 or sequence > 9999:
            raise IdentifierValidationError(f"event sequence must be between 0 and 9999 inclusive: {sequence!r}")
        value = f"P5EVT-{attempt_value}-{sequence:04d}"
        _require_match(cls._pattern, value, "event_id")
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> "EventId":
        _require_match(cls._pattern, value, "event_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, slots=True)
class ArtifactId:
    value: str

    _pattern: ClassVar[re.Pattern[str]] = _ARTIFACT_ID_PATTERN

    @classmethod
    def build(cls, sha256_prefix16: str, artifact_type: str) -> "ArtifactId":
        if not re.fullmatch(r"[A-F0-9]{16}", sha256_prefix16):
            raise IdentifierValidationError(
                f"artifact_id prefix must be exactly 16 uppercase hex characters: {sha256_prefix16!r}"
            )
        value = f"P5ART-{sha256_prefix16}-{artifact_type}"
        _require_match(cls._pattern, value, "artifact_id")
        return cls(value)

    @classmethod
    def parse(cls, value: str) -> "ArtifactId":
        _require_match(cls._pattern, value, "artifact_id")
        return cls(value)

    def __str__(self) -> str:
        return self.value
