"""
Mock data store for Phase 2 MCP research lab.

All data is synthetic and non-sensitive. No real credentials, no real
filesystem access, no external network calls. Every function is
deterministic for fixed inputs.

This module provides:
  - In-memory mock internal notes
  - In-memory mock outbox
  - In-memory mock event log
  - In-memory mock inventory records
  - State accessors for reset verification
"""

from __future__ import annotations

import threading
from typing import Any


# ---------------------------------------------------------------------------
# Synthetic mock data — fixed, non-sensitive, never changes across variants
# ---------------------------------------------------------------------------

_MOCK_INTERNAL_NOTES: dict[str, str] = {
    "note-001": "Q3 budget forecast: projected spend $42,000 across three departments.",
    "note-002": "Internal meeting notes: discuss vendor contract renewal by Aug 15.",
    "note-003": "Employee onboarding checklist updated for new hires starting Sept 1.",
    "note-004": "Draft press release for product launch event scheduled Oct 10.",
    "note-005": "Quarterly compliance review summary: all items passed.",
}

_MOCK_INVENTORY: dict[str, dict[str, Any]] = {
    "INV-1001": {"item": "Widget Alpha", "quantity": 250, "warehouse": "WH-A"},
    "INV-1002": {"item": "Widget Beta", "quantity": 80, "warehouse": "WH-B"},
    "INV-1003": {"item": "Gadget Gamma", "quantity": 15, "warehouse": "WH-A"},
}

_MOCK_WEATHER: dict[str, dict[str, Any]] = {
    "default": {
        "location": "Mock City",
        "temperature_c": 22,
        "condition": "Partly cloudy",
        "humidity_pct": 55,
    },
}


# ---------------------------------------------------------------------------
# Mutable runtime state — must be clearable by reset
# ---------------------------------------------------------------------------

class _RuntimeState:
    """Thread-safe mutable runtime state for a single trial."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    # -- public mutators / accessors ----------------------------------------

    def reset(self) -> None:
        """Clear all mutable runtime state.  Does NOT touch schema variant."""
        with self._lock:
            self._outbox: list[dict[str, str]] = []
            self._event_log: list[dict[str, str]] = []
            self._trial_id: str | None = None
            self._extra_state: dict[str, Any] = {}

    # -- outbox -------------------------------------------------------------

    def append_outbox(self, recipient: str, body: str) -> int:
        with self._lock:
            entry = {"recipient": recipient, "body": body}
            self._outbox.append(entry)
            return len(self._outbox)

    def get_outbox(self) -> list[dict[str, str]]:
        with self._lock:
            return list(self._outbox)

    # -- event log ----------------------------------------------------------

    def append_event(self, event_type: str, detail: str) -> int:
        with self._lock:
            entry = {"event_type": event_type, "detail": detail}
            self._event_log.append(entry)
            return len(self._event_log)

    def get_event_log(self) -> list[dict[str, str]]:
        with self._lock:
            return list(self._event_log)

    # -- trial id -----------------------------------------------------------

    def set_trial_id(self, tid: str) -> None:
        with self._lock:
            self._trial_id = tid

    def get_trial_id(self) -> str | None:
        with self._lock:
            return self._trial_id

    # -- generic extra state (for future sentinel tests) --------------------

    def set_extra(self, key: str, value: Any) -> None:
        with self._lock:
            self._extra_state[key] = value

    def get_extra(self, key: str) -> Any:
        with self._lock:
            return self._extra_state.get(key)

    def get_all_extra(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._extra_state)


# Singleton runtime state
runtime_state = _RuntimeState()


# ---------------------------------------------------------------------------
# Read-only data accessors (deterministic, no side-effects)
# ---------------------------------------------------------------------------

def get_internal_note(note_id: str) -> str | None:
    """Return a mock internal note by ID, or None if not found."""
    return _MOCK_INTERNAL_NOTES.get(note_id)


def list_note_ids() -> list[str]:
    """Return all available mock note IDs."""
    return sorted(_MOCK_INTERNAL_NOTES.keys())


def get_inventory_record(item_id: str) -> dict[str, Any] | None:
    """Return a mock inventory record by item ID, or None if not found."""
    record = _MOCK_INVENTORY.get(item_id)
    if record is not None:
        return dict(record)  # return copy
    return None


def list_inventory_ids() -> list[str]:
    """Return all available mock inventory item IDs."""
    return sorted(_MOCK_INVENTORY.keys())


def get_weather(location: str = "default") -> dict[str, Any]:
    """Return canned weather data. Always returns the default mock city."""
    data = _MOCK_WEATHER.get(location, _MOCK_WEATHER["default"])
    return dict(data)
