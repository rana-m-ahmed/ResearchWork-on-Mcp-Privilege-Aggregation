"""Frozen queue adapters for Phase 5."""

from __future__ import annotations

from .batch_partitioner import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_DATASET_VERSION,
    BatchPartitionManifest,
    BatchSlice,
    ModelCampaignPartition,
    WorkloadPartition,
    build_default_batch_partition_manifest,
    freeze_batch_partition_manifest,
    partition_contiguous_ranges,
)
from .frozen_queue_loader import (
    FROZEN_QUEUE_HEADER,
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
from .pending_resolver import (
    CheckpointHistory,
    OrphanRegistryEntry,
    PendingResolution,
    ResolvedTarget,
    resolve_pending_targets,
)

__all__ = [
    "BatchPartitionManifest",
    "BatchSlice",
    "CheckpointHistory",
    "DEFAULT_BATCH_SIZE",
    "DEFAULT_DATASET_VERSION",
    "FROZEN_QUEUE_HEADER",
    "FrozenQueue",
    "FrozenQueueBundle",
    "FrozenQueueLoadReport",
    "FrozenQueueRow",
    "ModelCampaignPartition",
    "OrphanRegistryEntry",
    "PendingResolution",
    "ResolvedTarget",
    "WorkloadPartition",
    "build_default_batch_partition_manifest",
    "freeze_batch_partition_manifest",
    "load_core_queue",
    "load_defense_queue",
    "load_frozen_queue_bundle",
    "load_utility_queue",
    "partition_contiguous_ranges",
    "resolve_pending_targets",
    "validate_frozen_queue_bundle",
]
