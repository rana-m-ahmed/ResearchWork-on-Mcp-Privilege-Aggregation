from __future__ import annotations

from pathlib import Path

import pytest

from phase5_5.scripts.publish_checkpoint import validate_evidence_path


def test_checkpoint_path_rejects_traversal(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not canonical"):
        validate_evidence_path(tmp_path, "phase5_5/evidence/../attempts/escape.json")


def test_checkpoint_path_accepts_canonical_evidence_file(tmp_path: Path) -> None:
    assert validate_evidence_path(tmp_path, "phase5_5/evidence/checkpoints/run/checkpoint.json") == (
        "phase5_5/evidence/checkpoints/run/checkpoint.json"
    )
