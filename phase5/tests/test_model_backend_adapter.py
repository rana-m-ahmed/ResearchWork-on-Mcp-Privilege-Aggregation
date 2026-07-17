from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from pathlib import Path

import pytest

from phase5.domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, RuntimeMismatchError, SchemaInvariantError
from phase5.runtime import build_frozen_model_backend_adapter, load_frozen_model_backend_identity
from phase5.runtime.model_backend_adapter import (
    _build_generation_kwargs,
    _build_model_load_kwargs,
    build_model_load_memory_plan,
    serialize_frozen_prompt_for_model,
)


class _FakeCuda:
    @staticmethod
    def device_count() -> int:
        return 2

    @staticmethod
    def mem_get_info(device: int) -> tuple[int, int]:
        assert device in {0, 1}
        return 16 * 1024**3, 16 * 1024**3


class _FakeTorch:
    float16 = "float16"
    cuda = _FakeCuda()


class _ChatTokenizer:
    eos_token_id = 2

    def apply_chat_template(self, messages, *, tokenize, add_generation_prompt):
        assert messages == [{"role": "user", "content": "compiled prompt"}]
        assert tokenize is False
        assert add_generation_prompt is True
        return "<|im_start|>user\ncompiled prompt<|im_end|>\n<|im_start|>assistant\n"


def test_model_serialization_uses_immutable_tokenizer_chat_template() -> None:
    serialized = serialize_frozen_prompt_for_model(_ChatTokenizer(), "compiled prompt")

    assert serialized.endswith("<|im_start|>assistant\n")


def test_model_serialization_fails_without_chat_template() -> None:
    with pytest.raises(RuntimeMismatchError, match="required chat template"):
        serialize_frozen_prompt_for_model(object(), "compiled prompt")


