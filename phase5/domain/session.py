"""Session state machine and sync guards for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .errors import FrozenArtifactHashError, SessionTransitionError, SyncSafetyError
from .enums import SessionState


@dataclass(frozen=True, slots=True)
class Phase5Session:
    state: SessionState = SessionState.PREPARATION
    seal_epoch: int = 0
    sync_epoch: int = 0

    @classmethod
    def initial(cls) -> "Phase5Session":
        return cls()

    def can_run_batch(self) -> bool:
        return self.state is SessionState.SEALED

    def require_can_run_batch(self) -> None:
        if not self.can_run_batch():
            raise SessionTransitionError(f"run-batch requires SEALED, not {self.state.value}")

    def seal(self, *, git_write_credential_present: bool = False) -> "Phase5Session":
        if git_write_credential_present:
            raise SyncSafetyError("session-seal refuses to run while a Git write credential is present")
        if self.state is SessionState.PREPARATION:
            return replace(self, state=SessionState.SEALED, seal_epoch=self.seal_epoch + 1)
        if self.state is SessionState.REVERIFIED_AFTER_SYNC:
            return replace(self, state=SessionState.SEALED, seal_epoch=self.seal_epoch + 1)
        raise SessionTransitionError(f"session-seal is only allowed from PREPARATION or REVERIFIED_AFTER_SYNC, not {self.state.value}")

    def close_after_finalization(self) -> "Phase5Session":
        if self.state is not SessionState.SEALED:
            raise SessionTransitionError(
                f"close-after-finalization requires SEALED, not {self.state.value}"
            )
        return replace(self, state=SessionState.CLOSED_AFTER_FINALIZATION)

    def begin_sync(self, *, trial_process_running: bool = False) -> "Phase5Session":
        if trial_process_running:
            raise SyncSafetyError("sync-github refuses to run while a trial process is active")
        if self.state is not SessionState.CLOSED_AFTER_FINALIZATION:
            raise SessionTransitionError(
                f"sync-github requires CLOSED_AFTER_FINALIZATION, not {self.state.value}"
            )
        return replace(self, state=SessionState.UNSEALED_SYNCING)

    def finish_sync(self) -> "Phase5Session":
        if self.state is not SessionState.UNSEALED_SYNCING:
            raise SessionTransitionError(
                f"finish-sync requires UNSEALED_SYNCING, not {self.state.value}"
            )
        return replace(self, state=SessionState.UNSEALED_SYNCED, sync_epoch=self.sync_epoch + 1)

    def reverify_after_sync(self, *, hashes_match: bool) -> "Phase5Session":
        if self.state is not SessionState.UNSEALED_SYNCED:
            raise SessionTransitionError(
                f"session-reverify requires UNSEALED_SYNCED, not {self.state.value}"
            )
        if not hashes_match:
            raise FrozenArtifactHashError("session-reverify failed because a source or frozen hash changed")
        return replace(self, state=SessionState.REVERIFIED_AFTER_SYNC)

    def quarantine(self) -> "Phase5Session":
        if self.state is SessionState.TERMINAL:
            return self
        return replace(self, state=SessionState.QUARANTINED)

    def terminate(self) -> "Phase5Session":
        return replace(self, state=SessionState.TERMINAL)
