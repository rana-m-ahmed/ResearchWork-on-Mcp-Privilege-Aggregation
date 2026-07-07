"""Protocol invariants for frozen Phase 5 domain objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .errors import (
    DuplicateAcceptedAttemptError,
    FrozenArtifactHashError,
    IdentifierValidationError,
    MissingFrozenSettingError,
    ProhibitedAliasError,
    SchemaInvariantError,
)
from .enums import (
    AttackFamily,
    DefenseCondition,
    Density,
    MetadataSurfaceCondition,
    ModelSlot,
    PayloadCondition,
    SessionState,
    TrialOutcome,
    TrialPhase,
)
from .identifiers import FrozenRowId, TrialId


def _schema_freeze_path() -> Path:
    return Path(__file__).resolve().parents[2] / "phase4" / "configs" / "phase5_schema_freeze.json"


def _load_schema_fields() -> tuple[str, ...]:
    import json

    path = _schema_freeze_path()
    if not path.is_file():
        raise MissingFrozenSettingError(f"phase5 schema freeze is missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError("phase5 schema freeze must be a JSON object")
    return tuple(data.keys())


FROZEN_TRIAL_FIELDS = _load_schema_fields()
FROZEN_TRIAL_FIELD_SET = frozenset(FROZEN_TRIAL_FIELDS)
PROHIBITED_FIELD_ALIASES = {
    "metadata_condition": "metadata_surface_condition",
    "model_slot": "model_id",
    "runtime_backend": "backend",
    "ollama_or_llamacpp_version": "ollama_version",
}


def _require_exact_keys(mapping: Mapping[str, Any]) -> None:
    keys = set(mapping)
    alias_hits = sorted(key for key in keys if key in PROHIBITED_FIELD_ALIASES)
    if alias_hits:
        aliases = ", ".join(f"{alias}->{PROHIBITED_FIELD_ALIASES[alias]}" for alias in alias_hits)
        raise ProhibitedAliasError(f"prohibited field alias used: {aliases}")

    missing = [key for key in FROZEN_TRIAL_FIELDS if key not in mapping]
    extra = [key for key in mapping if key not in FROZEN_TRIAL_FIELD_SET]
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise MissingFrozenSettingError(f"trial row field mismatch: {'; '.join(details)}")


def _require_nonempty_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_optional_string(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _require_nonempty_string(value, field)


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaInvariantError(f"{field} must be a boolean")
    return value


def _parse_model_slot(value: Any) -> ModelSlot:
    return ModelSlot.from_value(_require_nonempty_string(value, "model_id"))


def _parse_enum(enum_cls, value: Any, field: str):
    return enum_cls.from_value(_require_nonempty_string(value, field))


def _require_timestamp_utc(value: Any) -> str:
    text = _require_nonempty_string(value, "timestamp_utc")
    if text.endswith("Z"):
        from datetime import datetime

        datetime.fromisoformat(text[:-1] + "+00:00")
        return text
    from datetime import datetime

    datetime.fromisoformat(text)
    return text


def _require_hash_like(value: Any, field: str, *, allow_none: bool = False) -> str | None:
    if value is None:
        if allow_none:
            return None
        raise SchemaInvariantError(f"{field} cannot be null")
    text = _require_nonempty_string(value, field)
    return text


@dataclass(frozen=True, slots=True)
class FrozenTrialRow:
    phase: TrialPhase
    official_trial: bool
    trial_id: TrialId
    run_id: str
    branch: str
    git_commit_hash: str
    timestamp_utc: str
    model_id: ModelSlot
    exact_model_identifier: str
    model_digest: str
    quantization: str
    backend: str
    backend_version: str
    ollama_version: str | None
    density: Density
    metadata_surface_condition: MetadataSurfaceCondition
    attack_family: AttackFamily
    defense_condition: DefenseCondition
    payload_id: str
    phase1_payload_hash: str | None
    payload_hash: str | None
    adversarial_payload_present: bool
    payload_condition: PayloadCondition

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "FrozenTrialRow":
        _require_exact_keys(mapping)

        row = cls(
            phase=_parse_enum(TrialPhase, mapping["phase"], "phase"),
            official_trial=_require_bool(mapping["official_trial"], "official_trial"),
            trial_id=TrialId.parse(_require_nonempty_string(mapping["trial_id"], "trial_id")),
            run_id=_require_nonempty_string(mapping["run_id"], "run_id"),
            branch=_require_nonempty_string(mapping["branch"], "branch"),
            git_commit_hash=_require_nonempty_string(mapping["git_commit_hash"], "git_commit_hash"),
            timestamp_utc=_require_timestamp_utc(mapping["timestamp_utc"]),
            model_id=_parse_model_slot(mapping["model_id"]),
            exact_model_identifier=_require_nonempty_string(mapping["exact_model_identifier"], "exact_model_identifier"),
            model_digest=_require_nonempty_string(mapping["model_digest"], "model_digest"),
            quantization=_require_nonempty_string(mapping["quantization"], "quantization"),
            backend=_require_nonempty_string(mapping["backend"], "backend"),
            backend_version=_require_nonempty_string(mapping["backend_version"], "backend_version"),
            ollama_version=_require_optional_string(mapping["ollama_version"], "ollama_version"),
            density=_parse_enum(Density, mapping["density"], "density"),
            metadata_surface_condition=_parse_enum(
                MetadataSurfaceCondition, mapping["metadata_surface_condition"], "metadata_surface_condition"
            ),
            attack_family=_parse_enum(AttackFamily, mapping["attack_family"], "attack_family"),
            defense_condition=_parse_enum(DefenseCondition, mapping["defense_condition"], "defense_condition"),
            payload_id=_require_nonempty_string(mapping["payload_id"], "payload_id"),
            phase1_payload_hash=_require_hash_like(mapping["phase1_payload_hash"], "phase1_payload_hash", allow_none=True),
            payload_hash=_require_hash_like(mapping["payload_hash"], "payload_hash", allow_none=True),
            adversarial_payload_present=_require_bool(
                mapping["adversarial_payload_present"], "adversarial_payload_present"
            ),
            payload_condition=_parse_enum(PayloadCondition, mapping["payload_condition"], "payload_condition"),
        )
        validate_trial_row(row)
        return row


@dataclass(frozen=True, slots=True)
class TrialAssessment:
    density: Density
    outcome: TrialOutcome


@dataclass(frozen=True, slots=True)
class AcceptedAttemptRecord:
    target_frozen_row_id: FrozenRowId
    attempt_id: str
    accepted_attempt: bool


def validate_trial_row(row: FrozenTrialRow) -> None:
    if row.phase is TrialPhase.PHASE5_UTILITY_PRESERVATION:
        if row.metadata_surface_condition is not MetadataSurfaceCondition.CLEAN:
            raise SchemaInvariantError("utility rows must use CLEAN metadata surface")
        if row.attack_family is not AttackFamily.NONE:
            raise SchemaInvariantError("utility rows must use attack_family=NONE")
        if row.adversarial_payload_present:
            raise SchemaInvariantError("utility rows must not carry an adversarial payload")
        if row.phase1_payload_hash is not None or row.payload_hash is not None:
            raise SchemaInvariantError("utility rows must use null payload hashes")
        if row.payload_condition is not PayloadCondition.NONE:
            raise SchemaInvariantError("utility rows must use payload_condition=NONE")
        if row.density not in {Density.D3, Density.D5}:
            raise SchemaInvariantError("utility rows must use D3 or D5 density")
    else:
        if row.payload_condition is not PayloadCondition.PHASE1_HASH_AUTHORIZED:
            raise SchemaInvariantError("adversarial rows must use payload_condition=PHASE1_HASH_AUTHORIZED")


def validate_primary_outcome(assessment: TrialAssessment) -> None:
    if assessment.density is Density.D1 and assessment.outcome in {
        TrialOutcome.CRITICAL_EXPLOIT,
        TrialOutcome.ATTACK_SUCCESS,
    }:
        raise SchemaInvariantError("D1 cannot finalize as CRITICAL_EXPLOIT or ATTACK_SUCCESS")


def validate_single_accepted_attempt(records: Iterable[AcceptedAttemptRecord]) -> None:
    accepted_by_row: dict[str, int] = {}
    for record in records:
        if not isinstance(record.accepted_attempt, bool):
            raise SchemaInvariantError("accepted_attempt must be boolean")
        if not record.accepted_attempt:
            continue
        key = str(record.target_frozen_row_id)
        accepted_by_row[key] = accepted_by_row.get(key, 0) + 1
        if accepted_by_row[key] > 1:
            raise DuplicateAcceptedAttemptError(
                f"more than one accepted attempt was recorded for target frozen row {key!r}"
            )


def validate_hash_immutability(reference: Mapping[str, str], candidate: Mapping[str, str]) -> None:
    if set(reference) != set(candidate):
        raise FrozenArtifactHashError("hash key set changed within a dataset version")
    for key, expected in reference.items():
        actual = candidate[key]
        if actual != expected:
            raise FrozenArtifactHashError(f"hash changed within a dataset version for {key!r}")


def validate_session_execution_allowed(state: SessionState) -> None:
    if state in {SessionState.UNSEALED_SYNCING, SessionState.UNSEALED_SYNCED, SessionState.QUARANTINED, SessionState.TERMINAL}:
        raise SchemaInvariantError("execution is prohibited during sync or after terminal/quarantine states")
    if state is not SessionState.SEALED:
        raise SchemaInvariantError("execution requires SEALED state")
