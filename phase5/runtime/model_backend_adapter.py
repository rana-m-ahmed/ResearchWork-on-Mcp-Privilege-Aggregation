"""Frozen model backend adapter and runtime identity checks for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..domain.config import load_upstream_artifact_registry
from ..domain.errors import MissingFrozenSettingError, RuntimeMismatchError, SchemaInvariantError
from ..guards import repo_root


_SELECTED_MODEL_PATH = Path("phase4_5/configs/phase45_selected_model.yaml")
_LOCAL_DRYRUN_PATH = Path("phase4_5/configs/phase45_local_dryrun.yaml")
_MODEL_SET_PATH = Path("phase4/configs/model_set_freeze.yaml")

_PLACEHOLDER_DIGEST_MARKERS = (
    "AUTHENTIC_KAGGLE_EXECUTION",
    "TO_VERIFY_ON_KAGGLE",
    "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
)


def _yaml_safe_load(path: Path) -> Mapping[str, Any]:
    try:
        import yaml
    except Exception as exc:  # pragma: no cover - exercised by failure paths if unavailable
        raise SchemaInvariantError("PyYAML is required to load frozen model configuration") from exc

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise SchemaInvariantError(f"frozen YAML config must be a mapping: {path.as_posix()}")
    return data


def _require_string(value: Any, *, label: str, path: Path) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaInvariantError(f"{path.as_posix()} is missing required string field {label!r}")
    return value


def _require_optional_string(value: Any, *, label: str, path: Path) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SchemaInvariantError(f"{path.as_posix()} field {label!r} must be a string or null")
    return value


def _mapping_value(snapshot: Mapping[str, Any] | Any, *keys: str) -> Any:
    if isinstance(snapshot, Mapping):
        for key in keys:
            if key in snapshot:
                return snapshot[key]
        return None
    for key in keys:
        if hasattr(snapshot, key):
            return getattr(snapshot, key)
    return None


def _is_placeholder_digest(value: str | None) -> bool:
    if value is None:
        return True
    upper_value = value.upper()
    return any(marker in upper_value for marker in _PLACEHOLDER_DIGEST_MARKERS)


@dataclass(frozen=True, slots=True)
class FrozenModelBackendIdentity:
    """Frozen identity tuple for the selected backend/model combination."""

    model_id: str
    exact_model_identifier: str
    model_digest: str
    quantization: str
    backend: str
    backend_version: str
    tokenizer_identity: str
    ollama_version: str | None
    selected_model_path: Path
    local_dryrun_path: Path
    model_set_path: Path
    model_freeze_path: Path

    @property
    def model_digest_is_placeholder(self) -> bool:
        return _is_placeholder_digest(self.model_digest)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "backend": self.backend,
            "backend_version": self.backend_version,
            "exact_model_identifier": self.exact_model_identifier,
            "model_digest": self.model_digest,
            "model_id": self.model_id,
            "ollama_version": self.ollama_version,
            "quantization": self.quantization,
            "tokenizer_identity": self.tokenizer_identity,
        }


def load_frozen_model_backend_identity(root: Path | None = None) -> FrozenModelBackendIdentity:
    """Load the frozen model/backend tuple and fail closed on any divergence."""

    repository_root = (root or repo_root()).resolve()
    selected_model_path = repository_root / _SELECTED_MODEL_PATH
    local_dryrun_path = repository_root / _LOCAL_DRYRUN_PATH
    for path, label in (
        (selected_model_path, "selected model"),
        (local_dryrun_path, "local dry-run config"),
    ):
        if not path.is_file():
            raise MissingFrozenSettingError(f"frozen {label} is missing: {path.as_posix()}")

    selected_model = _yaml_safe_load(selected_model_path)
    local_dryrun = _yaml_safe_load(local_dryrun_path)
    registry = load_upstream_artifact_registry(repository_root / "phase5" / "configs" / "upstream_artifact_registry.json")

    model_set_entry = registry.require("Model freeze set")
    model_set_path = repository_root / model_set_entry.actual_paths[0]
    if not model_set_path.is_file():
        raise MissingFrozenSettingError(f"frozen model set is missing: {model_set_path.as_posix()}")
    model_set = _yaml_safe_load(model_set_path)

    selected_model_id = _require_string(selected_model.get("model_slot"), label="model_slot", path=selected_model_path)
    selected_model_identifier = _require_string(
        selected_model.get("exact_model_identifier"),
        label="exact_model_identifier",
        path=selected_model_path,
    )
    selected_source = _require_string(selected_model.get("frozen_source"), label="frozen_source", path=selected_model_path)
    if selected_source != _MODEL_SET_PATH.as_posix():
        raise SchemaInvariantError(
            f"{selected_model_path.as_posix()} must point frozen_source to {_MODEL_SET_PATH.as_posix()!r}"
        )

    local_slot = _require_string(local_dryrun.get("selected_model_slot"), label="selected_model_slot", path=local_dryrun_path)
    local_identifier = _require_string(
        local_dryrun.get("selected_model_identifier"),
        label="selected_model_identifier",
        path=local_dryrun_path,
    )
    if selected_model_id != local_slot or selected_model_identifier != local_identifier:
        raise RuntimeMismatchError(
            "selected model configuration diverges between phase45_selected_model.yaml and phase45_local_dryrun.yaml"
        )

    model_identifier = model_set.get(selected_model_id)
    if model_identifier is None:
        raise MissingFrozenSettingError(f"frozen model slot is missing from model set: {selected_model_id!r}")
    if model_identifier != selected_model_identifier:
        raise RuntimeMismatchError(
            f"model set identity mismatch for {selected_model_id!r}: expected {model_identifier!r}, "
            f"got {selected_model_identifier!r}"
        )

    slot_suffix = selected_model_id.removeprefix("M")
    if not slot_suffix or not slot_suffix.isdigit():
        raise SchemaInvariantError(f"frozen model slot is not canonical: {selected_model_id!r}")

    model_freeze_entry = registry.require(f"Model freeze {selected_model_id}")
    model_freeze_path = repository_root / model_freeze_entry.actual_paths[0]
    if not model_freeze_path.is_file():
        raise MissingFrozenSettingError(f"frozen model config is missing: {model_freeze_path.as_posix()}")

    model_freeze = _yaml_safe_load(model_freeze_path)
    model_freeze_slot = _require_string(model_freeze.get("model_slot"), label="model_slot", path=model_freeze_path)
    if model_freeze_slot != selected_model_id:
        raise RuntimeMismatchError(
            f"model freeze slot mismatch: expected {selected_model_id!r}, got {model_freeze_slot!r}"
        )

    exact_identifier = _require_string(
        model_freeze.get("exact_model_identifier"),
        label="exact_model_identifier",
        path=model_freeze_path,
    )
    if exact_identifier != selected_model_identifier:
        raise RuntimeMismatchError(
            f"frozen model identity mismatch: expected {selected_model_identifier!r}, got {exact_identifier!r}"
        )

    quantization = _require_string(model_freeze.get("quantization"), label="quantization", path=model_freeze_path)
    backend = _require_string(model_freeze.get("runtime_backend"), label="runtime_backend", path=model_freeze_path)
    backend_version = _require_string(model_freeze.get("backend_version"), label="backend_version", path=model_freeze_path)
    tokenizer_identity = _require_string(
        model_freeze.get("tokenizer_identity"),
        label="tokenizer_identity",
        path=model_freeze_path,
    )
    model_digest = _require_string(model_freeze.get("model_digest"), label="model_digest", path=model_freeze_path)
    ollama_version = _require_optional_string(
        model_freeze.get("ollama_or_llamacpp_version", model_freeze.get("ollama_version")),
        label="ollama_or_llamacpp_version",
        path=model_freeze_path,
    )

    if tokenizer_identity != selected_model_identifier:
        raise RuntimeMismatchError(
            f"tokenizer identity mismatch: expected {selected_model_identifier!r}, got {tokenizer_identity!r}"
        )

    return FrozenModelBackendIdentity(
        model_id=selected_model_id,
        exact_model_identifier=selected_model_identifier,
        model_digest=model_digest,
        quantization=quantization,
        backend=backend,
        backend_version=backend_version,
        tokenizer_identity=tokenizer_identity,
        ollama_version=ollama_version,
        selected_model_path=selected_model_path,
        local_dryrun_path=local_dryrun_path,
        model_set_path=model_set_path,
        model_freeze_path=model_freeze_path,
    )


@dataclass(frozen=True, slots=True)
class FrozenModelBackendAdapter:
    """Validated runtime adapter for the frozen Phase 5 model/backend tuple."""

    identity: FrozenModelBackendIdentity

    @property
    def model_id(self) -> str:
        return self.identity.model_id

    @property
    def exact_model_identifier(self) -> str:
        return self.identity.exact_model_identifier

    @property
    def model_digest(self) -> str:
        return self.identity.model_digest

    @property
    def quantization(self) -> str:
        return self.identity.quantization

    @property
    def backend(self) -> str:
        return self.identity.backend

    @property
    def backend_version(self) -> str:
        return self.identity.backend_version

    @property
    def tokenizer_identity(self) -> str:
        return self.identity.tokenizer_identity

    @property
    def ollama_version(self) -> str | None:
        return self.identity.ollama_version

    def to_mapping(self) -> dict[str, Any]:
        return self.identity.to_mapping()

    def validate_runtime_snapshot(self, snapshot: Mapping[str, Any] | Any) -> None:
        """Validate a runtime snapshot against the frozen identity tuple."""

        expected_fields = {
            "model_id": self.model_id,
            "exact_model_identifier": self.exact_model_identifier,
            "quantization": self.quantization,
            "backend": self.backend,
            "backend_version": self.backend_version,
            "tokenizer_identity": self.tokenizer_identity,
        }
        alias_map = {
            "backend": ("backend", "runtime_backend"),
            "exact_model_identifier": ("exact_model_identifier", "model_name"),
            "model_id": ("model_id", "model_slot"),
            "model_digest": ("model_digest",),
            "ollama_version": ("ollama_version", "ollama_or_llamacpp_version"),
            "quantization": ("quantization",),
            "backend_version": ("backend_version",),
            "tokenizer_identity": ("tokenizer_identity",),
        }
        for field, expected_value in expected_fields.items():
            actual_value = _mapping_value(snapshot, *alias_map[field])
            if actual_value is None:
                raise MissingFrozenSettingError(f"runtime snapshot is missing required field {field!r}")
            if actual_value != expected_value:
                raise RuntimeMismatchError(
                    f"runtime snapshot mismatch for {field!r}: expected {expected_value!r}, got {actual_value!r}"
                )

        actual_digest = _mapping_value(snapshot, *alias_map["model_digest"])
        if actual_digest is None:
            raise MissingFrozenSettingError("runtime snapshot is missing required field 'model_digest'")
        if self.identity.model_digest_is_placeholder:
            if _is_placeholder_digest(actual_digest):
                raise RuntimeMismatchError(
                    "runtime snapshot model_digest is still a placeholder and cannot satisfy runtime identity checks"
                )
        elif actual_digest != self.identity.model_digest:
            raise RuntimeMismatchError(
                f"runtime snapshot digest mismatch: expected {self.identity.model_digest!r}, got {actual_digest!r}"
            )

        actual_ollama_version = _mapping_value(snapshot, *alias_map["ollama_version"])
        if actual_ollama_version != self.identity.ollama_version:
            raise RuntimeMismatchError(
                f"runtime snapshot mismatch for 'ollama_version': expected {self.identity.ollama_version!r}, got {actual_ollama_version!r}"
            )


def build_frozen_model_backend_adapter(root: Path | None = None) -> FrozenModelBackendAdapter:
    """Convenience builder for the validated frozen model backend adapter."""

    return FrozenModelBackendAdapter(identity=load_frozen_model_backend_identity(root=root))
