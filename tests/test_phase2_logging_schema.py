"""
Test: Phase 2 Logging Schema

Verifies that every JSONL row:
  - Contains all required fields
  - Has phase == "phase2_infra"
  - Has non_experimental == true
  - Contains no forbidden labels (ASR, TID, attack_success, etc.)
  - Placeholder rows include is_placeholder_payload == true
"""
import pytest
from client.logging_writer import (
    build_row, validate_row, _REQUIRED_FIELDS, FORBIDDEN_LABELS,
)


def _make_valid_row(**overrides):
    defaults = dict(
        run_id="test-run",
        trial_id="test-trial",
        schema_variant_id="D1-CLEAN",
        tool_density_level=1,
        mcp_metadata_condition="clean_schema",
        model_backend_mode="scripted_fake_model",
        model_backend="scripted_fake_model",
    )
    defaults.update(overrides)
    return build_row(**defaults)


class TestRequiredFields:
    def test_all_required_fields_present(self):
        row = _make_valid_row()
        missing = _REQUIRED_FIELDS - set(row.keys())
        assert len(missing) == 0, f"Missing: {missing}"

    def test_phase_is_phase2_infra(self):
        row = _make_valid_row()
        assert row["phase"] == "phase2_infra"

    def test_non_experimental_is_true(self):
        row = _make_valid_row()
        assert row["non_experimental"] is True

    def test_timestamp_utc_present(self):
        row = _make_valid_row()
        assert "timestamp_utc" in row
        assert len(row["timestamp_utc"]) > 0


class TestValidation:
    def test_valid_row_passes(self):
        row = _make_valid_row()
        errors = validate_row(row)
        assert len(errors) == 0, f"Unexpected errors: {errors}"

    def test_wrong_phase_fails(self):
        row = _make_valid_row()
        row["phase"] = "phase3_experiment"
        errors = validate_row(row)
        assert any("phase" in e for e in errors)

    def test_non_experimental_false_fails(self):
        row = _make_valid_row()
        row["non_experimental"] = False
        errors = validate_row(row)
        assert any("non_experimental" in e for e in errors)

    def test_missing_field_fails(self):
        row = _make_valid_row()
        del row["schema_variant_id"]
        errors = validate_row(row)
        assert any("Missing" in e for e in errors)


class TestForbiddenLabels:
    @pytest.mark.parametrize("label", list(FORBIDDEN_LABELS))
    def test_forbidden_label_in_smoke_test_result(self, label):
        row = _make_valid_row()
        row["smoke_test_result"] = label
        errors = validate_row(row)
        assert any("Forbidden" in e for e in errors)


class TestPlaceholderFlag:
    def test_placeholder_row_has_flag(self):
        row = _make_valid_row(is_placeholder_payload=True)
        assert row["is_placeholder_payload"] is True

    def test_non_placeholder_row(self):
        row = _make_valid_row(is_placeholder_payload=False)
        assert row["is_placeholder_payload"] is False
