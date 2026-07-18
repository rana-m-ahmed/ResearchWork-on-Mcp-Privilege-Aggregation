from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_qualification_canary_script_entrypoint_resolves_repo_imports() -> None:
    root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, str(root / "phase5_5/scripts/run_qualification_canary.py"), "--help"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--root" in completed.stdout
