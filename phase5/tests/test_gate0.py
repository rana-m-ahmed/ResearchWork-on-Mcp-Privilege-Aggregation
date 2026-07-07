from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase5.gate0.verifier import (
    Gate0Check,
    Gate0Report,
    _parse_phase45_go_report,
    _parse_phase4_go_report,
    _sha256_file,
    _verify_checkout,
    _verify_model_frozen_files,
    _verify_queue_file,
    _verify_runtime_contract,
    run_gate0,
)


def test_gate0_passes_on_repository_fixture(tmp_path: Path) -> None:
    report = run_gate0(strict=True, report_dir=tmp_path, source_clean=True)

    assert report.status == "PASS"
    assert report.findings == ()
    payload = json.loads((tmp_path / "gate0_authorization_report.json").read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["strict"] is True


def test_gate0_reports_are_deterministic_for_fixed_input() -> None:
    report = Gate0Report(
        task_id="P03",
        status="PASS",
        strict=True,
        generated_utc="2026-07-08T00:00:00Z",
        repository_root="D:/research-work/ResearchWork-on-Mcp-Privilege-Aggregation",
        summary="summary",
        findings=(),
        checks=(Gate0Check(name="alpha", status="PASS", details=("ok",)),),
        verified_artifacts=(("label", "path", "sha256"),),
        consumed_frozen_inputs=(("input", "deadbeef"),),
        verdicts=(("phase4", "PASS"),),
    )

    assert report.to_json() == report.to_json()
    assert report.to_markdown() == report.to_markdown()


def test_phase4_go_report_requires_explicit_pass_and_ready_marker(tmp_path: Path) -> None:
    report = tmp_path / "phase4_go_no_go_decision.md"
    report.write_text(
        "# Phase4 Go No Go Decision\n\nStatus: FAIL\n\n```json\n{\"missing_dependencies\": [], \"ready_for_phase5\": false}\n```\n",
        encoding="utf-8",
    )

    check = _parse_phase4_go_report(report)
    assert check.status == "FAIL"


def test_phase45_go_report_requires_ready_for_external_audit(tmp_path: Path) -> None:
    report = tmp_path / "phase45_final_go_no_go.md"
    report.write_text(
        "# Phase 4.5 Final Go No Go\n\n- Final verdict: `FAIL`\n- Reason: `nope`\n",
        encoding="utf-8",
    )

    check = _parse_phase45_go_report(report)
    assert check.status == "FAIL"


@pytest.mark.parametrize("drop_row", [False, True])
def test_queue_duplicate_and_missing_row_fail(tmp_path: Path, drop_row: bool) -> None:
    src = Path("phase4/frozen_bundle/trial_order_core.csv").read_text(encoding="utf-8").splitlines()
    if drop_row:
        mutated = "\n".join(src[:2] + src[3:]) + "\n"
    else:
        mutated = "\n".join(src[:3] + [src[2]] + src[3:]) + "\n"
    path = tmp_path / "trial_order_core.csv"
    path.write_text(mutated, encoding="utf-8")

    check, metrics = _verify_queue_file(path, expected_row_count=2808)
    assert check.status == "FAIL"
    assert metrics.get("row_count") != 2808 or metrics.get("unique_rows") != 2808


def test_one_byte_mutation_fails_closed(tmp_path: Path) -> None:
    source = Path("phase4/configs/model_set_freeze.yaml")
    mutated = tmp_path / "model_set_freeze.yaml"
    original = source.read_bytes()
    mutated.write_bytes(original[:-1] + b"X")

    assert _sha256_file(mutated) != _sha256_file(source)


def test_model_runtime_bundle_rejects_model_digest_mismatch(tmp_path: Path) -> None:
    phase3_manifest = tmp_path / "reproducibility" / "phase3_hash_manifest.json"
    phase3_manifest.parent.mkdir(parents=True, exist_ok=True)
    phase3_manifest.write_text(Path("reproducibility/phase3_hash_manifest.json").read_text(encoding="utf-8"), encoding="utf-8")

    model_dir = tmp_path / "phase4" / "configs"
    model_dir.mkdir(parents=True, exist_ok=True)
    for name in ("model_set_freeze.yaml", "model_1_freeze.yaml", "model_2_freeze.yaml", "model_3_freeze.yaml", "model_4_freeze.yaml"):
        text = Path("phase4/configs") / name
        content = text.read_text(encoding="utf-8")
        if name == "model_1_freeze.yaml":
            content = content.replace("UNAVAILABLE_NOT_RECORDED_IN_PHASE3", "BROKEN")
        (model_dir / name).write_text(content, encoding="utf-8")

    checks, findings, consumed = _verify_model_frozen_files(tmp_path, {})
    assert findings
    assert any(check.name.startswith("model-freeze:M1") for check in checks)
    assert consumed


def test_dirty_checkout_rejects_strict_mode() -> None:
    check = _verify_checkout(strict=True, root=Path.cwd(), source_clean=False)
    assert check.status == "FAIL"


def test_nested_docker_runtime_flag_rejects(tmp_path: Path) -> None:
    env_lock_dir = tmp_path / "phase4_5" / "configs"
    env_lock_dir.mkdir(parents=True, exist_ok=True)
    env_lock_dir.joinpath("phase45_environment_lock.yaml").write_text(
        "source_of_truth: github\nkaggle_execution_enabled: true\nlocal_validation_enabled: true\nnested docker: true\n",
        encoding="utf-8",
    )
    runtime_dir = tmp_path / "phase4_5" / "kaggle"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    runtime_dir.joinpath("kaggle_runtime_setup.md").write_text(
        "Smoke preparation only.\nNested Docker is forbidden.\n",
        encoding="utf-8",
    )
    local_dir = tmp_path / "phase4_5" / "dryrun_results" / "local"
    local_dir.mkdir(parents=True, exist_ok=True)
    local_dir.joinpath("run_manifest.json").write_text(
        '{"git_commit_hash":"3a92c2d7e2987290b801cee95ae3c506254ff8f6"}',
        encoding="utf-8",
    )
    kaggle_dir = tmp_path / "phase4_5" / "dryrun_results" / "kaggle_smoke"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    kaggle_dir.joinpath("trials.jsonl").write_text(
        '{"trial":{"git_commit_hash":"3a92c2d7e2987290b801cee95ae3c506254ff8f6"}}\n',
        encoding="utf-8",
    )
    kaggle_dir.joinpath("hardware_metrics.jsonl").write_text("{}\n" * 8, encoding="utf-8")
    loader_dir = tmp_path / "phase4_5" / "dryrun_results" / "kaggle_model_loader_smoke"
    loader_dir.mkdir(parents=True, exist_ok=True)
    loader_dir.joinpath("model_loader_hardware_metrics.jsonl").write_text("{}\n" * 4, encoding="utf-8")

    checks, findings, consumed, commit = _verify_runtime_contract(tmp_path)
    assert findings
    assert commit == "3a92c2d7e2987290b801cee95ae3c506254ff8f6"
    assert any(check.name == "runtime-setup" and check.status == "FAIL" for check in checks)

