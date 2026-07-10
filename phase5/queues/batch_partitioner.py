"""Deterministic Phase 5 batch partitioning.

The official Phase 5 plan fixes the accepted target totals at 10,200 across
four models. Batch partitioning is an operational integrity step: it freezes a
contiguous ordering, emits collision-resistant batch identifiers, and never
silently rewrites an existing manifest.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Mapping, Sequence

from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError


DEFAULT_DATASET_VERSION = "P5-DV-1.0.0-A7C91E42"
DEFAULT_BATCH_SIZE = 50

MODEL_SLOTS = ("M1", "M2", "M3", "M4")
WORKLOAD_ORDER = (
    "phase5_adversarial_core",
    "phase5_adversarial_defense",
    "phase5_utility_preservation",
)

WORKLOAD_TARGET_COUNTS = {
    "phase5_adversarial_core": 1350,
    "phase5_adversarial_defense": 600,
    "phase5_utility_preservation": 600,
}

WORKLOAD_BATCH_SCOPES = {
    "phase5_adversarial_core": {"density_scope": "MIX", "surface_scope": "MIX", "defense_scope": "BASELINE"},
    "phase5_adversarial_defense": {"density_scope": "MIX", "surface_scope": "MIX", "defense_scope": "IHR_SPCE"},
    "phase5_utility_preservation": {"density_scope": "MIX", "surface_scope": "CLEAN", "defense_scope": "MIX"},
}


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _write_if_unchanged(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8")
        if existing != content:
            raise FrozenArtifactHashError(f"immutable manifest refusal for {path.as_posix()}")
        return
    path.write_text(content, encoding="utf-8")


@dataclass(frozen=True, slots=True)
class BatchSlice:
    dataset_version: str
    model_slot: str
    workload: str
    batch_index: int
    start_ordinal: int
    end_ordinal: int
    row_count: int
    density_scope: str
    surface_scope: str
    defense_scope: str
    run_token: str
    slice_token: str
    batch_artifact_id: str
    scope_digest: str

    @property
    def batch_key(self) -> str:
        return (
            f"{self.dataset_version}:{self.model_slot}:{self.workload}:{self.batch_index:03d}:"
            f"{self.start_ordinal:05d}-{self.end_ordinal:05d}"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_artifact_id": self.batch_artifact_id,
            "batch_index": self.batch_index,
            "batch_key": self.batch_key,
            "batch_size": self.row_count,
            "dataset_version": self.dataset_version,
            "defense_scope": self.defense_scope,
            "density_scope": self.density_scope,
            "end_ordinal": self.end_ordinal,
            "model_slot": self.model_slot,
            "row_count": self.row_count,
            "run_token": self.run_token,
            "scope_digest": self.scope_digest,
            "slice_token": self.slice_token,
            "start_ordinal": self.start_ordinal,
            "surface_scope": self.surface_scope,
            "workload": self.workload,
        }


@dataclass(frozen=True, slots=True)
class WorkloadPartition:
    workload: str
    target_count: int
    batches: tuple[BatchSlice, ...]

    @property
    def batch_count(self) -> int:
        return len(self.batches)

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_count": self.batch_count,
            "batches": [batch.to_dict() for batch in self.batches],
            "target_count": self.target_count,
            "workload": self.workload,
        }


@dataclass(frozen=True, slots=True)
class ModelCampaignPartition:
    model_slot: str
    target_count: int
    workload_partitions: tuple[WorkloadPartition, ...]

    @property
    def batch_count(self) -> int:
        return sum(partition.batch_count for partition in self.workload_partitions)

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_count": self.batch_count,
            "model_slot": self.model_slot,
            "target_count": self.target_count,
            "workload_partitions": [partition.to_dict() for partition in self.workload_partitions],
        }


@dataclass(frozen=True, slots=True)
class BatchPartitionManifest:
    task_id: str
    status: str
    generated_utc: str
    dataset_version: str
    batch_size: int
    total_targets: int
    model_campaigns: tuple[ModelCampaignPartition, ...]
    source_evidence: tuple[tuple[str, str], ...]
    manifest_sha256: str

    @property
    def total_batches(self) -> int:
        return sum(campaign.batch_count for campaign in self.model_campaigns)

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_size": self.batch_size,
            "dataset_version": self.dataset_version,
            "generated_utc": self.generated_utc,
            "manifest_sha256": self.manifest_sha256,
            "model_campaigns": [campaign.to_dict() for campaign in self.model_campaigns],
            "source_evidence": [
                {"label": label, "sha256": sha256} for label, sha256 in self.source_evidence
            ],
            "status": self.status,
            "task_id": self.task_id,
            "total_batches": self.total_batches,
            "total_targets": self.total_targets,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P05 Batch Partition Manifest",
            "",
            "## Verdict",
            "",
            f"- Task: `{self.task_id}`",
            f"- Status: `{self.status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- Batch size: `{self.batch_size}`",
            f"- Total targets: `{self.total_targets}`",
            f"- Total batches: `{self.total_batches}`",
            "",
            "## Model Campaigns",
        ]
        for campaign in self.model_campaigns:
            lines.append(
                f"- {campaign.model_slot}: targets={campaign.target_count}, batches={campaign.batch_count}, "
                f"workloads={len(campaign.workload_partitions)}"
            )
            for workload in campaign.workload_partitions:
                lines.append(
                    f"  - {workload.workload}: targets={workload.target_count}, batches={workload.batch_count}"
                )
        lines.extend(["", "## Source Evidence"])
        for label, sha256 in self.source_evidence:
            lines.append(f"- {label}: `{sha256}`")
        lines.extend(["", "## Manifest Hash", f"- `{self.manifest_sha256}`"])
        return "\n".join(lines)

    def write(self, manifest_path: Path, markdown_path: Path | None = None) -> None:
        json_text = self.to_json()
        _write_if_unchanged(manifest_path, json_text + "\n")
        if markdown_path is not None:
            _write_if_unchanged(markdown_path, self.to_markdown() + "\n")


def _batch_scope_digest(scope: Mapping[str, object]) -> str:
    return _sha256_bytes(_canonical_json(scope).encode("utf-8"))


def build_batch_slice(
    *,
    dataset_version: str,
    model_slot: str,
    workload: str,
    batch_index: int,
    start_ordinal: int,
    end_ordinal: int,
) -> BatchSlice:
    if workload not in WORKLOAD_BATCH_SCOPES:
        raise MissingFrozenSettingError(f"unknown workload for batch partitioning: {workload!r}")
    if start_ordinal < 1 or end_ordinal < start_ordinal:
        raise SchemaInvariantError("batch ordinals must be positive and monotonically increasing")

    row_count = end_ordinal - start_ordinal + 1
    batch_scope = {
        "batch_index": batch_index,
        "dataset_version": dataset_version,
        "defense_scope": WORKLOAD_BATCH_SCOPES[workload]["defense_scope"],
        "density_scope": WORKLOAD_BATCH_SCOPES[workload]["density_scope"],
        "end_ordinal": end_ordinal,
        "model_slot": model_slot,
        "row_count": row_count,
        "slice_token": f"{batch_index:04X}"[-4:],
        "start_ordinal": start_ordinal,
        "surface_scope": WORKLOAD_BATCH_SCOPES[workload]["surface_scope"],
        "workload": workload,
    }
    digest = _batch_scope_digest(batch_scope)
    run_token = digest[:8].upper()
    slice_token = digest[8:12].upper()
    batch_artifact_id = f"P5ART-{digest[:16].upper()}-batch"
    return BatchSlice(
        dataset_version=dataset_version,
        model_slot=model_slot,
        workload=workload,
        batch_index=batch_index,
        start_ordinal=start_ordinal,
        end_ordinal=end_ordinal,
        row_count=row_count,
        density_scope=WORKLOAD_BATCH_SCOPES[workload]["density_scope"],
        surface_scope=WORKLOAD_BATCH_SCOPES[workload]["surface_scope"],
        defense_scope=WORKLOAD_BATCH_SCOPES[workload]["defense_scope"],
        run_token=run_token,
        slice_token=slice_token,
        batch_artifact_id=batch_artifact_id,
        scope_digest=digest,
    )


def partition_contiguous_ranges(
    *,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    model_slot: str,
    workload: str,
    target_count: int,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> WorkloadPartition:
    if batch_size <= 0:
        raise SchemaInvariantError("batch size must be positive")
    if target_count <= 0:
        raise MissingFrozenSettingError(f"workload target count must be positive for {workload!r}")
    if workload not in WORKLOAD_BATCH_SCOPES:
        raise MissingFrozenSettingError(f"unknown workload for batch partitioning: {workload!r}")

    batches: list[BatchSlice] = []
    start = 1
    batch_index = 1
    while start <= target_count:
        end = min(start + batch_size - 1, target_count)
        batches.append(
            build_batch_slice(
                dataset_version=dataset_version,
                model_slot=model_slot,
                workload=workload,
                batch_index=batch_index,
                start_ordinal=start,
                end_ordinal=end,
            )
        )
        batch_index += 1
        start = end + 1

    return WorkloadPartition(workload=workload, target_count=target_count, batches=tuple(batches))


def build_default_batch_partition_manifest(
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    source_evidence: Sequence[tuple[str, str]] = (),
    generated_utc: str | None = None,
) -> BatchPartitionManifest:
    if batch_size != DEFAULT_BATCH_SIZE:
        raise SchemaInvariantError(
            f"frozen operational batch size mismatch: expected {DEFAULT_BATCH_SIZE}, got {batch_size}"
        )

    generated_utc = generated_utc or datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")
    campaigns: list[ModelCampaignPartition] = []
    for model_slot in MODEL_SLOTS:
        workload_partitions = tuple(
            partition_contiguous_ranges(
                dataset_version=dataset_version,
                model_slot=model_slot,
                workload=workload,
                target_count=target_count,
                batch_size=batch_size,
            )
            for workload, target_count in WORKLOAD_TARGET_COUNTS.items()
        )
        campaigns.append(
            ModelCampaignPartition(
                model_slot=model_slot,
                target_count=sum(WORKLOAD_TARGET_COUNTS.values()),
                workload_partitions=workload_partitions,
            )
        )

    manifest = BatchPartitionManifest(
        task_id="P05",
        status="PASS",
        generated_utc=generated_utc,
        dataset_version=dataset_version,
        batch_size=batch_size,
        total_targets=sum(WORKLOAD_TARGET_COUNTS.values()) * len(MODEL_SLOTS),
        model_campaigns=tuple(campaigns),
        source_evidence=tuple(source_evidence),
        manifest_sha256="",
    )
    manifest_json = json.dumps(
        {
            "batch_size": manifest.batch_size,
            "dataset_version": manifest.dataset_version,
            "generated_utc": manifest.generated_utc,
            "model_campaigns": [campaign.to_dict() for campaign in manifest.model_campaigns],
            "source_evidence": [
                {"label": label, "sha256": sha256} for label, sha256 in manifest.source_evidence
            ],
            "status": manifest.status,
            "task_id": manifest.task_id,
            "total_batches": manifest.total_batches,
            "total_targets": manifest.total_targets,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    manifest_sha256 = _sha256_bytes(manifest_json.encode("utf-8"))
    return BatchPartitionManifest(
        task_id=manifest.task_id,
        status=manifest.status,
        generated_utc=manifest.generated_utc,
        dataset_version=manifest.dataset_version,
        batch_size=manifest.batch_size,
        total_targets=manifest.total_targets,
        model_campaigns=manifest.model_campaigns,
        source_evidence=manifest.source_evidence,
        manifest_sha256=manifest_sha256,
    )


def freeze_batch_partition_manifest(
    manifest_path: Path,
    *,
    markdown_path: Path | None = None,
    batch_size: int = DEFAULT_BATCH_SIZE,
    dataset_version: str = DEFAULT_DATASET_VERSION,
    source_evidence: Sequence[tuple[str, str]] = (),
    generated_utc: str | None = None,
) -> BatchPartitionManifest:
    manifest = build_default_batch_partition_manifest(
        batch_size=batch_size,
        dataset_version=dataset_version,
        source_evidence=source_evidence,
        generated_utc=generated_utc,
    )
    manifest.write(manifest_path, markdown_path)
    return manifest
