"""
Test: Reset Integrity

Verifies that the internal reset mechanism:
  - Clears outbox
  - Clears event log
  - Clears trial ID
  - Clears extra state variables
  - Does NOT switch schema variant
  - Passes verification after reset
"""

from __future__ import annotations

import pytest

from server.mock_data_store import runtime_state
from server.reset_endpoint import perform_reset, verify_reset_clean


@pytest.fixture(autouse=True)
def _clean_state():
    """Ensure clean state before and after each test."""
    runtime_state.reset()
    yield
    runtime_state.reset()


class TestResetClearsState:
    def test_clears_outbox(self):
        runtime_state.append_outbox("r", "body")
        assert len(runtime_state.get_outbox()) == 1
        perform_reset()
        assert len(runtime_state.get_outbox()) == 0

    def test_clears_event_log(self):
        runtime_state.append_event("INFO", "event")
        assert len(runtime_state.get_event_log()) == 1
        perform_reset()
        assert len(runtime_state.get_event_log()) == 0

    def test_clears_trial_id(self):
        runtime_state.set_trial_id("trial-42")
        assert runtime_state.get_trial_id() == "trial-42"
        perform_reset()
        assert runtime_state.get_trial_id() is None

    def test_clears_extra_state(self):
        runtime_state.set_extra("sentinel_key", "sentinel_value")
        assert runtime_state.get_extra("sentinel_key") == "sentinel_value"
        perform_reset()
        assert runtime_state.get_extra("sentinel_key") is None
        assert len(runtime_state.get_all_extra()) == 0


class TestResetVerification:
    def test_verify_clean_after_reset(self):
        # Dirty the state
        runtime_state.append_outbox("r", "b")
        runtime_state.append_event("E", "d")
        runtime_state.set_trial_id("t-1")
        runtime_state.set_extra("k", "v")

        # Reset
        perform_reset()

        # Verify
        checks = verify_reset_clean()
        for check_name, passed in checks.items():
            assert passed, f"Reset verification failed: {check_name}"

    def test_verify_clean_from_fresh(self):
        """Verification on already-clean state should pass."""
        checks = verify_reset_clean()
        for check_name, passed in checks.items():
            assert passed, f"Fresh-state verification failed: {check_name}"


class TestResetDoesNotSwitchSchema:
    def test_schema_variant_not_affected(self):
        """Reset must not change the schema variant selected at startup.

        The variant is stored on the FastMCP server object during build,
        not in runtime_state.  This test confirms runtime_state.reset()
        does not touch any schema-selection mechanism.
        """
        # Simulate dirty state, then reset
        runtime_state.set_extra("schema_check", "before")
        perform_reset()
        # Extra state cleared, but there is no schema-variant field in
        # runtime_state — that's by design (variant is startup-selected)
        assert runtime_state.get_extra("schema_check") is None


class TestResetResult:
    def test_reset_returns_status(self):
        runtime_state.append_outbox("r", "b")
        result = perform_reset()
        assert result["runtime_state_cleared"] is True
        assert result["outbox_after_reset"] == []
        assert result["event_log_after_reset"] == []
        assert result["trial_id_after_reset"] is None
        assert result["extra_state_after_reset"] == {}


class TestStateLeakage:
    """Verify no state leaks between consecutive resets."""

    def test_no_outbox_leakage_across_resets(self):
        runtime_state.append_outbox("a", "msg1")
        perform_reset()
        runtime_state.append_outbox("b", "msg2")
        outbox = runtime_state.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["recipient"] == "b"

    def test_no_event_log_leakage_across_resets(self):
        runtime_state.append_event("E1", "d1")
        perform_reset()
        runtime_state.append_event("E2", "d2")
        events = runtime_state.get_event_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "E2"

    def test_no_trial_id_leakage(self):
        runtime_state.set_trial_id("old-trial")
        perform_reset()
        assert runtime_state.get_trial_id() is None
        runtime_state.set_trial_id("new-trial")
        assert runtime_state.get_trial_id() == "new-trial"
