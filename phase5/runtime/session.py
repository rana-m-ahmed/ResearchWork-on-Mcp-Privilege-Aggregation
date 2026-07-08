"""Operational campaign session helpers for Phase 5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..domain.errors import IdentifierValidationError, MissingFrozenSettingError, SessionTransitionError
from ..domain.enums import ModelSlot, SessionState
from ..domain.identifiers import RunId
from ..domain.session import Phase5Session


def _canonical_json(data: Mapping[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalise_run_id(value: str | None, *, model_slot: ModelSlot, batch_id: str | None, utcdate: str | None) -> str:
    if value is not None:
        return str(RunId.parse(value))
    if utcdate is None:
        utcdate = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    seed = "|".join(
        (
            model_slot.value,
            batch_id or "",
            utcdate,
        )
    )
    session_token = _sha256_text(seed)[:8].upper()
    return str(RunId.build("P5-DV-1.0.0-A7C91E42", model_slot, utcdate, session_token))


@dataclass(frozen=True, slots=True)
class CampaignSession:
    """A fail-closed operational wrapper around the frozen Phase 5 session state."""

    run_id: str
    model_slot: ModelSlot
    phase5_session: Phase5Session
    batch_id: str | None = None
    seal_epoch_hashes: tuple[str, ...] = ()
    processed_batch_ids: tuple[str, ...] = ()
    accepted_finalized_count: int = 0
    finalized_batch_count: int = 0
    invalid_attempt_count: int = 0
    orphan_attempt_count: int = 0
    checkpoint_sync_status: str = "NOT_SYNCED"
    time_to_safety_horizon_seconds: float | None = None
    batch_manifest_sha256: str | None = None
    run_plan_sha256: str | None = None
    local_commit_sha: str | None = None
    remote_commit_sha: str | None = None
    last_barrier_reason: str | None = None
    max_observed_token_count: int | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not self.run_id:
            raise MissingFrozenSettingError("run_id is required for an operational campaign session")
        RunId.parse(self.run_id)
        if not isinstance(self.model_slot, ModelSlot):
            raise IdentifierValidationError("model_slot must be one of the frozen model slots")
        if self.batch_id is not None and (not isinstance(self.batch_id, str) or not self.batch_id):
            raise IdentifierValidationError("batch_id must be a non-empty string or null")
        if not isinstance(self.phase5_session, Phase5Session):
            raise SessionTransitionError("phase5_session must be a frozen Phase 5 session state")
        if self.accepted_finalized_count < 0:
            raise IdentifierValidationError("accepted_finalized_count must be non-negative")
        if self.finalized_batch_count < 0:
            raise IdentifierValidationError("finalized_batch_count must be non-negative")
        if self.invalid_attempt_count < 0:
            raise IdentifierValidationError("invalid_attempt_count must be non-negative")
        if self.orphan_attempt_count < 0:
            raise IdentifierValidationError("orphan_attempt_count must be non-negative")
        if self.time_to_safety_horizon_seconds is not None and self.time_to_safety_horizon_seconds < 0:
            raise IdentifierValidationError("time_to_safety_horizon_seconds must be non-negative")
        if self.max_observed_token_count is not None and self.max_observed_token_count < 0:
            raise IdentifierValidationError("max_observed_token_count must be non-negative")

    @property
    def seal_epoch(self) -> int:
        return self.phase5_session.seal_epoch

    @property
    def state(self) -> SessionState:
        return self.phase5_session.state

    @classmethod
    def open(
        cls,
        *,
        model_slot: ModelSlot | str,
        batch_id: object | None = None,
        run_id: str | None = None,
        utcdate: str | None = None,
        phase5_session: Phase5Session | None = None,
        batch_manifest_sha256: str | None = None,
        run_plan_sha256: str | None = None,
        time_to_safety_horizon_seconds: float | None = None,
    ) -> "CampaignSession":
        model_value = model_slot if isinstance(model_slot, ModelSlot) else ModelSlot.from_value(model_slot)
        batch_value = None if batch_id is None else str(getattr(batch_id, "value", batch_id))
        if batch_value == "":
            raise MissingFrozenSettingError("batch_id is required for an operational campaign session")
        campaign_run_id = _normalise_run_id(run_id, model_slot=model_value, batch_id=batch_value, utcdate=utcdate)
        return cls(
            run_id=campaign_run_id,
            model_slot=model_value,
            batch_id=batch_value,
            phase5_session=phase5_session or Phase5Session.initial(),
            batch_manifest_sha256=batch_manifest_sha256,
            run_plan_sha256=run_plan_sha256,
            time_to_safety_horizon_seconds=time_to_safety_horizon_seconds,
        )

    def _with_session(self, session: Phase5Session, **changes: Any) -> "CampaignSession":
        seal_epoch_hashes = tuple(changes.pop("seal_epoch_hashes", self.seal_epoch_hashes))
        return replace(self, phase5_session=session, seal_epoch_hashes=seal_epoch_hashes, **changes)

    def seal(self, *, git_write_credential_present: bool = False) -> "CampaignSession":
        return self._with_session(self.phase5_session.seal(git_write_credential_present=git_write_credential_present))

    def close_after_finalization(self) -> "CampaignSession":
        return self._with_session(self.phase5_session.close_after_finalization())

    def begin_sync(self, *, trial_process_running: bool = False) -> "CampaignSession":
        return self._with_session(self.phase5_session.begin_sync(trial_process_running=trial_process_running))

    def finish_sync(self) -> "CampaignSession":
        return self._with_session(self.phase5_session.finish_sync())

    def reverify_after_sync(self, *, hashes_match: bool) -> "CampaignSession":
        return self._with_session(
            self.phase5_session.reverify_after_sync(hashes_match=hashes_match),
            checkpoint_sync_status="REVERIFIED_AFTER_SYNC",
        )

    def record_batch(
        self,
        *,
        batch_id: object,
        accepted_count: int,
        finalized: bool = True,
        estimated_seconds: float | None = None,
        max_observed_token_count: int | None = None,
    ) -> "CampaignSession":
        batch_value = str(getattr(batch_id, "value", batch_id))
        if not batch_value:
            raise MissingFrozenSettingError("batch_id is required when recording a campaign batch")
        if accepted_count < 0:
            raise IdentifierValidationError("accepted_count must be non-negative")
        if estimated_seconds is not None and estimated_seconds < 0:
            raise IdentifierValidationError("estimated_seconds must be non-negative")
        if max_observed_token_count is not None and max_observed_token_count < 0:
            raise IdentifierValidationError("max_observed_token_count must be non-negative")
        batch_ids = self.processed_batch_ids
        if batch_value in batch_ids:
            raise MissingFrozenSettingError(f"duplicate batch processed in campaign session: {batch_value}")
        updated = replace(
            self,
            processed_batch_ids=batch_ids + (batch_value,),
            accepted_finalized_count=self.accepted_finalized_count + accepted_count,
            finalized_batch_count=self.finalized_batch_count + (1 if finalized else 0),
            max_observed_token_count=max(
                [value for value in (self.max_observed_token_count, max_observed_token_count) if value is not None],
                default=None,
            ),
        )
        if estimated_seconds is not None:
            updated = replace(
                updated,
                time_to_safety_horizon_seconds=(
                    None
                    if self.time_to_safety_horizon_seconds is None
                    else max(0.0, self.time_to_safety_horizon_seconds - estimated_seconds)
                ),
            )
        return updated

    def mark_barrier(
        self,
        *,
        reason: str,
        seal_epoch_hash: str,
        checkpoint_sync_status: str,
        local_commit_sha: str | None = None,
        remote_commit_sha: str | None = None,
    ) -> "CampaignSession":
        if not reason:
            raise MissingFrozenSettingError("barrier reason is required")
        if not seal_epoch_hash:
            raise MissingFrozenSettingError("seal epoch hash is required")
        return replace(
            self,
            last_barrier_reason=reason,
            seal_epoch_hashes=self.seal_epoch_hashes + (seal_epoch_hash,),
            checkpoint_sync_status=checkpoint_sync_status,
            local_commit_sha=local_commit_sha if local_commit_sha is not None else self.local_commit_sha,
            remote_commit_sha=remote_commit_sha if remote_commit_sha is not None else self.remote_commit_sha,
        )

    def dashboard_mapping(self) -> dict[str, Any]:
        return {
            "accepted_finalized_count": self.accepted_finalized_count,
            "batch_id": self.batch_id,
            "checkpoint_sync_status": self.checkpoint_sync_status,
            "finalized_batch_count": self.finalized_batch_count,
            "invalid_attempt_count": self.invalid_attempt_count,
            "last_barrier_reason": self.last_barrier_reason,
            "local_commit_sha": self.local_commit_sha,
            "max_observed_token_count": self.max_observed_token_count,
            "model_slot": self.model_slot.value,
            "orphan_attempt_count": self.orphan_attempt_count,
            "pending_batch_count": None,
            "processed_batch_ids": list(self.processed_batch_ids),
            "run_id": self.run_id,
            "run_plan_sha256": self.run_plan_sha256,
            "seal_epoch": self.seal_epoch,
            "seal_epoch_hashes": list(self.seal_epoch_hashes),
            "state": self.state.value,
            "time_to_safety_horizon_seconds": self.time_to_safety_horizon_seconds,
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "remote_commit_sha": self.remote_commit_sha,
        }

    def to_mapping(self) -> dict[str, Any]:
        return {
            "accepted_finalized_count": self.accepted_finalized_count,
            "batch_id": self.batch_id,
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "checkpoint_sync_status": self.checkpoint_sync_status,
            "finalized_batch_count": self.finalized_batch_count,
            "invalid_attempt_count": self.invalid_attempt_count,
            "last_barrier_reason": self.last_barrier_reason,
            "local_commit_sha": self.local_commit_sha,
            "max_observed_token_count": self.max_observed_token_count,
            "model_slot": self.model_slot.value,
            "orphan_attempt_count": self.orphan_attempt_count,
            "processed_batch_ids": list(self.processed_batch_ids),
            "remote_commit_sha": self.remote_commit_sha,
            "run_id": self.run_id,
            "run_plan_sha256": self.run_plan_sha256,
            "seal_epoch": self.seal_epoch,
            "seal_epoch_hashes": list(self.seal_epoch_hashes),
            "state": self.state.value,
            "time_to_safety_horizon_seconds": self.time_to_safety_horizon_seconds,
        }

    def to_markdown(self) -> str:
        lines = [
            "# P14 Campaign Session",
            "",
            f"- Run ID: `{self.run_id}`",
            f"- Model slot: `{self.model_slot.value}`",
            f"- Session state: `{self.state.value}`",
            f"- Seal epoch: `{self.seal_epoch}`",
            f"- Accepted finalized count: `{self.accepted_finalized_count}`",
            f"- Finalized batch count: `{self.finalized_batch_count}`",
            f"- Invalid attempts: `{self.invalid_attempt_count}`",
            f"- Orphan attempts: `{self.orphan_attempt_count}`",
            f"- Checkpoint sync status: `{self.checkpoint_sync_status}`",
            f"- Time to safety horizon: `{self.time_to_safety_horizon_seconds}`",
            f"- Batch manifest hash: `{self.batch_manifest_sha256}`",
            f"- Run plan hash: `{self.run_plan_sha256}`",
        ]
        if self.batch_id is not None:
            lines.append(f"- Batch ID: `{self.batch_id}`")
        if self.processed_batch_ids:
            lines.extend(["", "## Processed Batches"])
            lines.extend(f"- `{batch_id}`" for batch_id in self.processed_batch_ids)
        if self.seal_epoch_hashes:
            lines.extend(["", "## Seal Epoch Hashes"])
            lines.extend(f"- `{seal_hash}`" for seal_hash in self.seal_epoch_hashes)
        return "\n".join(lines) + "\n"