def test_model_load_memory_plan_reserves_gpu_and_cpu_headroom(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("phase5.runtime.model_backend_adapter._available_cpu_memory_bytes", lambda: 30 * 1024**3)
    monkeypatch.setenv("PHASE5_MODEL_OFFLOAD_DIR", str(tmp_path / "offload"))

    max_memory, offload_folder = build_model_load_memory_plan(_FakeTorch())

    assert max_memory == {0: 14 * 1024**3, 1: 14 * 1024**3, "cpu": 26 * 1024**3}
    assert offload_folder == tmp_path / "offload"
    assert offload_folder.is_dir()


def test_model_load_memory_plan_fails_closed_on_insufficient_gpu(monkeypatch) -> None:
    monkeypatch.setattr(_FakeCuda, "mem_get_info", staticmethod(lambda device: (5 * 1024**3, 16 * 1024**3)))
    monkeypatch.setattr("phase5.runtime.model_backend_adapter._available_cpu_memory_bytes", lambda: 30 * 1024**3)

    with pytest.raises(RuntimeMismatchError, match="insufficient free GPU memory"):
        build_model_load_memory_plan(_FakeTorch())


def test_phi3_runtime_kwargs_force_eager_attention_and_disable_cache(tmp_path: Path) -> None:
    identity = SimpleNamespace(
        exact_model_identifier="microsoft/Phi-3.5-mini-instruct",
        huggingface_commit_sha="2fe192450127e6a83f7441aef6e3ca586c338b77",
    )

    load_kwargs = _build_model_load_kwargs(
        identity=identity,
        torch_module=_FakeTorch,
        max_memory={0: 1},
        offload_folder=tmp_path,
    )
    generation_kwargs = _build_generation_kwargs(
        exact_model_identifier=identity.exact_model_identifier,
        tokenizer=_ChatTokenizer(),
    )

    assert load_kwargs["attn_implementation"] == "eager"
    assert load_kwargs["use_cache"] is False
    assert generation_kwargs["use_cache"] is False


def test_non_phi_runtime_kwargs_preserve_default_cache_path(tmp_path: Path) -> None:
    identity = SimpleNamespace(
        exact_model_identifier="mistralai/Mistral-7B-Instruct-v0.3",
        huggingface_commit_sha="c170c708c41dac9275d15a8fff4eca08d52bab71",
    )

    load_kwargs = _build_model_load_kwargs(
        identity=identity,
        torch_module=_FakeTorch,
        max_memory={0: 1},
        offload_folder=tmp_path,
    )
    generation_kwargs = _build_generation_kwargs(
        exact_model_identifier=identity.exact_model_identifier,
        tokenizer=_ChatTokenizer(),
    )

    assert "attn_implementation" not in load_kwargs
    assert "use_cache" not in load_kwargs
    assert "use_cache" not in generation_kwargs


def test_phi3_dynamic_cache_shim_allows_omitted_layer_index(monkeypatch) -> None:
    cache_utils_module = types.ModuleType("transformers.cache_utils")

    class FakeDynamicCache:
        def __init__(self) -> None:
            self.seen_tokens = 7
            self.calls: list[int] = []

        def get_seq_length(self, layer_idx):
            self.calls.append(layer_idx)
            return 100 + layer_idx

        def get_max_length(self):
            return 110

    cache_utils_module.DynamicCache = FakeDynamicCache
    transformers_module = types.ModuleType("transformers")
    transformers_module.cache_utils = cache_utils_module
    monkeypatch.setitem(sys.modules, "transformers", transformers_module)
    monkeypatch.setitem(sys.modules, "transformers.cache_utils", cache_utils_module)

    from phase5.runtime.model_backend_adapter import _install_phi3_dynamic_cache_compatibility_shim

    _install_phi3_dynamic_cache_compatibility_shim()

    cache = FakeDynamicCache()
    legacy = FakeDynamicCache.from_legacy_cache(None)

    assert isinstance(legacy, FakeDynamicCache)
    assert FakeDynamicCache.from_legacy_cache(cache) is cache
    assert cache.get_seq_length() == 7
    assert cache.calls == []
    assert cache.get_seq_length(3) == 103
    assert cache.calls == [3]
    assert cache.get_usable_length(5, 3) == 103
    assert cache.get_usable_length(20, 3) == 90


def _copy_text(source: Path, destination: Path, *, replacement: tuple[str, str] | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    if replacement is not None:
        before, after = replacement
        text = text.replace(before, after)
    destination.write_text(text, encoding="utf-8")


def _prepare_frozen_model_root(tmp_path: Path, *, mutate: tuple[Path, tuple[str, str]] | None = None) -> Path:
    identity = load_frozen_model_backend_identity()
    slot_number = identity.model_id.removeprefix("M")
    root = tmp_path
    for relative in (
        "phase5/configs/upstream_artifact_registry.json",
        "phase5/manifests/model_runtime_authority_v2.json",
        "phase4/configs/model_set_freeze.yaml",
        f"phase4/configs/model_{slot_number}_freeze.yaml",
        "phase4_5/configs/phase45_selected_model.yaml",
        "phase4_5/configs/phase45_local_dryrun.yaml",
    ):
        source = Path(relative)
        destination = root / relative
        replacement = None
        if mutate is not None and source == mutate[0]:
            replacement = mutate[1]
        _copy_text(source, destination, replacement=replacement)
    return root


def test_load_frozen_model_backend_identity_matches_frozen_inputs() -> None:
    identity = load_frozen_model_backend_identity()

    assert identity.model_id == "M3"
    assert identity.exact_model_identifier == "mistralai/Mistral-7B-Instruct-v0.3"
    assert identity.quantization == "float16"
    assert identity.backend == "transformers"
    assert identity.backend_version == "transformers==5.0.0"
    assert identity.tokenizer_identity == "mistralai/Mistral-7B-Instruct-v0.3"
    assert identity.model_digest == "UNAVAILABLE_NOT_RECORDED_IN_PHASE3"
    assert identity.model_digest_is_placeholder is True


def test_adapter_accepts_exact_runtime_snapshot() -> None:
    identity = load_frozen_model_backend_identity()
    adapter = build_frozen_model_backend_adapter()

    adapter.validate_runtime_snapshot(
        {
            "model_id": identity.model_id,
            "exact_model_identifier": identity.exact_model_identifier,
            "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "quantization": identity.quantization,
            "backend": identity.backend,
            "backend_version": identity.backend_version,
            "tokenizer_identity": identity.tokenizer_identity,
            "ollama_version": None,
        }
    )


def test_adapter_rejects_placeholder_runtime_digest() -> None:
    identity = load_frozen_model_backend_identity()
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(RuntimeMismatchError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": identity.model_id,
                "exact_model_identifier": identity.exact_model_identifier,
                "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
                "quantization": identity.quantization,
                "backend": identity.backend,
                "backend_version": identity.backend_version,
                "tokenizer_identity": identity.tokenizer_identity,
                "ollama_version": None,
            }
        )


def test_adapter_rejects_backend_version_mismatch() -> None:
    identity = load_frozen_model_backend_identity()
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(RuntimeMismatchError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": identity.model_id,
                "exact_model_identifier": identity.exact_model_identifier,
                "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "quantization": identity.quantization,
                "backend": identity.backend,
                "backend_version": "transformers==9.9.9",
                "tokenizer_identity": identity.tokenizer_identity,
                "ollama_version": None,
            }
        )


