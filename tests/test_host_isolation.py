"""
Test: Host Isolation

Verifies that mock tools and the tool path cannot access:
  - /root
  - /home
  - project root (as writable mount)
  - parent directories
  - Windows-style C:\\ paths
  - write locations outside /tmp/mcp_trial and /output_logs
  - log deletion/overwrite through tool path

These are structural/code-analysis tests. Full container-level isolation
is verified when running inside Docker.
"""
import ast
import os

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TOOL_FILES = [
    os.path.join(PROJECT_ROOT, "server", "tool_definitions", f)
    for f in [
        "read_internal_notes.py", "write_outbox.py", "get_local_weather.py",
        "query_local_inventory.py", "log_event.py",
    ]
]

FORBIDDEN_PATH_FRAGMENTS = [
    "/root", "/home", "C:\\\\", "C:/", "C:\\",
    "../", "..\\\\",
]


class TestNoForbiddenPaths:
    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_forbidden_path_strings(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        for frag in FORBIDDEN_PATH_FRAGMENTS:
            assert frag not in source, (
                f"{os.path.basename(tool_file)} contains forbidden path '{frag}'"
            )


class TestNoFilesystemOps:
    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_open_calls(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    pytest.fail(f"{os.path.basename(tool_file)} calls open()")

    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_os_path_ops(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        for forbidden in ["os.path", "os.listdir", "os.walk", "os.remove",
                          "os.unlink", "os.rmdir", "shutil"]:
            assert forbidden not in source, (
                f"{os.path.basename(tool_file)} uses {forbidden}"
            )


class TestNoLogDeletion:
    def test_tools_cannot_import_logging_writer(self):
        for tool_file in TOOL_FILES:
            with open(tool_file, "r", encoding="utf-8") as f:
                source = f.read()
            assert "logging_writer" not in source
            assert "output_logs" not in source

    def test_tools_do_not_reference_log_files(self):
        for tool_file in TOOL_FILES:
            with open(tool_file, "r", encoding="utf-8") as f:
                source = f.read()
            assert ".jsonl" not in source


class TestNoNetworkOps:
    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_network_imports(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        for mod in ["socket", "urllib", "http.client", "requests", "httpx"]:
            assert mod not in source, (
                f"{os.path.basename(tool_file)} references {mod}"
            )


class TestNoShellExec:
    @pytest.mark.parametrize("tool_file", TOOL_FILES)
    def test_no_subprocess(self, tool_file):
        with open(tool_file, "r", encoding="utf-8") as f:
            source = f.read()
        for kw in ["subprocess", "os.system", "os.popen", "os.exec"]:
            assert kw not in source
