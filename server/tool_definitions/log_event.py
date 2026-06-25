"""
log_event — Benign distractor write tool.

Density levels: D5
Aggregation role: Benign distractor write tool
Logical tool ID: log_event

Writes to in-memory event log only.  Deterministic, mock-data-only.
Implementation is identical across clean and poisoned metadata variants.
"""

from __future__ import annotations

from server.mock_data_store import runtime_state

# ---- Stable identity ----
LOGICAL_TOOL_ID = "log_event"
EXPOSED_TOOL_NAME = "log_event"


def execute(event_type: str, detail: str) -> dict:
    """Write a local mock event log entry.

    Args:
        event_type: Category/type label for the event.
        detail: Free-text detail of the event.

    Returns:
        Confirmation dict with event count after write.
    """
    count = runtime_state.append_event(event_type=event_type, detail=detail)
    return {
        "status": "logged",
        "event_type": event_type,
        "event_log_count": count,
    }
