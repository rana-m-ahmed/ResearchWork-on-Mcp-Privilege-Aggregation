from __future__ import annotations

import pytest

from phase5.domain import Phase5Session, SessionState
from phase5.domain.errors import FrozenArtifactHashError, SessionTransitionError, SyncSafetyError


def test_session_state_machine_supports_multiple_seal_epochs() -> None:
    session = Phase5Session.initial()
    assert session.state is SessionState.PREPARATION
    with pytest.raises(SessionTransitionError):
        session.require_can_run_batch()

    sealed = session.seal()
    assert sealed.state is SessionState.SEALED
    assert sealed.seal_epoch == 1
    assert sealed.can_run_batch() is True

    closed = sealed.close_after_finalization()
    assert closed.state is SessionState.CLOSED_AFTER_FINALIZATION
    with pytest.raises(SessionTransitionError):
        closed.require_can_run_batch()

    syncing = closed.begin_sync()
    assert syncing.state is SessionState.UNSEALED_SYNCING
    with pytest.raises(SessionTransitionError):
        syncing.require_can_run_batch()

    synced = syncing.finish_sync()
    assert synced.state is SessionState.UNSEALED_SYNCED
    assert synced.sync_epoch == 1
    with pytest.raises(SessionTransitionError):
        synced.require_can_run_batch()

    reverified = synced.reverify_after_sync(hashes_match=True)
    assert reverified.state is SessionState.REVERIFIED_AFTER_SYNC

    resealed = reverified.seal()
    assert resealed.state is SessionState.SEALED
    assert resealed.seal_epoch == 2


def test_session_transitions_fail_closed_out_of_order() -> None:
    session = Phase5Session.initial()

    with pytest.raises(SessionTransitionError):
        session.close_after_finalization()
    with pytest.raises(SessionTransitionError):
        session.begin_sync()
    with pytest.raises(SessionTransitionError):
        session.finish_sync()
    with pytest.raises(SessionTransitionError):
        session.reverify_after_sync(hashes_match=True)

    with pytest.raises(SyncSafetyError):
        session.seal(git_write_credential_present=True)

    sealed = session.seal()
    with pytest.raises(SyncSafetyError):
        sealed.begin_sync(trial_process_running=True)

    synced = sealed.close_after_finalization().begin_sync().finish_sync()
    with pytest.raises(FrozenArtifactHashError):
        synced.reverify_after_sync(hashes_match=False)
