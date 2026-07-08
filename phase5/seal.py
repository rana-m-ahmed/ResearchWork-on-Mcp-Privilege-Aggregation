"""Seal-epoch barrier helpers for the Phase 5 campaign controller."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from .domain.errors import MissingFrozenSettingError, SessionTransitionError
from .domain.enums import SessionState
from .runtime.session import CampaignSession


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class BarrierDecision:
    """A frozen decision about whether the campaign should sync or stop."""

    should_sync: bool
    should_stop: bool
    reason: str
    remaining_seconds: float
    sync_margin_seconds: float

    def to_mapping(self) -> dict[str, Any]:
        return {
            "reason": self.reason,
            "remaining_seconds": self.remaining_seconds,
            "should_stop": self.should_stop,
            "should_sync": self.should_sync,
            "sync_margin_seconds": self.sync_margin_seconds,
        }


@dataclass(frozen=True, slots=True)
class CampaignBarrierController:
    """Fail-closed safety-horizon controller for long-running Phase 5 campaigns."""

    safe_session_seconds: float
    checkpoint_barrier_interval_trials: int
    p95_trial_seconds: float
    load_overhead_seconds: float = 0.0

    def __post_init__(self) -> None:
        if self.safe_session_seconds <= 0:
            raise MissingFrozenSettingError("safe_session_seconds must be positive")
        if self.checkpoint_barrier_interval_trials <= 0:
            raise MissingFrozenSettingError("checkpoint_barrier_interval_trials must be positive")
        if self.p95_trial_seconds <= 0:
            raise MissingFrozenSettingError("p95_trial_seconds must be positive")
        if self.load_overhead_seconds < 0:
            raise MissingFrozenSettingError("load_overhead_seconds must be non-negative")

    @property
    def sync_margin_seconds(self) -> float:
        return float(self.checkpoint_barrier_interval_trials * self.p95_trial_seconds)

    def batch_estimate_seconds(self, row_count: int) -> float:
        if row_count <= 0:
            raise MissingFrozenSettingError("row_count must be positive")
        return float(row_count * self.p95_trial_seconds)

    def remaining_seconds(self, elapsed_seconds: float) -> float:
        return max(0.0, self.safe_session_seconds - elapsed_seconds)

    def should_stop_before_batch(self, *, elapsed_seconds: float, next_batch_row_count: int) -> bool:
        estimated = self.batch_estimate_seconds(next_batch_row_count)
        return elapsed_seconds + estimated + self.sync_margin_seconds > self.safe_session_seconds

    def decide(
        self,
        *,
        elapsed_seconds: float,
        accepted_count: int,
        finalized_batch_count: int,
    ) -> BarrierDecision:
        remaining = self.remaining_seconds(elapsed_seconds)
        should_sync = (
            accepted_count >= self.checkpoint_barrier_interval_trials
            or finalized_batch_count >= self.checkpoint_barrier_interval_trials
            or remaining <= self.sync_margin_seconds
        )
        should_stop = remaining <= self.sync_margin_seconds
        if should_stop and not should_sync:
            should_sync = True
        reasons: list[str] = []
        if accepted_count >= self.checkpoint_barrier_interval_trials:
            reasons.append("accepted-count-threshold")
        if finalized_batch_count >= self.checkpoint_barrier_interval_trials:
            reasons.append("batch-count-threshold")
        if remaining <= self.sync_margin_seconds:
            reasons.append("time-threshold")
        if not reasons:
            reasons.append("continue")
        return BarrierDecision(
            should_sync=should_sync,
            should_stop=should_stop,
            reason="+".join(reasons),
            remaining_seconds=remaining,
            sync_margin_seconds=self.sync_margin_seconds,
        )


@dataclass(frozen=True, slots=True)
class SealEpochRecord:
    """Hash-bound record of a seal/barrier transition."""

    seal_epoch: int
    reason: str
    before_state: str
    after_state: str
    batch_ids: tuple[str, ...]
    accepted_count: int
    finalized_batch_count: int
    elapsed_seconds: float
    credential_purged: bool
    hashes_verified: bool
    resealed: bool

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_count": self.accepted_count,
            "after_state": self.after_state,
            "before_state": self.before_state,
            "batch_ids": list(self.batch_ids),
            "credential_purged": self.credential_purged,
            "elapsed_seconds": self.elapsed_seconds,
            "finalized_batch_count": self.finalized_batch_count,
            "hashes_verified": self.hashes_verified,
            "reason": self.reason,
            "resealed": self.resealed,
            "seal_epoch": self.seal_epoch,
        }

    @property
    def record_hash(self) -> str:
        return _sha256_text(json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":")))

    def to_digest_mapping(self) -> dict[str, Any]:
        return {**self.to_mapping(), "record_hash": self.record_hash}


def perform_sync_barrier(
    session: CampaignSession,
    *,
    reason: str,
    hashes_match: bool = True,
    credential_purged: bool = True,
    reseal: bool = True,
    elapsed_seconds: float | None = None,
) -> tuple[CampaignSession, SealEpochRecord]:
    """Advance a campaign through the frozen close/sync/reverify/reseal sequence."""

    if session.state is not SessionState.SEALED:
        raise SessionTransitionError(f"sync barrier requires SEALED, not {session.state.value}")
    closed = session.close_after_finalization()
    syncing = closed.begin_sync(trial_process_running=False)
    synced = syncing.finish_sync()
    reverified = synced.reverify_after_sync(hashes_match=hashes_match)
    final_session = reverified.seal() if reseal else reverified
    record = SealEpochRecord(
        seal_epoch=final_session.seal_epoch,
        reason=reason,
        before_state=session.state.value,
        after_state=final_session.state.value,
        batch_ids=final_session.processed_batch_ids,
        accepted_count=final_session.accepted_finalized_count,
        finalized_batch_count=final_session.finalized_batch_count,
        elapsed_seconds=elapsed_seconds if elapsed_seconds is not None else (session.time_to_safety_horizon_seconds or 0.0),
        credential_purged=credential_purged,
        hashes_verified=hashes_match,
        resealed=reseal,
    )
    return final_session.mark_barrier(
        reason=reason,
        seal_epoch_hash=record.record_hash,
        checkpoint_sync_status=final_session.state.value,
    ), record
