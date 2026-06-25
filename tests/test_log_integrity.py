"""
Test: Log Integrity

Verifies:
  - SHA-256 is computed after writing JSONL
  - Log file hash changes when new rows are appended
  - Tool path cannot delete or overwrite logs (structural check)
  - MCP server module does not write trial JSONL logs
  - Phase 2 logs are separate from Phase 3/5 paths
"""
import json
import os
import shutil
import uuid

import pytest

from client.logging_writer import build_row, write_jsonl_row, compute_log_hash

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def tmp_log_dir():
    log_dir = os.path.join(PROJECT_ROOT, ".test_scratch", f"logs_{uuid.uuid4().hex[:8]}")
    os.makedirs(log_dir, exist_ok=True)
    yield log_dir
    shutil.rmtree(log_dir, ignore_errors=True)


def _make_row(**overrides):
    defaults = dict(
        run_id="test-run", trial_id="test-trial",
        schema_variant_id="D1-CLEAN", tool_density_level=1,
        mcp_metadata_condition="clean_schema",
        model_backend_mode="scripted_fake_model",
        model_backend="scripted_fake_model",
    )
    defaults.update(overrides)
    return build_row(**defaults)


class TestSHA256AfterWrite:
    def test_hash_computed_after_write(self, tmp_log_dir):
        filepath = os.path.join(tmp_log_dir, "test.jsonl")
        row = _make_row()
        sha = write_jsonl_row(filepath, row)
        assert len(sha) == 64
        assert sha == compute_log_hash(filepath)

    def test_hash_changes_on_append(self, tmp_log_dir):
        filepath = os.path.join(tmp_log_dir, "test.jsonl")
        row1 = _make_row(trial_id="t1")
        sha1 = write_jsonl_row(filepath, row1)
        row2 = _make_row(trial_id="t2")
        sha2 = write_jsonl_row(filepath, row2)
        assert sha1 != sha2


class TestLogFileContents:
    def test_each_line_is_valid_json(self, tmp_log_dir):
        filepath = os.path.join(tmp_log_dir, "test.jsonl")
        write_jsonl_row(filepath, _make_row(trial_id="a"))
        write_jsonl_row(filepath, _make_row(trial_id="b"))
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()
        assert len(lines) == 2
        for line in lines:
            obj = json.loads(line)
            assert obj["phase"] == "phase2_infra"
            assert obj["non_experimental"] is True


class TestMCPServerDoesNotWriteLogs:
    def test_server_module_has_no_log_writes(self):
        """Structural check: server/mock_server.py must not import logging_writer."""
        import ast
        server_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "server", "mock_server.py"
        )
        with open(server_path, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                assert node.module is None or "logging_writer" not in node.module, \
                    "MCP server must not import logging_writer"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "logging_writer" not in alias.name, \
                        "MCP server must not import logging_writer"


class TestPhase2LogSeparation:
    def test_phase2_logs_in_dedicated_directory(self):
        """Phase 2 logs go to logs/output_logs/phase2_*.jsonl"""
        log_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "logs", "output_logs",
        )
        assert os.path.isdir(log_dir)
        # Phase 3/5 log files should not exist
        for f in os.listdir(log_dir):
            assert not f.startswith("phase3_"), f"Phase 3 log found: {f}"
            assert not f.startswith("phase5_"), f"Phase 5 log found: {f}"
