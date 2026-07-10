from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from phase5.domain import MissingFrozenSettingError, FrozenArtifactHashError, load_upstream_artifact_registry


def _registry_hash() -> str:
    path = Path("phase5/configs/upstream_artifact_registry.json")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_registry_loads_and_resolves_verified_entries() -> None:
    registry = load_upstream_artifact_registry(expected_sha256=_registry_hash())
    entry = registry.require("Phase 4 GO report")

    assert entry.verified is True
    assert entry.actual_paths[0].as_posix() == "phase4/reports/remediation_v2/phase4_corrected_go_no_go_decision.md"
    actual_hash = hashlib.sha256(entry.actual_paths[0].read_bytes()).hexdigest()
    assert entry.sha256[0].lower() == actual_hash.lower()
    assert "Phase 4 GO report" in registry.labels()


def test_registry_hash_mismatch_fails_closed() -> None:
    with pytest.raises(FrozenArtifactHashError):
        load_upstream_artifact_registry(expected_sha256="0" * 64)


def test_missing_frozen_setting_fails_closed(tmp_path: Path) -> None:
    registry_path = tmp_path / "registry.json"
    registry_path.write_text(
        json.dumps({"registry_id": "P00", "status": "COMPLETE", "required_items": {}}),
        encoding="utf-8",
    )

    registry = load_upstream_artifact_registry(registry_path, verify_verified_entries=False)
    with pytest.raises(MissingFrozenSettingError):
        registry.require("Phase 4 GO report")


def test_verified_registry_hashes_match_checkout_attributes() -> None:
    registry = load_upstream_artifact_registry(verify_verified_entries=False)

    for entry in registry.entries:
        if not entry.verified:
            continue
        for relative_path, expected_sha256 in zip(entry.actual_paths, entry.sha256, strict=True):
            actual_bytes = relative_path.read_bytes()
            actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()
            assert actual_sha256.lower() == expected_sha256.lower(), relative_path.as_posix()
