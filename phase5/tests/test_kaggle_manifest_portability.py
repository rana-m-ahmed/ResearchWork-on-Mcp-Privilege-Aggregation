from __future__ import annotations

import hashlib
from pathlib import Path

from phase5.kaggle.run_planner import _sha256_frozen_path, _write_if_unchanged


def test_immutable_kaggle_manifest_accepts_existing_utf8_bom(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_bytes(b"\xef\xbb\xbf{\"status\": \"PASS\"}\n")

    _write_if_unchanged(path, '{"status": "PASS"}\n')

    assert path.read_bytes().startswith(b"\xef\xbb\xbf")


def test_phase45_hash_is_stable_across_newline_checkouts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    phase45_file = root / "phase4_5" / "validation" / "timing.md"
    phase45_file.parent.mkdir(parents=True)
    phase45_file.write_bytes(b"one\ntwo\n")

    assert _sha256_frozen_path(phase45_file, repository_root=root) == _sha256_frozen_path(
        root / "phase4_5" / "validation" / "timing.md",
        repository_root=root,
    )
    assert _sha256_frozen_path(phase45_file, repository_root=root) == hashlib.sha256(
        b"one\r\ntwo\r\n"
    ).hexdigest()


def test_frozen_json_evidence_hash_is_stable_across_newline_checkouts(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    evidence = root / "phase5" / "validation" / "m4_loader_status_reconciliation.json"
    evidence.parent.mkdir(parents=True)
    evidence.write_bytes(b'{"status":"PASS"}\n')

    assert _sha256_frozen_path(evidence, repository_root=root) == hashlib.sha256(
        b'{"status":"PASS"}\r\n'
    ).hexdigest()
