from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_official_preflight_preserves_synthetic_boundary(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    output = tmp_path / "official_preflight.json"
    completed = subprocess.run(
        [
            sys.executable,
            str(root / "phase5_5/scripts/official_preflight.py"),
            "--root",
            str(root),
            "--allow-dirty",
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["official_evidence_created"] is False
    assert len(report["checks"]["branches"]) == 4
    assert all(item["source_match"] is True for item in report["checks"]["branches"])
    assert all(item["receipt_official"] is False for item in report["checks"]["branches"])
    assert report["checks"]["historical_closure"]["reconciliation_pass"] is True
    assert report["checks"]["synthetic_canary"]["pass"] is True
    assert completed.returncode in {0, 1}
