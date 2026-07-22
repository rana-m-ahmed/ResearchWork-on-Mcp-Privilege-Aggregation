from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def git_run(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)


def test_official_publication_hashes_evidence_and_records_purge(tmp_path: Path) -> None:
    root = tmp_path / "work"
    remote = tmp_path / "remote.git"
    root.mkdir()
    remote.mkdir()
    git_run(remote, "init", "--bare")
    git_run(root, "init")
    git_run(root, "config", "user.name", "phase5.5-test")
    git_run(root, "config", "user.email", "phase5.5-test@example.invalid")
    script = Path(__file__).resolve().parents[1] / "scripts/publish_official_evidence.py"
    destination = root / "phase5_5/scripts/publish_official_evidence.py"
    destination.parent.mkdir(parents=True)
    shutil.copy2(script, destination)
    (root / "README.txt").write_text("fixture\n", encoding="utf-8")
    git_run(root, "add", ".")
    git_run(root, "commit", "-m", "fixture")
    git_run(root, "branch", "-M", "phase5_5-model-1")
    git_run(root, "remote", "add", "origin", str(remote))
    git_run(root, "push", "--set-upstream", "origin", "phase5_5-model-1")
    parent = git(root, "rev-parse", "HEAD")

    evidence = root / "phase5_5/evidence/attempts/A1/output.txt"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("raw-preserved-evidence\n", encoding="utf-8")
    lineage = root / "phase5_5/evidence/lineage.csv"
    lineage.write_text(
        "run_id,raw_attempt_directory\n"
        f"TEST-RUN,{evidence.parent.as_posix()}\n",
        encoding="utf-8",
    )
    output = tmp_path / "receipt.json"
    environment = os.environ.copy()
    environment["PHASE5_GITHUB_TOKEN"] = "test-only-token"
    completed = subprocess.run(
        [
            sys.executable,
            str(destination),
            "--root",
            str(root),
            "--model-slot",
            "M1",
            "--run-id",
            "TEST-RUN",
            "--expected-parent",
            parent,
            "--output",
            str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert completed.returncode == 0, completed.stderr
    receipt = json.loads(output.read_text(encoding="utf-8"))
    manifest = json.loads(
        (root / "phase5_5/evidence/publications/TEST-RUN/official_publication_manifest.json").read_text(encoding="utf-8")
    )
    assert receipt["credential_purged"] is True
    assert {item["path"] for item in manifest["files"]} == {
        "phase5_5/evidence/attempts/A1/output.txt",
        "phase5_5/evidence/lineage.csv",
    }
    assert git(root, "rev-parse", "HEAD") == receipt["receipt_commit"]
    assert git(remote, "rev-parse", "refs/heads/phase5_5-model-1") == receipt["receipt_commit"]
