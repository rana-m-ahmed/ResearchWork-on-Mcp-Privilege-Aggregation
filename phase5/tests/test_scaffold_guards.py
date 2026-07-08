from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from phase5.guards import (
    reject_evidence_source_staging,
    reject_frozen_path_changes,
    scan_text_for_forbidden_analysis,
    scan_text_for_secrets,
)


def test_frozen_path_guard_blocks_phase4_changes() -> None:
    blocked = reject_frozen_path_changes(["phase4/configs/phase5_schema_freeze.json"])
    assert blocked == ["phase4/configs/phase5_schema_freeze.json"]


def test_frozen_path_guard_allows_phase5_paths() -> None:
    assert reject_frozen_path_changes(["phase5/implementation/reports/P01_implementation_report.md"]) == []


def test_evidence_guard_blocks_source_staging() -> None:
    rejected = reject_evidence_source_staging(["client/orchestrator.py"])
    assert rejected == ["client/orchestrator.py"]


def test_evidence_guard_allows_reporting_paths() -> None:
    assert reject_evidence_source_staging(["phase5/implementation/reports/P01_implementation_report.md"]) == []


def test_evidence_guard_allows_phase5_evidence_and_attempt_paths() -> None:
    assert reject_evidence_source_staging(["phase5/evidence/attempts/P5ATT-trial-001-A000-ABCDEF12/attempt_manifest.json"]) == []
    assert reject_evidence_source_staging(["phase5/attempts/attempt_lineage.csv"]) == []


def test_secret_lint_detects_secret_like_text() -> None:
    findings = scan_text_for_secrets("token ghp_abcdefghijklmnopqrstuvwxyz123456")
    assert findings


def test_forbidden_analysis_lint_detects_analysis_terms() -> None:
    findings = scan_text_for_forbidden_analysis("p-values and confidence intervals")
    assert findings


def test_instruction_script_runs_successfully() -> None:
    result = subprocess.run(
        [sys.executable, "phase5/scripts/check_phase5_instructions.py"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_frozen_guard_cli_rejects_phase4_paths() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "phase5/scripts/check_phase5_frozen_paths.py",
            "--changed",
            "phase4/configs/phase5_schema_freeze.json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1


def test_frozen_phase4_artifacts_use_crlf_checkout_rules() -> None:
    gitattributes = Path(".gitattributes").read_text(encoding="utf-8")
    assert "client/** text eol=crlf" in gitattributes
    assert "docs/** text eol=crlf" in gitattributes
    assert "phase2_5/** text eol=crlf" in gitattributes
    assert "phase3/** text eol=crlf" in gitattributes
    assert "phase4/** text eol=crlf" in gitattributes
    assert "phase4_5/** text eol=crlf" in gitattributes
    assert "prompts/*.txt text eol=crlf" in gitattributes
    assert "phase5/tests/fixtures/p08/*.txt text eol=lf" in gitattributes
    assert "server/** text eol=crlf" in gitattributes
    assert "client/model_backend.py text eol=lf" in gitattributes
    assert "docs/Phase5_Practical_Implementation_Plan_v1_1_Audited_Long_Run.md text eol=lf" in gitattributes
    assert "docs/Phase5_Revised_Execution_Plan_v3_2.md text eol=lf" in gitattributes
    assert "phase3/tasks/task_corpus_hash.txt text eol=lf" in gitattributes
    assert "phase3/tasks/task_generation_metadata.json text eol=lf" in gitattributes
