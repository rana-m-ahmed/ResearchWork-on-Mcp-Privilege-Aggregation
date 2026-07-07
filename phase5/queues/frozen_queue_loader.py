"""Read-only loaders for the frozen Phase 5 trial queues.

The repository currently freezes one populated core queue and two header-only
queue placeholders. This module preserves those three artifacts separately,
verifies their hashes against the P00 registry, and exposes deterministic
iterators without reordering or concatenating the underlying rows.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

try:  # pragma: no cover - optional dependency is validated in tests
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from ..domain.config import ArtifactRegistry, load_upstream_artifact_registry
from ..domain.enums import DefenseCondition, Density, ModelSlot, PayloadCondition
from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from ..domain.identifiers import TrialId
from ..guards import repo_root


QUEUE_ORDER = ("core", "defense", "utility")
QUEUE_LABELS = {
    "core": "Trial order core",
    "defense": "Trial order defense",
    "utility": "Trial order utility",
}
QUEUE_PATHS = {
    "core": Path("phase4/frozen_bundle/trial_order_core.csv"),
    "defense": Path("phase4/frozen_bundle/trial_order_defense.csv"),
    "utility": Path("phase4/frozen_bundle/trial_order_utility.csv"),
}
CORE_QUEUE_HEADER = (
    "trial_id",
    "model_id",
    "density",
    "payload_id",
    "payload_condition",
    "defense_condition",
    "status",
)
DEFENSE_QUEUE_HEADER = ("trial_id", "model", "density", "poison")
UTILITY_QUEUE_HEADER = ("trial_id", "model", "density", "defense")
FROZEN_QUEUE_HEADER = CORE_QUEUE_HEADER
_PHASE4_LOCK_LABEL = "Cryptographic lock manifest"
_PAYLOAD_REFERENCE_LABEL = "Payload reference map"
_DEFENSE_FREEZE_LABEL = "Defense freeze"
_PHASE5_MANIFEST_LABEL = "Phase 5 execution manifest"
_QUEUE_STATISTICS_KEY = "queue_statistics"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_json(path: Path) -> Mapping[str, object]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SchemaInvariantError(f"{path.as_posix()} must contain a JSON object")
    return data


def _load_yaml(path: Path) -> Mapping[str, object]:
    if yaml is None:
        raise SchemaInvariantError("pyyaml is required to load the frozen defense configuration")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError(f"{path.as_posix()} must contain a YAML mapping")
    return data


def _load_csv_rows(path: Path) -> tuple[tuple[str, ...], list[tuple[str, ...]]]:
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        raise MissingFrozenSettingError(f"frozen queue is missing its header row: {path.as_posix()}")
    header = tuple(rows[0])
    data_rows = [tuple(row) for row in rows[1:]]
    return header, data_rows


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise SchemaInvariantError(f"{label} must contain a JSON object mapping")
    return value


def _require_queue_stats(registry_doc: Mapping[str, object]) -> Mapping[str, object]:
    stats = registry_doc.get(_QUEUE_STATISTICS_KEY)
    if not isinstance(stats, dict):
        raise MissingFrozenSettingError("upstream registry is missing queue_statistics")
    return stats


def _require_payload_reference_map(root: Path, registry: ArtifactRegistry, payload_reference_map_path: Path | None) -> tuple[Path, Mapping[str, object], str]:
    if payload_reference_map_path is None:
        entry = registry.require(_PAYLOAD_REFERENCE_LABEL)
        path = root / entry.actual_paths[0]
        expected_sha256 = entry.sha256[0]
    else:
        path = payload_reference_map_path
        expected_sha256 = None
    actual_sha256 = _sha256_file(path)
    if expected_sha256 is not None and actual_sha256.lower() != expected_sha256.lower():
        raise FrozenArtifactHashError(
            f"payload reference map hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    payload_reference_map = _load_json(path)
    return path, payload_reference_map, actual_sha256


@dataclass(frozen=True, slots=True)
class FrozenQueueRow:
    queue_name: str
    order_index: int
    trial_id: TrialId
    model_id: ModelSlot
    density: Density
    payload_id: str
    payload_condition: PayloadCondition
    defense_condition: DefenseCondition
    status: str
    source_path: Path
    source_sha256: str

    @property
    def row_reference(self) -> str:
        return f"{self.queue_name}:{self.order_index:05d}:{self.trial_id}"


@dataclass(frozen=True, slots=True)
class FrozenQueue:
    queue_name: str
    source_path: Path
    source_sha256: str
    header: tuple[str, ...]
    rows: tuple[FrozenQueueRow, ...]

    def __iter__(self):
        return iter(self.rows)

    @property
    def row_count(self) -> int:
        return len(self.rows)

    def trial_ids(self) -> tuple[str, ...]:
        return tuple(str(row.trial_id) for row in self.rows)

    def model_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(row.model_id.value for row in self.rows).items()))

    def density_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(row.density.value for row in self.rows).items()))

    def defense_counts(self) -> dict[str, int]:
        return dict(sorted(Counter(row.defense_condition.value for row in self.rows).items()))

    def status_values(self) -> tuple[str, ...]:
        return tuple(sorted({row.status for row in self.rows}))

    def row_references(self) -> tuple[str, ...]:
        return tuple(row.row_reference for row in self.rows)

    def metrics(self) -> dict[str, object]:
        row_tuples = [tuple(str(value) for value in (
            row.row_reference,
            str(row.trial_id),
            row.model_id.value,
            row.density.value,
            row.payload_id,
            row.payload_condition.value,
            row.defense_condition.value,
            row.status,
        )) for row in self.rows]
        return {
            "queue_name": self.queue_name,
            "row_count": self.row_count,
            "unique_trial_ids": len(set(self.trial_ids())),
            "unique_rows": len({item for item in row_tuples}),
            "non_empty_cells": sum(1 for row in row_tuples for cell in row if cell != ""),
            "duplicates": sorted(trial_id for trial_id, count in Counter(self.trial_ids()).items() if count > 1),
            "by_model": self.model_counts(),
            "by_density": self.density_counts(),
            "by_defense": self.defense_counts(),
            "statuses": list(self.status_values()),
            "first_row_reference": self.row_references()[0] if self.rows else None,
            "last_row_reference": self.row_references()[-1] if self.rows else None,
        }


@dataclass(frozen=True, slots=True)
class FrozenQueueBundle:
    core: FrozenQueue
    defense: FrozenQueue
    utility: FrozenQueue

    def iter_rows(self) -> Iterable[FrozenQueueRow]:
        yield from self.core
        yield from self.defense
        yield from self.utility

    def queues(self) -> tuple[FrozenQueue, FrozenQueue, FrozenQueue]:
        return self.core, self.defense, self.utility

    def metrics(self) -> dict[str, object]:
        return {
            "queues": {queue.queue_name: queue.metrics() for queue in self.queues()},
            "total_rows": sum(queue.row_count for queue in self.queues()),
        }


@dataclass(frozen=True, slots=True)
class FrozenQueueLoadReport:
    task_id: str
    status: str
    generated_utc: str
    repository_root: str
    summary: str
    findings: tuple[str, ...]
    queue_metrics: tuple[tuple[str, object], ...]
    consumed_frozen_inputs: tuple[tuple[str, str], ...]
    queue_hashes: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "generated_utc": self.generated_utc,
            "repository_root": self.repository_root,
            "summary": self.summary,
            "findings": list(self.findings),
            "queue_metrics": {name: value for name, value in self.queue_metrics},
            "consumed_frozen_inputs": [
                {"label": label, "sha256": sha256} for label, sha256 in self.consumed_frozen_inputs
            ],
            "queue_hashes": [
                {"queue_name": queue_name, "sha256": sha256} for queue_name, sha256 in self.queue_hashes
            ],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P04 Frozen Queue Loading Report",
            "",
            "## Verdict",
            "",
            f"- Task: `{self.task_id}`",
            f"- Status: `{self.status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Queue Metrics",
        ]
        for queue_name, metrics in self.queue_metrics:
            lines.append(f"- {queue_name}: `{json.dumps(metrics, sort_keys=True)}`")
        lines.extend(["", "## Findings"])
        if self.findings:
            lines.extend(f"- {item}" for item in self.findings)
        else:
            lines.append("- none")
        lines.extend(["", "## Frozen Inputs"])
        for label, sha256 in self.consumed_frozen_inputs:
            lines.append(f"- {label}: `{sha256}`")
        lines.extend(["", "## Queue Hashes"])
        for queue_name, sha256 in self.queue_hashes:
            lines.append(f"- {queue_name}: `{sha256}`")
        return "\n".join(lines) + "\n"

    def write(self, report_dir: Path) -> None:
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / "P04_queue_separation_and_order_validation.md").write_text(self.to_markdown(), encoding="utf-8")
        (report_dir / "P04_queue_separation_and_order_validation.json").write_text(self.to_json(), encoding="utf-8")


def _build_registry(
    root: Path,
    *,
    registry: ArtifactRegistry | None,
    registry_path: Path | None,
    expected_registry_sha256: str | None,
) -> ArtifactRegistry:
    if registry is not None:
        return registry
    registry_path = registry_path or (root / "phase5" / "configs" / "upstream_artifact_registry.json")
    return load_upstream_artifact_registry(registry_path, expected_sha256=expected_registry_sha256)


def _queue_row_from_mapping(
    *,
    queue_name: str,
    order_index: int,
    source_path: Path,
    source_sha256: str,
    mapping: Mapping[str, str],
    payload_reference_map: Mapping[str, object],
    expected_defense_condition: DefenseCondition,
) -> FrozenQueueRow:
    missing = [field for field in CORE_QUEUE_HEADER if field not in mapping]
    extra = [field for field in mapping if field not in CORE_QUEUE_HEADER]
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing={missing}")
        if extra:
            details.append(f"extra={extra}")
        raise MissingFrozenSettingError(f"queue row field mismatch: {'; '.join(details)}")

    trial_id = TrialId.parse(mapping["trial_id"])
    model_id = ModelSlot.from_value(mapping["model_id"])
    density = Density.from_value(mapping["density"])
    payload_id = mapping["payload_id"]
    payload_condition = PayloadCondition.from_value(mapping["payload_condition"])
    defense_condition = DefenseCondition.from_value(mapping["defense_condition"])
    status = mapping["status"]

    if not payload_id:
        raise SchemaInvariantError("payload_id must be a non-empty string")
    if payload_id not in payload_reference_map:
        raise MissingFrozenSettingError(f"payload reference is missing: {payload_id!r}")
    if payload_reference_map[payload_id] is not None:
        raise SchemaInvariantError(f"payload reference map must preserve null reference placeholders: {payload_id!r}")
    if status != "PENDING":
        raise SchemaInvariantError(f"frozen queue rows must remain pending: {trial_id}")
    if payload_condition is not PayloadCondition.PHASE1_HASH_AUTHORIZED:
        raise SchemaInvariantError("frozen queue rows must use PHASE1_HASH_AUTHORIZED")
    if defense_condition is not expected_defense_condition:
        raise SchemaInvariantError(
            f"frozen queue rows must use defense_condition={expected_defense_condition.value}"
        )

    return FrozenQueueRow(
        queue_name=queue_name,
        order_index=order_index,
        trial_id=trial_id,
        model_id=model_id,
        density=density,
        payload_id=payload_id,
        payload_condition=payload_condition,
        defense_condition=defense_condition,
        status=status,
        source_path=source_path,
        source_sha256=source_sha256,
    )


def _load_single_queue(
    root: Path,
    queue_name: str,
    registry: ArtifactRegistry,
    payload_reference_map: Mapping[str, object],
    registry_doc: Mapping[str, object],
    *,
    expected_header: tuple[str, ...],
    expected_defense_condition: DefenseCondition,
) -> FrozenQueue:
    label = QUEUE_LABELS[queue_name]
    entry = registry.require(label)
    path = root / entry.actual_paths[0]
    actual_sha256 = _sha256_file(path)
    expected_sha256 = entry.sha256[0]
    if actual_sha256.lower() != expected_sha256.lower():
        raise FrozenArtifactHashError(
            f"{queue_name} queue hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )

    header, data_rows = _load_csv_rows(path)
    if header != expected_header:
        raise SchemaInvariantError(
            f"{queue_name} queue header mismatch: expected {expected_header!r}, got {header!r}"
        )

    stats = _require_queue_stats(registry_doc)
    expected_rows = stats.get(f"trial_order_{queue_name}_rows")
    if not isinstance(expected_rows, int):
        raise MissingFrozenSettingError(f"queue statistics missing row count for {queue_name!r}")
    if len(data_rows) != expected_rows:
        raise SchemaInvariantError(
            f"{queue_name} queue row-count mismatch: expected {expected_rows}, got {len(data_rows)}"
        )

    if queue_name in {"defense", "utility"}:
        if data_rows:
            raise SchemaInvariantError(f"{queue_name} queue must remain header-only")
        return FrozenQueue(
            queue_name=queue_name,
            source_path=path,
            source_sha256=actual_sha256,
            header=header,
            rows=(),
        )

    expected_model_counts = stats.get("trial_order_core_by_model")
    expected_density_counts = stats.get("trial_order_core_by_density")
    expected_defense_counts = stats.get("trial_order_core_by_defense_condition")
    expected_unique_trials = stats.get("trial_order_core_unique_trial_ids")
    expected_non_empty_cells = stats.get("trial_order_core_non_empty_cells")
    expected_duplicates = stats.get("trial_order_core_duplicates")
    expected_payload_ids = stats.get("unique_payload_ids_used_in_core")

    rows: list[FrozenQueueRow] = []
    seen_trial_ids: set[str] = set()
    seen_row_tuples: set[tuple[str, ...]] = set()
    for order_index, row in enumerate(data_rows, start=1):
        if len(row) != len(FROZEN_QUEUE_HEADER):
            raise SchemaInvariantError(
                f"core queue row {order_index} has {len(row)} cells, expected {len(FROZEN_QUEUE_HEADER)}"
            )
        mapping = dict(zip(FROZEN_QUEUE_HEADER, row, strict=True))
        queue_row = _queue_row_from_mapping(
            queue_name=queue_name,
            order_index=order_index,
            source_path=path,
            source_sha256=actual_sha256,
            mapping=MappingProxyType(mapping),
            payload_reference_map=payload_reference_map,
            expected_defense_condition=expected_defense_condition,
        )
        row_tuple = tuple(row)
        if queue_row.trial_id.value in seen_trial_ids:
            raise SchemaInvariantError(f"duplicate trial_id found in core queue: {queue_row.trial_id}")
        if row_tuple in seen_row_tuples:
            raise SchemaInvariantError(f"duplicate frozen queue row found at {queue_row.row_reference}")
        seen_trial_ids.add(queue_row.trial_id.value)
        seen_row_tuples.add(row_tuple)
        rows.append(queue_row)

    row_metrics = {
        "unique_trial_ids": len(seen_trial_ids),
        "unique_rows": len(seen_row_tuples),
        "non_empty_cells": sum(1 for row in data_rows for cell in row if cell != ""),
        "duplicates": sorted(trial_id for trial_id, count in Counter(row[0] for row in data_rows).items() if count > 1),
        "by_model": dict(sorted(Counter(row[1] for row in data_rows).items())),
        "by_density": dict(sorted(Counter(row[2] for row in data_rows).items())),
        "by_defense": dict(sorted(Counter(row[5] for row in data_rows).items())),
        "unique_payload_ids": len({row[3] for row in data_rows}),
    }
    expected_by_model = dict(sorted(_require_mapping(expected_model_counts, "trial_order_core_by_model").items()))
    expected_by_density = dict(sorted(_require_mapping(expected_density_counts, "trial_order_core_by_density").items()))
    expected_by_defense = dict(sorted(_require_mapping(expected_defense_counts, "trial_order_core_by_defense_condition").items()))
    if (
        row_metrics["unique_trial_ids"] != expected_unique_trials
        or row_metrics["non_empty_cells"] != expected_non_empty_cells
        or row_metrics["duplicates"] != list(expected_duplicates or [])
        or row_metrics["by_model"] != expected_by_model
        or row_metrics["by_density"] != expected_by_density
        or row_metrics["by_defense"] != expected_by_defense
        or row_metrics["unique_payload_ids"] != expected_payload_ids
    ):
        raise SchemaInvariantError(
            "core queue statistics do not reconcile with the frozen registry summary"
        )

    return FrozenQueue(
        queue_name=queue_name,
        source_path=path,
        source_sha256=actual_sha256,
        header=header,
        rows=tuple(rows),
    )


def load_core_queue(
    *,
    root: Path | None = None,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    payload_reference_map_path: Path | None = None,
    expected_registry_sha256: str | None = None,
) -> FrozenQueue:
    return load_frozen_queue_bundle(
        root=root,
        registry=registry,
        registry_path=registry_path,
        payload_reference_map_path=payload_reference_map_path,
        expected_registry_sha256=expected_registry_sha256,
    ).core


def load_defense_queue(
    *,
    root: Path | None = None,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    payload_reference_map_path: Path | None = None,
    expected_registry_sha256: str | None = None,
) -> FrozenQueue:
    return load_frozen_queue_bundle(
        root=root,
        registry=registry,
        registry_path=registry_path,
        payload_reference_map_path=payload_reference_map_path,
        expected_registry_sha256=expected_registry_sha256,
    ).defense


def load_utility_queue(
    *,
    root: Path | None = None,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    payload_reference_map_path: Path | None = None,
    expected_registry_sha256: str | None = None,
) -> FrozenQueue:
    return load_frozen_queue_bundle(
        root=root,
        registry=registry,
        registry_path=registry_path,
        payload_reference_map_path=payload_reference_map_path,
        expected_registry_sha256=expected_registry_sha256,
    ).utility


def load_frozen_queue_bundle(
    *,
    root: Path | None = None,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    payload_reference_map_path: Path | None = None,
    expected_registry_sha256: str | None = None,
) -> FrozenQueueBundle:
    repository_root = (root or repo_root()).resolve()
    current_registry = _build_registry(
        repository_root,
        registry=registry,
        registry_path=registry_path,
        expected_registry_sha256=expected_registry_sha256,
    )
    registry_doc = _load_json(current_registry.source_path)
    defense_entry = current_registry.require(_DEFENSE_FREEZE_LABEL)
    defense_doc = _load_yaml(repository_root / defense_entry.actual_paths[0])
    defense_value = defense_doc.get("defense")
    if not isinstance(defense_value, str):
        raise MissingFrozenSettingError("frozen defense configuration is missing the defense label")
    expected_defense_condition = DefenseCondition.from_value(defense_value)

    _payload_reference_path, payload_reference_map, _payload_reference_sha256 = _require_payload_reference_map(
        repository_root,
        current_registry,
        payload_reference_map_path,
    )
    core = _load_single_queue(
        repository_root,
        "core",
        current_registry,
        payload_reference_map,
        registry_doc,
        expected_header=CORE_QUEUE_HEADER,
        expected_defense_condition=expected_defense_condition,
    )
    defense = _load_single_queue(
        repository_root,
        "defense",
        current_registry,
        payload_reference_map,
        registry_doc,
        expected_header=DEFENSE_QUEUE_HEADER,
        expected_defense_condition=expected_defense_condition,
    )
    utility = _load_single_queue(
        repository_root,
        "utility",
        current_registry,
        payload_reference_map,
        registry_doc,
        expected_header=UTILITY_QUEUE_HEADER,
        expected_defense_condition=expected_defense_condition,
    )

    manifest_entry = current_registry.require(_PHASE5_MANIFEST_LABEL)
    manifest_hash = _sha256_file(repository_root / manifest_entry.actual_paths[0])
    if manifest_hash.lower() != manifest_entry.sha256[0].lower():
        raise FrozenArtifactHashError(
            f"phase 5 execution manifest hash mismatch: expected {manifest_entry.sha256[0]}, got {manifest_hash}"
        )
    manifest = _load_json(repository_root / manifest_entry.actual_paths[0])
    hashes = _require_mapping(manifest.get("hashes"), "phase5_execution_manifest.hashes")
    metrics = _require_mapping(manifest.get("metrics"), "phase5_execution_manifest.metrics")
    if hashes.get("trial_order_sha256") != core.source_sha256:
        raise FrozenArtifactHashError("phase 5 execution manifest does not reference the frozen core queue hash")
    if hashes.get("phase4_manifest_hash") != current_registry.require(_PHASE4_LOCK_LABEL).sha256[0]:
        raise FrozenArtifactHashError("phase 5 execution manifest does not reference the frozen cryptographic lock")
    if metrics.get("expected_trial_count") != core.row_count:
        raise SchemaInvariantError("phase 5 execution manifest expected_trial_count does not match the core queue")

    return FrozenQueueBundle(core=core, defense=defense, utility=utility)


def validate_frozen_queue_bundle(
    *,
    root: Path | None = None,
    registry: ArtifactRegistry | None = None,
    registry_path: Path | None = None,
    payload_reference_map_path: Path | None = None,
    expected_registry_sha256: str | None = None,
    report_dir: Path | None = None,
) -> FrozenQueueLoadReport:
    repository_root = (root or repo_root()).resolve()
    current_registry = _build_registry(
        repository_root,
        registry=registry,
        registry_path=registry_path,
        expected_registry_sha256=expected_registry_sha256,
    )
    bundle = load_frozen_queue_bundle(
        root=repository_root,
        registry=current_registry,
        payload_reference_map_path=payload_reference_map_path,
    )
    registry_doc = _load_json(current_registry.source_path)
    defense_entry = current_registry.require(_DEFENSE_FREEZE_LABEL)
    defense_sha256 = _sha256_file(repository_root / defense_entry.actual_paths[0])
    payload_reference_entry = current_registry.require(_PAYLOAD_REFERENCE_LABEL)
    payload_reference_sha256 = _sha256_file(repository_root / payload_reference_entry.actual_paths[0])
    manifest_entry = current_registry.require(_PHASE5_MANIFEST_LABEL)
    manifest_sha256 = _sha256_file(repository_root / manifest_entry.actual_paths[0])
    lock_sha256 = current_registry.require(_PHASE4_LOCK_LABEL).sha256[0]
    generated_utc = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    findings: list[str] = []
    queue_metrics = tuple((queue.queue_name, queue.metrics()) for queue in bundle.queues())
    consumed_frozen_inputs = (
        ("Upstream registry", current_registry.sha256),
        ("Defense freeze", defense_sha256),
        ("Payload reference map", payload_reference_sha256),
        ("Phase 4 cryptographic lock", lock_sha256),
        ("Phase 5 execution manifest", manifest_sha256),
        ("Trial order core", bundle.core.source_sha256),
        ("Trial order defense", bundle.defense.source_sha256),
        ("Trial order utility", bundle.utility.source_sha256),
    )
    queue_hashes = tuple((queue.queue_name, queue.source_sha256) for queue in bundle.queues())
    manifest = _load_json(repository_root / manifest_entry.actual_paths[0])
    metrics = _require_mapping(manifest.get("metrics"), "phase5_execution_manifest.metrics")
    if metrics.get("expected_trial_count") != bundle.core.row_count:
        findings.append("expected_trial_count mismatch")
    summary = (
        "Frozen queue loading passed with strict hash verification, queue separation, exact order preservation, "
        "and registry-bound row reconciliation."
        if not findings
        else "Frozen queue loading completed with validation findings."
    )
    report = FrozenQueueLoadReport(
        task_id="P04",
        status="PASS" if not findings else "FAIL",
        generated_utc=generated_utc,
        repository_root=repository_root.as_posix(),
        summary=summary,
        findings=tuple(findings),
        queue_metrics=queue_metrics,
        consumed_frozen_inputs=consumed_frozen_inputs,
        queue_hashes=queue_hashes,
    )
    if report_dir is not None:
        report.write(report_dir)
    return report
