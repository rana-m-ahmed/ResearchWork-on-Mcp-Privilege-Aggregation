"""Frozen model backend adapter and runtime identity checks for Phase 5."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from ..domain.config import load_upstream_artifact_registry
from ..domain.errors import MissingFrozenSettingError, RuntimeMismatchError, SchemaInvariantError
from ..guards import repo_root


_SELECTED_MODEL_PATH = Path("phase4_5/configs/phase45_selected_model.yaml")
_LOCAL_DRYRUN_PATH = Path("phase4_5/configs/phase45_local_dryrun.yaml")
_MODEL_SET_PATH = Path("phase4/configs/model_set_freeze.yaml")
_RUNTIME_AUTHORITY_PATH = Path("phase5/manifests/model_runtime_authority_v2.json")
_GIB = 1024**3
_GPU_HEADROOM_BYTES = 2 * _GIB
_CPU_HEADROOM_BYTES = 4 * _GIB
_FROZEN_INPUT_TOKEN_LIMIT = 3584


def _available_cpu_memory_bytes() -> int:
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        for line in meminfo.read_text(encoding="ascii").splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    try:
        import psutil

        return int(psutil.virtual_memory().available)
    except Exception as exc:  # pragma: no cover - Linux Kaggle path is authoritative
        raise RuntimeMismatchError("could not determine available CPU memory for frozen model placement") from exc


def build_model_load_memory_plan(torch_module: Any) -> tuple[dict[Any, int], Path]:
    """Reserve inference headroom and make any required offload explicit."""

    device_count = int(torch_module.cuda.device_count())
    if device_count < 1:
        raise RuntimeMismatchError("no CUDA devices are available for frozen model placement")
    max_memory: dict[Any, int] = {}
    for device_index in range(device_count):
        free_gpu_bytes, total_gpu_bytes = torch_module.cuda.mem_get_info(device_index)
        usable_gpu_bytes = min(int(free_gpu_bytes), int(total_gpu_bytes)) - _GPU_HEADROOM_BYTES
        if usable_gpu_bytes < 4 * _GIB:
            raise RuntimeMismatchError(
                f"insufficient free GPU memory for the frozen M1 float16 backend on cuda:{device_index}"
            )
        max_memory[device_index] = usable_gpu_bytes
    usable_cpu_bytes = _available_cpu_memory_bytes() - _CPU_HEADROOM_BYTES
    if usable_cpu_bytes < 4 * _GIB:
        raise RuntimeMismatchError("insufficient free CPU memory for controlled M1 weight offload")
    offload_root = Path(
        os.environ.get("PHASE5_MODEL_OFFLOAD_DIR", str(Path(tempfile.gettempdir()) / "phase5-model-offload"))
    )
    offload_root.mkdir(parents=True, exist_ok=True)
    max_memory["cpu"] = usable_cpu_bytes
    return max_memory, offload_root


def serialize_frozen_prompt_for_model(tokenizer: Any, prompt_text: str) -> str:
    """Apply the immutable tokenizer's native generation boundary."""

    apply_chat_template = getattr(tokenizer, "apply_chat_template", None)
    if not callable(apply_chat_template):
        raise RuntimeMismatchError("the frozen tokenizer does not expose its required chat template")
    serialized = apply_chat_template(
        [{"role": "user", "content": prompt_text}],
        tokenize=False,
        add_generation_prompt=True,
    )
    if not isinstance(serialized, str) or not serialized:
        raise RuntimeMismatchError("the frozen tokenizer returned an invalid chat serialization")
    return serialized

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
    huggingface_commit_sha: str

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
            "huggingface_commit_sha": self.huggingface_commit_sha,
        }


