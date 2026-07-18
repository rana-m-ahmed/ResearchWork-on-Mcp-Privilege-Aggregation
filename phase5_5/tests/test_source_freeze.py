from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_source_freeze_is_reproducible_from_authoritative_builder(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    freeze_path = root / "phase5_5/manifests/phase5_5_source_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8-sig"))
    regenerated = tmp_path / "source_freeze.json"

    completed = subprocess.run(
        [
            sys.executable,
            str(root / "phase5_5/scripts/build_source_freeze.py"),
            "--root",
            str(root),
            "--source-commit",
            freeze["source_commit"],
            "--output",
            str(regenerated),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert regenerated.read_bytes() == freeze_path.read_bytes()
