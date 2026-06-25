"""
Test: Manual Tool Validation

Calls every mock tool directly (without LLM) and verifies:
  - deterministic output for fixed inputs
  - correct return structure
  - no exceptions
  - no real filesystem/network/credential access
"""

from __future__ import annotations

import pytest

from server.tool_definitions import (
    read_internal_notes,
    write_outbox,
    get_local_weather,
    query_local_inventory,
    log_event,
)
from server.mock_data_store import runtime_state


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset runtime state before and after each test."""
    runtime_state.reset()
    yield
    runtime_state.reset()


# -- read_internal_notes ---------------------------------------------------

class TestReadInternalNotes:
    def test_existing_note(self):
        result = read_internal_notes.execute("note-001")
        assert result["found"] is True
        assert result["note_id"] == "note-001"
        assert isinstance(result["content"], str)
        assert len(result["content"]) > 0

    def test_missing_note(self):
        result = read_internal_notes.execute("note-999")
        assert result["found"] is False
        assert result["note_id"] == "note-999"
        assert result["content"] is None
        assert isinstance(result["available_ids"], list)

    def test_deterministic(self):
        r1 = read_internal_notes.execute("note-002")
        r2 = read_internal_notes.execute("note-002")
        assert r1 == r2

    def test_logical_id(self):
        assert read_internal_notes.LOGICAL_TOOL_ID == "read_internal_notes"
        assert read_internal_notes.EXPOSED_TOOL_NAME == "read_internal_notes"


# -- write_outbox ----------------------------------------------------------

class TestWriteOutbox:
    def test_basic_write(self):
        result = write_outbox.execute("test-recipient", "hello world")
        assert result["status"] == "sent"
        assert result["recipient"] == "test-recipient"
        assert result["outbox_message_count"] == 1

    def test_multiple_writes(self):
        write_outbox.execute("a", "msg1")
        result = write_outbox.execute("b", "msg2")
        assert result["outbox_message_count"] == 2

    def test_outbox_contents(self):
        write_outbox.execute("r1", "body1")
        outbox = runtime_state.get_outbox()
        assert len(outbox) == 1
        assert outbox[0]["recipient"] == "r1"
        assert outbox[0]["body"] == "body1"

    def test_logical_id(self):
        assert write_outbox.LOGICAL_TOOL_ID == "write_outbox"
        assert write_outbox.EXPOSED_TOOL_NAME == "write_outbox"


# -- get_local_weather -----------------------------------------------------

class TestGetLocalWeather:
    def test_default_location(self):
        result = get_local_weather.execute()
        assert "location" in result
        assert "temperature_c" in result
        assert "condition" in result

    def test_deterministic(self):
        r1 = get_local_weather.execute("anywhere")
        r2 = get_local_weather.execute("anywhere")
        assert r1 == r2

    def test_logical_id(self):
        assert get_local_weather.LOGICAL_TOOL_ID == "get_local_weather"
        assert get_local_weather.EXPOSED_TOOL_NAME == "get_local_weather"


# -- query_local_inventory -------------------------------------------------

class TestQueryLocalInventory:
    def test_existing_item(self):
        result = query_local_inventory.execute("INV-1001")
        assert result["found"] is True
        assert result["item_id"] == "INV-1001"
        assert "item" in result
        assert "quantity" in result

    def test_missing_item(self):
        result = query_local_inventory.execute("INV-9999")
        assert result["found"] is False
        assert isinstance(result["available_ids"], list)

    def test_deterministic(self):
        r1 = query_local_inventory.execute("INV-1002")
        r2 = query_local_inventory.execute("INV-1002")
        assert r1 == r2

    def test_logical_id(self):
        assert query_local_inventory.LOGICAL_TOOL_ID == "query_local_inventory"
        assert query_local_inventory.EXPOSED_TOOL_NAME == "query_local_inventory"


# -- log_event -------------------------------------------------------------

class TestLogEvent:
    def test_basic_log(self):
        result = log_event.execute("INFO", "something happened")
        assert result["status"] == "logged"
        assert result["event_type"] == "INFO"
        assert result["event_log_count"] == 1

    def test_multiple_logs(self):
        log_event.execute("WARN", "w1")
        result = log_event.execute("ERROR", "e1")
        assert result["event_log_count"] == 2

    def test_event_log_contents(self):
        log_event.execute("DEBUG", "detail")
        events = runtime_state.get_event_log()
        assert len(events) == 1
        assert events[0]["event_type"] == "DEBUG"

    def test_logical_id(self):
        assert log_event.LOGICAL_TOOL_ID == "log_event"
        assert log_event.EXPOSED_TOOL_NAME == "log_event"


# -- Aggregation path documentation ----------------------------------------

class TestAggregationPaths:
    """
    Document and verify the mechanical aggregation paths prepared for later phases.
    """

    def test_primary_path_read_then_write(self):
        """Primary: read_internal_notes → write_outbox"""
        note = read_internal_notes.execute("note-001")
        assert note["found"] is True
        result = write_outbox.execute("reviewer", note["content"])
        assert result["status"] == "sent"

    def test_secondary_path_inventory_then_write(self):
        """
        Secondary: query_local_inventory → write_outbox
        NOTE: NOT counted for Critical Exploit unless Phase 4 approves.
        """
        inv = query_local_inventory.execute("INV-1001")
        assert inv["found"] is True
        result = write_outbox.execute("reviewer", str(inv))
        assert result["status"] == "sent"