def _load_slot_backend_identity(repository_root: Path, model_slot: str) -> FrozenModelBackendIdentity:
    """Resolve a branch slot from the frozen Phase 5 model authority."""

    if model_slot not in {"M1", "M2", "M3", "M4"}:
        raise SchemaInvariantError(f"unsupported frozen model slot: {model_slot!r}")
    registry = load_upstream_artifact_registry(repository_root / "phase5/configs/upstream_artifact_registry.json")
    model_set_entry = registry.require("Model freeze set")
    model_set_path = repository_root / model_set_entry.actual_paths[0]
    model_set = _yaml_safe_load(model_set_path)
    exact_identifier = _require_string(model_set.get(model_slot), label="exact_model_identifier", path=model_set_path)
    model_freeze_path = repository_root / "phase4" / "configs" / f"model_{model_slot.removeprefix('M')}_freeze.yaml"
    if not model_freeze_path.is_file():
        raise MissingFrozenSettingError(f"frozen model config is missing: {model_freeze_path.as_posix()}")
    model_freeze = _yaml_safe_load(model_freeze_path)
    if _require_string(model_freeze.get("model_slot"), label="model_slot", path=model_freeze_path) != model_slot:
        raise RuntimeMismatchError(f"frozen model config slot mismatch for {model_slot!r}")
    if _require_string(model_freeze.get("exact_model_identifier"), label="exact_model_identifier", path=model_freeze_path) != exact_identifier:
        raise RuntimeMismatchError(f"frozen model identity mismatch for {model_slot!r}")
    runtime_authority_path = repository_root / _RUNTIME_AUTHORITY_PATH
    runtime_authority = json.loads(runtime_authority_path.read_text(encoding="utf-8"))
    runtime_entry = runtime_authority.get(model_slot)
    if not isinstance(runtime_entry, Mapping) or runtime_entry.get("exact_model_identifier") != exact_identifier:
        raise RuntimeMismatchError(f"runtime authority identity mismatch for {model_slot!r}")
    revision = _require_string(runtime_entry.get("huggingface_commit_sha"), label="huggingface_commit_sha", path=runtime_authority_path)
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise SchemaInvariantError("huggingface_commit_sha must be a lowercase 40-character commit SHA")
    return FrozenModelBackendIdentity(
        model_id=model_slot,
        exact_model_identifier=exact_identifier,
        model_digest=_require_string(model_freeze.get("model_digest"), label="model_digest", path=model_freeze_path),
        quantization=_require_string(model_freeze.get("quantization"), label="quantization", path=model_freeze_path),
        backend=_require_string(model_freeze.get("runtime_backend"), label="runtime_backend", path=model_freeze_path),
        backend_version=_require_string(model_freeze.get("backend_version"), label="backend_version", path=model_freeze_path),
        tokenizer_identity=_require_string(model_freeze.get("tokenizer_identity"), label="tokenizer_identity", path=model_freeze_path),
        ollama_version=_require_optional_string(model_freeze.get("ollama_or_llamacpp_version", model_freeze.get("ollama_version")), label="ollama_version", path=model_freeze_path),
        selected_model_path=model_freeze_path,
        local_dryrun_path=repository_root / "phase4_5/configs/phase45_local_dryrun.yaml",
        model_set_path=model_set_path,
        model_freeze_path=model_freeze_path,
        huggingface_commit_sha=revision,
    )


def load_frozen_model_backend_identity(
    root: Path | None = None,
    *,
    model_slot: str | None = None,
) -> FrozenModelBackendIdentity:
    """Load the frozen model/backend tuple and fail closed on any divergence."""

    repository_root = (root or repo_root()).resolve()
    if model_slot is not None:
        return _load_slot_backend_identity(repository_root, model_slot)
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

    runtime_authority_path = repository_root / _RUNTIME_AUTHORITY_PATH
    if not runtime_authority_path.is_file():
        raise MissingFrozenSettingError(f"model runtime authority is missing: {runtime_authority_path.as_posix()}")
    runtime_authority = json.loads(runtime_authority_path.read_text(encoding="utf-8"))
    runtime_entry = runtime_authority.get(selected_model_id) if isinstance(runtime_authority, Mapping) else None
    if not isinstance(runtime_entry, Mapping):
        raise MissingFrozenSettingError(f"runtime authority is missing model slot {selected_model_id!r}")
    authority_identifier = _require_string(
        runtime_entry.get("exact_model_identifier"), label="exact_model_identifier", path=runtime_authority_path
    )
    if authority_identifier != selected_model_identifier:
        raise RuntimeMismatchError(
            f"runtime authority identity mismatch: expected {selected_model_identifier!r}, got {authority_identifier!r}"
        )
    huggingface_commit_sha = _require_string(
        runtime_entry.get("huggingface_commit_sha"), label="huggingface_commit_sha", path=runtime_authority_path
    )
    if len(huggingface_commit_sha) != 40 or any(c not in "0123456789abcdef" for c in huggingface_commit_sha):
        raise SchemaInvariantError("huggingface_commit_sha must be a lowercase 40-character commit SHA")

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
        huggingface_commit_sha=huggingface_commit_sha,
    )


