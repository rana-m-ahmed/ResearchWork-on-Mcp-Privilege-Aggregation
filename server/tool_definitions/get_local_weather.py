"""
get_local_weather — Benign distractor tool.

Density levels: D3, D5
Aggregation role: Benign distractor
Logical tool ID: get_local_weather

Returns canned local weather data. Deterministic, mock-data-only.
Implementation is identical across clean and poisoned metadata variants.
"""

from __future__ import annotations

from server.mock_data_store import get_weather

# ---- Stable identity ----
LOGICAL_TOOL_ID = "get_local_weather"
EXPOSED_TOOL_NAME = "get_local_weather"


def execute(location: str = "default") -> dict:
    """Return canned local weather for a mock location.

    Args:
        location: Location name (always returns default mock city data).

    Returns:
        Weather data dict.
    """
    return get_weather(location)
