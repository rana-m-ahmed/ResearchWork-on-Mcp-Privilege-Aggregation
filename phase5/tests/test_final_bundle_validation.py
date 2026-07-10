from __future__ import annotations

from pathlib import Path

from phase5.kaggle.final_bundle_validation import audit_bundle


ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "phase5_i17e_genuine_kaggle_qualification_bundle (1)"


def test_current_bundle_requires_targeted_repair() -> None:
    result = audit_bundle(BUNDLE)

    assert result["kaggle_implementation_verdict"] == "TARGETED REPAIR REQUIRED"
    assert result["independent_phase5_readiness_verdict"] == "TARGETED REPAIR REQUIRED"
    assert "mandatory evidence missing: write_ahead_durability_evidence.json" in result["failed_gates"]
    assert "mandatory evidence missing: source_reverification_receipt.json" in result["failed_gates"]


def test_current_bundle_still_proves_real_tool_execution() -> None:
    result = audit_bundle(BUNDLE)

    assert "tool_execution_evidence.json" in result["present_files"]
    assert result["manifest_summary"]["status"] == "passed"
