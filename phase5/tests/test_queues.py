from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from phase5.domain import (
    ArtifactRegistry,
    DefenseCondition,
    Density,
    FrozenTrialRow,
    MetadataSurfaceCondition,
    ModelSlot,
    PayloadCondition,
    TrialAssessment,
    TrialOutcome,
    TrialPhase,
    validate_primary_outcome,
)
from phase5.domain.config import RegistryEntry, load_upstream_artifact_registry
from phase5.domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from phase5.queues import (
    FrozenQueue,
    FrozenQueueBundle,
    FrozenQueueLoadReport,
    FrozenQueueRow,
    load_core_queue,
    load_defense_queue,
    load_frozen_queue_bundle,
    load_utility_queue,
    validate_frozen_queue_bundle,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _actual_registry() -> ArtifactRegistry:
    return load_upstream_artifact_registry()


def _registry_with_overrides(*, core_path: Path | None = None, core_hash: str | None = None, payload_map_path: Path | None = None, payload_map_hash: str | None = None) -> ArtifactRegistry:
    base = _actual_registry()
    entries = []
    index: dict[str, RegistryEntry] = {}
    for entry in base.entries:
        updated = entry
        if entry.label == "Trial order core" and core_path is not None and core_hash is not None:
            updated = RegistryEntry(
                label=entry.label,
                actual_paths=(core_path,),
                sha256=(core_hash,),
                status=entry.status,
                notes=entry.notes,
            )
        if entry.label == "Payload reference map" and payload_map_path is not None and payload_map_hash is not None:
            updated = RegistryEntry(
                label=entry.label,
                actual_paths=(payload_map_path,),
                sha256=(payload_map_hash,),
                status=entry.status,
                notes=entry.notes,
            )
        entries.append(updated)
        index[updated.label] = updated
    return ArtifactRegistry(
        registry_id=base.registry_id,
        registry_version=base.registry_version,
        generated_utc=base.generated_utc,
        status=base.status,
        source_path=base.source_path,
        sha256=base.sha256,
        entries=tuple(entries),
        _index=MappingProxyType(index),
    )


def _full_trial_row() -> dict[str, object]:
    return {
        "phase": "phase5_adversarial_core",
        "official_trial": False,
        "trial_id": "kaggle-01",
        "run_id": "phase4_5_kaggle_real_smoke_run",
        "branch": "phase5-model-1",
        "git_commit_hash": "3a92c2d7e2987290b801cee95ae3c506254ff8f6",
        "timestamp_utc": "2026-07-05T12:40:35.067749+00:00",
        "model_id": "M1",
        "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
        "model_digest": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "quantization": "float16",
        "backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "ollama_version": None,
        "density": "D3",
        "metadata_surface_condition": "POISON_TD",
        "attack_family": "DIRECT_OVERRIDE",
        "defense_condition": "BASELINE",
        "payload_id": "kaggle_smoke_01",
        "phase1_payload_hash": "b913d5ae30d568588539ee592a978420358a31f42263b8d7571e31ef0e7ab4c6",
        "payload_hash": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "adversarial_payload_present": True,
        "payload_condition": "PHASE1_HASH_AUTHORIZED",
    }


def test_frozen_queue_bundle_reconciles_real_fixture() -> None:
    bundle = load_frozen_queue_bundle()

    assert bundle.core.row_count == 2808
    assert bundle.defense.row_count == 0
    assert bundle.utility.row_count == 0
    assert bundle.core.model_counts() == {"M1": 702, "M2": 702, "M3": 702, "M4": 702}
    assert bundle.core.density_counts() == {"D1": 936, "D3": 936, "D5": 936}
    assert bundle.core.defense_counts() == {"IHR_SPCE": 2808}
    assert bundle.core.status_values() == ("PENDING",)
    assert list(bundle.iter_rows()) == list(bundle.core.rows)

    registry = _actual_registry()
    assert bundle.core.source_sha256 == registry.require("Trial order core").sha256[0]
    assert bundle.defense.source_sha256 == registry.require("Trial order defense").sha256[0]
    assert bundle.utility.source_sha256 == registry.require("Trial order utility").sha256[0]


def test_queue_iteration_is_deterministic() -> None:
    bundle = load_frozen_queue_bundle()

    first = tuple(bundle.iter_rows())
    second = tuple(bundle.iter_rows())

    assert first == second
    assert tuple(row.row_reference for row in first) == tuple(row.row_reference for row in second)


def test_no_concatenation_or_reordering_in_bundle_iteration() -> None:
    core_row = FrozenQueueRow(
        queue_name="core",
        order_index=1,
        trial_id=load_frozen_queue_bundle().core.rows[0].trial_id,
        model_id=ModelSlot.M1,
        density=Density.D3,
        payload_id="PAYLOAD_000001",
        payload_condition=PayloadCondition.PHASE1_HASH_AUTHORIZED,
        defense_condition=DefenseCondition.IHR_SPCE,
        status="PENDING",
        source_path=Path("phase4/frozen_bundle/trial_order_core.csv"),
        source_sha256="core",
    )
    defense_row = FrozenQueueRow(
        queue_name="defense",
        order_index=1,
        trial_id=load_frozen_queue_bundle().core.rows[1].trial_id,
        model_id=ModelSlot.M2,
        density=Density.D5,
        payload_id="PAYLOAD_000002",
        payload_condition=PayloadCondition.PHASE1_HASH_AUTHORIZED,
        defense_condition=DefenseCondition.IHR_SPCE,
        status="PENDING",
        source_path=Path("phase4/frozen_bundle/trial_order_defense.csv"),
        source_sha256="defense",
    )
    utility_row = FrozenQueueRow(
        queue_name="utility",
        order_index=1,
        trial_id=load_frozen_queue_bundle().core.rows[2].trial_id,
        model_id=ModelSlot.M3,
        density=Density.D1,
        payload_id="PAYLOAD_000003",
        payload_condition=PayloadCondition.PHASE1_HASH_AUTHORIZED,
        defense_condition=DefenseCondition.IHR_SPCE,
        status="PENDING",
        source_path=Path("phase4/frozen_bundle/trial_order_utility.csv"),
        source_sha256="utility",
    )
    bundle = FrozenQueueBundle(
        core=FrozenQueue("core", Path("c.csv"), "core", ("trial_id",), (core_row,)),
        defense=FrozenQueue("defense", Path("d.csv"), "defense", ("trial_id",), (defense_row,)),
        utility=FrozenQueue("utility", Path("u.csv"), "utility", ("trial_id",), (utility_row,)),
    )

    assert tuple(bundle.iter_rows()) == (core_row, defense_row, utility_row)


def test_malformed_and_missing_field_rows_fail_closed(tmp_path: Path) -> None:
    source = Path("phase4/frozen_bundle/trial_order_core.csv")
    rows = list(csv.reader(source.read_text(encoding="utf-8").splitlines()))
    rows[0] = rows[0][:-1]
    broken = tmp_path / "trial_order_core.csv"
    broken.write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")

    registry = _registry_with_overrides(core_path=broken, core_hash=_sha256(broken))
    with pytest.raises(SchemaInvariantError):
        load_frozen_queue_bundle(registry=registry)


def test_duplicate_identity_row_fails_closed(tmp_path: Path) -> None:
    source_rows = list(csv.reader(Path("phase4/frozen_bundle/trial_order_core.csv").read_text(encoding="utf-8").splitlines()))
    duplicate_rows = source_rows[:]
    duplicate_rows.insert(3, duplicate_rows[2])
    path = tmp_path / "trial_order_core.csv"
    path.write_text("\n".join(",".join(row) for row in duplicate_rows) + "\n", encoding="utf-8")

    registry = _registry_with_overrides(core_path=path, core_hash=_sha256(path))
    with pytest.raises(SchemaInvariantError):
        load_frozen_queue_bundle(registry=registry)


def test_payload_reference_mismatch_fails_closed(tmp_path: Path) -> None:
    source_rows = list(csv.reader(Path("phase4/frozen_bundle/trial_order_core.csv").read_text(encoding="utf-8").splitlines()))
    rows = [source_rows[0], source_rows[1], source_rows[2][:]]
    rows[2][3] = "PAYLOAD_999999"
    rows.extend(source_rows[3:])
    path = tmp_path / "trial_order_core.csv"
    path.write_text("\n".join(",".join(row) for row in rows) + "\n", encoding="utf-8")

    registry = _registry_with_overrides(core_path=path, core_hash=_sha256(path))
    with pytest.raises(MissingFrozenSettingError):
        load_frozen_queue_bundle(registry=registry)


def test_hash_mismatch_fails_closed(tmp_path: Path) -> None:
    source = Path("phase4/frozen_bundle/trial_order_core.csv")
    mutated = tmp_path / "trial_order_core.csv"
    mutated.write_bytes(source.read_bytes()[:-1] + b"X")

    registry = _registry_with_overrides(core_path=mutated, core_hash=_sha256(source))
    with pytest.raises(FrozenArtifactHashError):
        load_frozen_queue_bundle(registry=registry)


def test_utility_row_semantics_and_d1_structure() -> None:
    utility_row = _full_trial_row()
    utility_row.update(
        {
            "phase": "phase5_utility_preservation",
            "density": "D5",
            "metadata_surface_condition": "CLEAN",
            "attack_family": "NONE",
            "defense_condition": "IHR_SPCE",
            "payload_id": "PAYLOAD_000001",
            "phase1_payload_hash": None,
            "payload_hash": None,
            "adversarial_payload_present": False,
            "payload_condition": "NONE",
        }
    )
    row = FrozenTrialRow.from_mapping(utility_row)
    assert row.phase is TrialPhase.PHASE5_UTILITY_PRESERVATION
    assert row.attack_family.value == "NONE"
    assert row.metadata_surface_condition is MetadataSurfaceCondition.CLEAN
    assert row.phase1_payload_hash is None
    assert row.payload_hash is None

    validate_primary_outcome(TrialAssessment(density=Density.D1, outcome=TrialOutcome.HIJACK_ATTEMPT))
    with pytest.raises(SchemaInvariantError):
        validate_primary_outcome(TrialAssessment(density=Density.D1, outcome=TrialOutcome.ATTACK_SUCCESS))


def test_queue_loader_helpers_return_specific_queue_views() -> None:
    assert load_core_queue().row_count == 2808
    assert load_defense_queue().row_count == 0
    assert load_utility_queue().row_count == 0


def test_validation_report_rendering_is_deterministic(tmp_path: Path) -> None:
    report = validate_frozen_queue_bundle(report_dir=tmp_path)

    assert isinstance(report, FrozenQueueLoadReport)
    assert report.to_json() == report.to_json()
    assert report.to_markdown() == report.to_markdown()
    assert (tmp_path / "P04_queue_separation_and_order_validation.md").is_file()
    assert (tmp_path / "P04_queue_separation_and_order_validation.json").is_file()
