from __future__ import annotations

from pathlib import Path

import phase5


def test_phase5_import_smoke() -> None:
    assert phase5.__version__ == "0.1.0"


def test_required_phase5_packages_exist() -> None:
    assert (Path("phase5") / "__init__.py").is_file()
    assert (Path("phase5") / "guards.py").is_file()
