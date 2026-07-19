from __future__ import annotations

import csv
from pathlib import Path

import pytest

from phase5_5.scripts.publish_official_evidence import parse_porcelain_paths, run_evidence_files


def test_porcelain_parser_handles_renames() -> None:
    raw = "?? phase5_5/evidence/attempts/a/file.json\0R  phase5_5/evidence/old.json\tphase5_5/evidence/new.json\0"
    assert parse_porcelain_paths(raw) == ["phase5_5/evidence/attempts/a/file.json", "phase5_5/evidence/old.json", "phase5_5/evidence/new.json"]


def test_run_evidence_files_reconciles_checkpoint_commits(tmp_path: Path) -> None:
    attempt = tmp_path / "phase5_5/evidence/attempts/a1"
    attempt.mkdir(parents=True)
    (attempt / "attempt_manifest.json").write_text("{}\n", encoding="utf-8")
    lineage = tmp_path / "phase5_5/evidence/lineage.csv"
    lineage.parent.mkdir(parents=True, exist_ok=True)
    with lineage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["run_id", "raw_attempt_directory"])
        writer.writeheader()
        writer.writerow({"run_id": "RUN-1", "raw_attempt_directory": attempt.as_posix()})
    assert run_evidence_files(tmp_path, "RUN-1") == ["phase5_5/evidence/attempts/a1/attempt_manifest.json", "phase5_5/evidence/lineage.csv"]


def test_run_evidence_files_fails_closed_for_missing_run(tmp_path: Path) -> None:
    lineage = tmp_path / "phase5_5/evidence/lineage.csv"
    lineage.parent.mkdir(parents=True)
    lineage.write_text("run_id,raw_attempt_directory\nRUN-OTHER,/tmp/other\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="no lineage rows"):
        run_evidence_files(tmp_path, "RUN-1")