def test_missing_selected_model_file_fails_closed(tmp_path: Path) -> None:
    identity = load_frozen_model_backend_identity()
    slot_number = identity.model_id.removeprefix("M")
    root = tmp_path
    _copy_text(Path("phase5/configs/upstream_artifact_registry.json"), root / "phase5/configs/upstream_artifact_registry.json")
    _copy_text(Path("phase4/configs/model_set_freeze.yaml"), root / "phase4/configs/model_set_freeze.yaml")
    _copy_text(Path(f"phase4/configs/model_{slot_number}_freeze.yaml"), root / f"phase4/configs/model_{slot_number}_freeze.yaml")
    _copy_text(
        Path("phase4_5/configs/phase45_local_dryrun.yaml"),
        root / "phase4_5/configs/phase45_local_dryrun.yaml",
    )

    with pytest.raises(MissingFrozenSettingError):
        load_frozen_model_backend_identity(root=root)


def test_selected_model_divergence_fails_closed(tmp_path: Path) -> None:
    identity = load_frozen_model_backend_identity()
    root = _prepare_frozen_model_root(
        tmp_path,
        mutate=(
            Path("phase4_5/configs/phase45_local_dryrun.yaml"),
            (f"selected_model_identifier: {identity.exact_model_identifier}", "selected_model_identifier: broken/model"),
        ),
    )

    with pytest.raises(RuntimeMismatchError):
        load_frozen_model_backend_identity(root=root)


def test_model_freeze_backend_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    identity = load_frozen_model_backend_identity()
    slot_number = identity.model_id.removeprefix("M")
    root = _prepare_frozen_model_root(
        tmp_path,
        mutate=(
            Path(f"phase4/configs/model_{slot_number}_freeze.yaml"),
            ("backend_version: transformers==5.0.0", "backend_version: transformers==9.9.9"),
        ),
    )

    import hashlib
    from types import SimpleNamespace

    class FakeRegistry:
        def require(self, label: str) -> SimpleNamespace:
            if label == "Model freeze set":
                relative = Path("phase4/configs/model_set_freeze.yaml")
                expected = hashlib.sha256(Path("phase4/configs/model_set_freeze.yaml").read_bytes()).hexdigest()
                actual = (root / relative).read_bytes()
                if hashlib.sha256(actual).hexdigest() != expected:
                    raise FrozenArtifactHashError("model set hash mismatch")
                return SimpleNamespace(actual_paths=(relative,), sha256=(expected,), status="FOUND_VERIFIED")
            if label == f"Model freeze {identity.model_id}":
                relative = Path(f"phase4/configs/model_{slot_number}_freeze.yaml")
                expected = hashlib.sha256(Path(f"phase4/configs/model_{slot_number}_freeze.yaml").read_bytes()).hexdigest()
                actual = (root / relative).read_bytes()
                if hashlib.sha256(actual).hexdigest() != expected:
                    raise FrozenArtifactHashError("model freeze hash mismatch")
                return SimpleNamespace(actual_paths=(relative,), sha256=(expected,), status="FOUND_VERIFIED")
            raise MissingFrozenSettingError(f"missing label: {label}")

    monkeypatch.setattr("phase5.runtime.model_backend_adapter.load_upstream_artifact_registry", lambda path: FakeRegistry())
    with pytest.raises(FrozenArtifactHashError):
        load_frozen_model_backend_identity(root=root)


def test_missing_runtime_snapshot_field_fails_closed() -> None:
    identity = load_frozen_model_backend_identity()
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(MissingFrozenSettingError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": identity.model_id,
                "exact_model_identifier": identity.exact_model_identifier,
                "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "quantization": identity.quantization,
                "backend": identity.backend,
                "tokenizer_identity": identity.tokenizer_identity,
                "ollama_version": None,
            }
        )


def test_malformed_frozen_model_path_fails_closed(tmp_path: Path) -> None:
    identity = load_frozen_model_backend_identity()
    slot_number = identity.model_id.removeprefix("M")
    root = tmp_path
    _copy_text(Path("phase5/configs/upstream_artifact_registry.json"), root / "phase5/configs/upstream_artifact_registry.json")
    (root / "phase4/configs").mkdir(parents=True, exist_ok=True)
    (root / "phase4_5/configs").mkdir(parents=True, exist_ok=True)
    (root / "phase4/configs/model_set_freeze.yaml").write_text(f"{identity.model_id}: {identity.exact_model_identifier}\n", encoding="utf-8")
    (root / f"phase4/configs/model_{slot_number}_freeze.yaml").write_text("[]\n", encoding="utf-8")
    (root / "phase4_5/configs/phase45_selected_model.yaml").write_text(
        f"model_slot: {identity.model_id}\nexact_model_identifier: {identity.exact_model_identifier}\nfrozen_source: phase4/configs/model_set_freeze.yaml\n",
        encoding="utf-8",
    )
    (root / "phase4_5/configs/phase45_local_dryrun.yaml").write_text(
        f"selected_model_slot: {identity.model_id}\nselected_model_identifier: {identity.exact_model_identifier}\n",
        encoding="utf-8",
    )

    with pytest.raises(SchemaInvariantError):
        load_frozen_model_backend_identity(root=root)
