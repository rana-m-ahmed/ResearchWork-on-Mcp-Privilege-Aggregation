from __future__ import annotations

from pathlib import Path

import pytest

from phase5.guards import ensure_required_agents_exist, validate_agents_hierarchy, validate_report_json


def test_agents_hierarchy_present() -> None:
    assert ensure_required_agents_exist() == []
    assert validate_agents_hierarchy() == []


def test_implementation_report_json_schema() -> None:
    report = Path("phase5/implementation/reports/P01_implementation_report.json")
    missing = validate_report_json(
        report,
        required_keys=[
            "task_id",
            "status",
            "generated_utc",
            "files_changed",
            "frozen_inputs_consumed",
            "tests_run",
            "fault_tests",
            "remaining_blockers",
        ],
    )
    assert missing == []


def test_workflow_yaml_files_parse_when_tooling_available() -> None:
    yaml = pytest.importorskip("yaml")
    from phase5.guards import validate_workflow_yaml

    for path in Path(".github/workflows").glob("phase5-*.yml"):
        assert validate_workflow_yaml(path) == []
