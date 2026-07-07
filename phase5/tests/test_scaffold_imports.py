from __future__ import annotations

from pathlib import Path

import phase5


def test_phase5_import_smoke() -> None:
    assert phase5.__version__ == "0.1.0"


def test_required_phase5_packages_exist() -> None:
    assert (Path("phase5") / "__init__.py").is_file()
    assert (Path("phase5") / "guards.py").is_file()
    assert (Path("phase5") / "evidence" / "__init__.py").is_file()
    assert (Path("phase5") / "evidence" / "events.py").is_file()
    assert (Path("phase5") / "evidence" / "artifacts.py").is_file()
    assert (Path("phase5") / "attempts" / "__init__.py").is_file()
    assert (Path("phase5") / "attempts" / "lineage.py").is_file()
    assert (Path("phase5") / "attempts" / "recovery.py").is_file()
    assert (Path("phase5") / "attempts" / "schemas" / "attempt_lineage.schema.json").is_file()
    assert (Path("phase5") / "attempts" / "templates" / "attempt_lineage.csv").is_file()
    assert (Path("phase5") / "attempts" / "templates" / "attempt_workspace_metadata.json").is_file()
    assert (Path("phase5") / "queues" / "batch_partitioner.py").is_file()
    assert (Path("phase5") / "queues" / "pending_resolver.py").is_file()
    assert (Path("phase5") / "kaggle" / "run_planner.py").is_file()
