"""
read_internal_notes — Primary read capability.

Density levels: D1, D3, D5
Aggregation role: Primary read capability
Logical tool ID: read_internal_notes

Deterministic, mock-data-only, no filesystem/network/credential access.
Implementation is identical across clean and poisoned metadata variants.
"""

from __future__ import annotations

from server.mock_data_store import get_internal_note, list_note_ids

# ---- Stable identity (PHASE2.md §2.5 logical-ID rule) ----
LOGICAL_TOOL_ID = "read_internal_notes"
EXPOSED_TOOL_NAME = "read_internal_notes"  # equal to logical ID (tool-name poisoning disabled)


def execute(note_id: str) -> dict:
    """Read a mock internal note by ID.

    Args:
        note_id: The identifier of the note to retrieve.

    Returns:
        A dict with ``found`` bool, ``note_id``, and ``content`` (or available IDs on miss).
    """
    content = get_internal_note(note_id)
    if content is not None:
        return {
            "found": True,
            "note_id": note_id,
            "content": content,
        }
    return {
        "found": False,
        "note_id": note_id,
        "content": None,
        "available_ids": list_note_ids(),
    }
