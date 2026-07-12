from __future__ import annotations

from pathlib import Path

import pytest

from phase5.domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, RuntimeMismatchError, SchemaInvariantError
from phase5.runtime import build_frozen_model_backend_adapter, load_frozen_model_backend_identity
from phase5.runtime.model_backend_adapter import build_model_load_memory_plan


class _FakeCuda:
    @staticmethod
    def mem_get_info(device: int) -> tuple[int, int]:
        assert device == 0
        return 16 * 1024**3, 16 * 1024**3


class _FakeTorch:
    cuda = _FakeCuda()


def test_model_load_memory_plan_reserves_gpu_and_cpu_headroom(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("phase5.runtime.model_backend_adapter._available_cpu_memory_bytes", lambda: 30 * 1024**3)
    monkeypatch.setenv("PHASE5_MODEL_OFFLOAD_DIR", str(tmp_path / "offload"))

    max_memory, offload_folder = build_model_load_memory_plan(_FakeTorch())

    assert max_memory == {0: 14 * 1024**3, "cpu": 26 * 1024**3}
    assert offload_folder == tmp_path / "offload"
    assert offload_folder.is_dir()


def test_model_load_memory_plan_fails_closed_on_insufficient_gpu(monkeypatch) -> None:
    monkeypatch.setattr(_FakeCuda, "mem_get_info", staticmethod(lambda device: (5 * 1024**3, 16 * 1024**3)))
    monkeypatch.setattr("phase5.runtime.model_backend_adapter._available_cpu_memory_bytes", lambda: 30 * 1024**3)

    with pytest.raises(RuntimeMismatchError, match="insufficient free GPU memory"):
        build_model_load_memory_plan(_FakeTorch())


def _copy_text(source: Path, destination: Path, *, replacement: tuple[str, str] | None = None) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    text = source.read_text(encoding="utf-8")
    if replacement is not None:
        before, after = replacement
        text = text.replace(before, after)
    destination.write_text(text, encoding="utf-8")


def _prepare_frozen_model_root(tmp_path: Path, *, mutate: tuple[Path, tuple[str, str]] | None = None) -> Path:
    root = tmp_path
    for relative in (
        "phase5/configs/upstream_artifact_registry.json",
        "phase5/manifests/model_runtime_authority_v2.json",
        "phase4/configs/model_set_freeze.yaml",
        "phase4/configs/model_1_freeze.yaml",
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

    assert identity.model_id == "M1"
    assert identity.exact_model_identifier == "Qwen/Qwen2.5-7B-Instruct"
    assert identity.quantization == "float16"
    assert identity.backend == "transformers"
    assert identity.backend_version == "transformers==5.0.0"
    assert identity.tokenizer_identity == "Qwen/Qwen2.5-7B-Instruct"
    assert identity.model_digest == "UNAVAILABLE_NOT_RECORDED_IN_PHASE3"
    assert identity.model_digest_is_placeholder is True


def test_adapter_accepts_exact_runtime_snapshot() -> None:
    adapter = build_frozen_model_backend_adapter()

    adapter.validate_runtime_snapshot(
        {
            "model_id": "M1",
            "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
            "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
            "quantization": "float16",
            "backend": "transformers",
            "backend_version": "transformers==5.0.0",
            "tokenizer_identity": "Qwen/Qwen2.5-7B-Instruct",
            "ollama_version": None,
        }
    )


def test_adapter_rejects_placeholder_runtime_digest() -> None:
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(RuntimeMismatchError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": "M1",
                "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
                "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
                "quantization": "float16",
                "backend": "transformers",
                "backend_version": "transformers==5.0.0",
                "tokenizer_identity": "Qwen/Qwen2.5-7B-Instruct",
                "ollama_version": None,
            }
        )


def test_adapter_rejects_backend_version_mismatch() -> None:
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(RuntimeMismatchError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": "M1",
                "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
                "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "quantization": "float16",
                "backend": "transformers",
                "backend_version": "transformers==9.9.9",
                "tokenizer_identity": "Qwen/Qwen2.5-7B-Instruct",
                "ollama_version": None,
            }
        )


