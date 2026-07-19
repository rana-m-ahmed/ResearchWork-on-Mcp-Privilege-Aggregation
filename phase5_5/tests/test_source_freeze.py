from __future__ import annotations

import json
import hashlib
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


def test_v3_freeze_hashes_authoritative_git_blobs() -> None:
    root = Path(__file__).resolve().parents[2]
    freeze = json.loads(
        (root / "phase5_5/manifests/phase5_5_source_freeze_v3.json").read_text(
            encoding="utf-8-sig"
        )
    )
    source_commit = freeze["source_commit"]
    for relative_path, expected_hash in freeze["bound_files"].items():
        blob = subprocess.check_output(
            ["git", "-C", str(root), "show", f"{source_commit}:{relative_path}"]
        )
        assert hashlib.sha256(blob).hexdigest() == expected_hash, relative_path


def test_v3_schema_manifest_uses_line_ending_independent_schema_hashes() -> None:
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads(
        (root / "phase5_5/configs/schema_variant_manifest_v3.json").read_text(
            encoding="utf-8-sig"
        )
    )
    for variant_id, entry in manifest["variants"].items():
        schema_bytes = (root / entry["path"]).read_bytes()
        canonical_bytes = schema_bytes.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        assert hashlib.sha256(canonical_bytes).hexdigest() == entry["sha256"], variant_id
