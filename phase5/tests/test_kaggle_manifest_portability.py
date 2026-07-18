from __future__ import annotations

from pathlib import Path

from phase5.kaggle.run_planner import _write_if_unchanged


def test_immutable_kaggle_manifest_accepts_existing_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(b"\xef\xbb\xbf{\"status\": \"PASS\"}\n")

    _write_if_unchanged(path, '{"status": "PASS"}\n')

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")