def test_missing_selected_model_file_fails_closed(tmp_path: Path) -> None:
    root = tmp_path
    _copy_text(Path("phase5/configs/upstream_artifact_registry.json"), root / "phase5/configs/upstream_artifact_registry.json")
    _copy_text(Path("phase4/configs/model_set_freeze.yaml"), root / "phase4/configs/model_set_freeze.yaml")
    _copy_text(Path("phase4/configs/model_1_freeze.yaml"), root / "phase4/configs/model_1_freeze.yaml")
    _copy_text(
        Path("phase4_5/configs/phase45_local_dryrun.yaml"),
        root / "phase4_5/configs/phase45_local_dryrun.yaml",
    )

    with pytest.raises(MissingFrozenSettingError):
        load_frozen_model_backend_identity(root=root)


def test_selected_model_divergence_fails_closed(tmp_path: Path) -> None:
    root = _prepare_frozen_model_root(
        tmp_path,
        mutate=(
            Path("phase4_5/configs/phase45_local_dryrun.yaml"),
            ("selected_model_identifier: Qwen/Qwen2.5-7B-Instruct", "selected_model_identifier: broken/model"),
        ),
    )

    with pytest.raises(RuntimeMismatchError):
        load_frozen_model_backend_identity(root=root)


def test_model_freeze_backend_mismatch_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _prepare_frozen_model_root(
        tmp_path,
        mutate=(
            Path("phase4/configs/model_1_freeze.yaml"),
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
            if label == "Model freeze M1":
                relative = Path("phase4/configs/model_1_freeze.yaml")
                expected = hashlib.sha256(Path("phase4/configs/model_1_freeze.yaml").read_bytes()).hexdigest()
                actual = (root / relative).read_bytes()
                if hashlib.sha256(actual).hexdigest() != expected:
                    raise FrozenArtifactHashError("model freeze hash mismatch")
                return SimpleNamespace(actual_paths=(relative,), sha256=(expected,), status="FOUND_VERIFIED")
            raise MissingFrozenSettingError(f"missing label: {label}")

    monkeypatch.setattr("phase5.runtime.model_backend_adapter.load_upstream_artifact_registry", lambda path: FakeRegistry())
    with pytest.raises(FrozenArtifactHashError):
        load_frozen_model_backend_identity(root=root)


def test_missing_runtime_snapshot_field_fails_closed() -> None:
    adapter = build_frozen_model_backend_adapter()

    with pytest.raises(MissingFrozenSettingError):
        adapter.validate_runtime_snapshot(
            {
                "model_id": "M1",
                "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
                "model_digest": "sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
                "quantization": "float16",
                "backend": "transformers",
                "tokenizer_identity": "Qwen/Qwen2.5-7B-Instruct",
                "ollama_version": None,
            }
        )


def test_malformed_frozen_model_path_fails_closed(tmp_path: Path) -> None:
    root = tmp_path
    _copy_text(Path("phase5/configs/upstream_artifact_registry.json"), root / "phase5/configs/upstream_artifact_registry.json")
    (root / "phase4/configs").mkdir(parents=True, exist_ok=True)
    (root / "phase4_5/configs").mkdir(parents=True, exist_ok=True)
    (root / "phase4/configs/model_set_freeze.yaml").write_text("M1: Qwen/Qwen2.5-7B-Instruct\n", encoding="utf-8")
    (root / "phase4/configs/model_1_freeze.yaml").write_text("[]\n", encoding="utf-8")
    (root / "phase4_5/configs/phase45_selected_model.yaml").write_text(
        "model_slot: M1\nexact_model_identifier: Qwen/Qwen2.5-7B-Instruct\nfrozen_source: phase4/configs/model_set_freeze.yaml\n",
        encoding="utf-8",
    )
    (root / "phase4_5/configs/phase45_local_dryrun.yaml").write_text(
        "selected_model_slot: M1\nselected_model_identifier: Qwen/Qwen2.5-7B-Instruct\n",
        encoding="utf-8",
    )

    with pytest.raises(SchemaInvariantError):
        load_frozen_model_backend_identity(root=root)