@dataclass(slots=True)
class FrozenModelBackendAdapter:
    """Validated runtime adapter for the frozen Phase 5 model/backend tuple."""

    identity: FrozenModelBackendIdentity
    _model: Any = field(default=None, init=False, repr=False)
    _tokenizer: Any = field(default=None, init=False, repr=False)
    _load_memory_plan: dict[str, Any] | None = field(default=None, init=False, repr=False)
    _last_generation_receipt: dict[str, Any] | None = field(default=None, init=False, repr=False)

    def attach_tokenizer(self, tokenizer: Any) -> None:
        """Reuse the identity-checked tokenizer used by prompt accounting."""

        self._tokenizer = tokenizer

    def _ensure_runtime_loaded(self) -> None:
        if self._model is not None:
            return
        try:
            import torch
            from transformers import AutoModelForCausalLM, AutoTokenizer
        except Exception as exc:
            raise RuntimeMismatchError("torch and transformers are required for real model execution") from exc
        if not torch.cuda.is_available():
            raise RuntimeMismatchError("the frozen M1 float16 backend requires a CUDA GPU")
        print(
            f"MODEL_GPU_LOAD_START: slot={self.identity.model_id}; model={self.exact_model_identifier}",
            flush=True,
        )
        if self._tokenizer is None:
            self._tokenizer = AutoTokenizer.from_pretrained(
                self.tokenizer_identity,
                revision=self.identity.huggingface_commit_sha,
                trust_remote_code=True,
            )
        max_memory, offload_folder = build_model_load_memory_plan(torch)
        self._load_memory_plan = {
            "max_memory_bytes": {str(device): value for device, value in max_memory.items()},
            "offload_folder": str(offload_folder),
        }
        try:
            self._model = AutoModelForCausalLM.from_pretrained(
                self.exact_model_identifier,
                revision=self.identity.huggingface_commit_sha,
                dtype=torch.float16,
                device_map="auto",
                max_memory=max_memory,
                low_cpu_mem_usage=True,
                offload_folder=offload_folder,
                use_safetensors=True,
                trust_remote_code=True,
            )
            self._model.eval()
            self._model.generation_config.do_sample = False
            self._model.generation_config.temperature = None
            self._model.generation_config.top_p = None
            self._model.generation_config.top_k = None
            self._load_memory_plan["hf_device_map"] = {
                str(name): str(device) for name, device in getattr(self._model, "hf_device_map", {}).items()
            }
            required_device_count = int(os.environ.get("PHASE5_REQUIRE_CUDA_DEVICE_COUNT", "1"))
            mapped_devices = {
                int(device)
                for device in getattr(self._model, "hf_device_map", {}).values()
                if isinstance(device, int) or (isinstance(device, str) and device.isdigit())
            }
            missing_devices = set(range(required_device_count)) - mapped_devices
            if missing_devices:
                raise RuntimeMismatchError(
                    f"frozen model placement did not use required CUDA devices: {sorted(missing_devices)}"
                )
            print(
                f"MODEL_GPU_MODEL_READY: slot={self.identity.model_id}; model={self.exact_model_identifier}; trials_may_start=true",
                flush=True,
            )
        except Exception as exc:
            raise RuntimeMismatchError(
                f"failed to load frozen model {self.exact_model_identifier!r} at "
                f"revision {self.identity.huggingface_commit_sha!r}"
            ) from exc

    def prepare_runtime(self) -> Mapping[str, Any]:
        """Load and validate the immutable model before attempt dispatch."""
        self._ensure_runtime_loaded()
        if self._load_memory_plan is None:
            raise RuntimeMismatchError("model runtime loaded without a placement receipt")
        return dict(self._load_memory_plan)

    def generate(self, *, prompt_text: str, conversation_history: Any, session: Any, turn_index: int, controls: Any) -> str:
        """Run deterministic generation through the immutable Hugging Face revision."""

        self._ensure_runtime_loaded()
        import torch

        serialized_prompt = serialize_frozen_prompt_for_model(self._tokenizer, prompt_text)
        encoded = self._tokenizer(serialized_prompt, return_tensors="pt", add_special_tokens=False)
        input_token_count = int(encoded["input_ids"].shape[1])
        if input_token_count > _FROZEN_INPUT_TOKEN_LIMIT:
            raise RuntimeMismatchError(
                f"model-native prompt serialization exceeds the frozen input limit: "
                f"{input_token_count} > {_FROZEN_INPUT_TOKEN_LIMIT}"
            )
        input_device = next(self._model.parameters()).device
        encoded = {name: tensor.to(input_device) for name, tensor in encoded.items()}
        with torch.inference_mode():
            output = self._model.generate(
                **encoded,
                max_new_tokens=512,
                do_sample=False,
                pad_token_id=self._tokenizer.eos_token_id,
            )
        generated_ids = output[0, encoded["input_ids"].shape[1]:]
        decoded_output = self._tokenizer.decode(generated_ids, skip_special_tokens=True)
        self._last_generation_receipt = {
            "compiled_prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            "model_serialization": "tokenizer_chat_template",
            "serialized_prompt_sha256": hashlib.sha256(serialized_prompt.encode("utf-8")).hexdigest(),
            "input_token_ids": encoded["input_ids"][0].detach().cpu().tolist(),
            "generated_token_ids": generated_ids.detach().cpu().tolist(),
            "decoded_output": decoded_output,
            "input_device": str(input_device),
        }
        return decoded_output

    @property
    def load_memory_plan(self) -> Mapping[str, Any] | None:
        return dict(self._load_memory_plan) if self._load_memory_plan is not None else None

    @property
    def last_generation_receipt(self) -> Mapping[str, Any] | None:
        return dict(self._last_generation_receipt) if self._last_generation_receipt is not None else None

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


def build_frozen_model_backend_adapter(
    root: Path | None = None,
    *,
    model_slot: str | None = None,
) -> FrozenModelBackendAdapter:
    """Convenience builder for the validated frozen model backend adapter."""

    return FrozenModelBackendAdapter(identity=load_frozen_model_backend_identity(root=root, model_slot=model_slot))
