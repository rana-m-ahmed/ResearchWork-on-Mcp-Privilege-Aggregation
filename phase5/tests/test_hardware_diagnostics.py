from __future__ import annotations

from phase5.runtime import engine


def test_optional_nvidia_smi_diagnostic_does_not_block_without_binary(monkeypatch) -> None:
    monkeypatch.setattr(engine.shutil, "which", lambda _: None)
    assert engine._capture_nvidia_smi(cuda_available=True) == ""


def test_optional_nvidia_smi_diagnostic_skips_when_cuda_is_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(engine.shutil, "which", lambda _: "nvidia-smi")
    assert engine._capture_nvidia_smi(cuda_available=False) == ""
