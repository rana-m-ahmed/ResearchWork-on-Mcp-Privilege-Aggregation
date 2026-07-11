"""Pytest bootstrap for the Phase 5 worktree.

The host environment may point TMP/TEMP at a system location that is not
accessible inside this workspace. Force pytest and standard temp APIs to use a
workspace-local directory so fixture setup stays deterministic.
"""

from __future__ import annotations

import os
from pathlib import Path


def pytest_configure(config) -> None:  # type: ignore[override]
    root = Path(__file__).resolve().parent
    temp_root = root / ".pytest-temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("TMP", str(temp_root))
    os.environ.setdefault("TEMP", str(temp_root))
    os.environ.setdefault("PYTEST_ADDOPTS", f"--basetemp={temp_root / 'basetemp'}")
