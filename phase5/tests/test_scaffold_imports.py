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
    assert (Path("phase5") / "evidence" / "archive_index.py").is_file()
    assert (Path("phase5") / "evidence" / "manifest_builder.py").is_file()
    assert (Path("phase5") / "evidence" / "trial_materializer.py").is_file()
    assert (Path("phase5") / "attempts" / "__init__.py").is_file()
    assert (Path("phase5") / "attempts" / "lineage.py").is_file()
    assert (Path("phase5") / "attempts" / "recovery.py").is_file()
    assert (Path("phase5") / "grading" / "__init__.py").is_file()
    assert (Path("phase5") / "grading" / "frozen_grader.py").is_file()
    assert (Path("phase5") / "grading" / "tid.py").is_file()
    assert (Path("phase5") / "attempts" / "schemas" / "attempt_lineage.schema.json").is_file()
    assert (Path("phase5") / "attempts" / "templates" / "attempt_lineage.csv").is_file()
    assert (Path("phase5") / "attempts" / "templates" / "attempt_workspace_metadata.json").is_file()
    assert (Path("phase5") / "runtime" / "mcp_server_launcher.py").is_file()
    assert (Path("phase5") / "runtime" / "agent_loop.py").is_file()
    assert (Path("phase5") / "runtime" / "parser_adapter.py").is_file()
    assert (Path("phase5") / "runtime" / "model_backend_adapter.py").is_file()
    assert (Path("phase5") / "runtime" / "prompt_compiler.py").is_file()
    assert (Path("phase5") / "runtime" / "prompt_serialization.py").is_file()
    assert (Path("phase5") / "runtime" / "reset_controller.py").is_file()
    assert (Path("phase5") / "runtime" / "tool_dispatch.py").is_file()
    assert (Path("phase5") / "runtime" / "token_budget.py").is_file()
    assert (Path("phase5") / "runtime" / "workspace_isolation.py").is_file()
    assert (Path("phase5") / "queues" / "batch_partitioner.py").is_file()
    assert (Path("phase5") / "queues" / "pending_resolver.py").is_file()
    assert (Path("phase5") / "kaggle" / "run_planner.py").is_file()
    assert (Path("phase5") / "kaggle" / "handoff.py").is_file()
    assert (Path("phase5") / "kaggle" / "validation.py").is_file()
    assert (Path("phase5") / "kaggle" / "phase5_runner.ipynb").is_file()
    assert (Path("phase5") / "kaggle" / "README.md").is_file()
    assert (Path("phase5") / "kaggle" / "operator_runbook.md").is_file()
    assert (Path("phase5") / "kaggle" / "handoff_contract.md").is_file()
    assert (Path("phase5") / "kaggle" / "secret_names.md").is_file()
    assert (Path("phase5") / "kaggle" / "manifests" / "phase5_runner_parameters.schema.json").is_file()
    assert (Path("phase5") / "runtime" / "session.py").is_file()
    assert (Path("phase5") / "seal.py").is_file()
    assert (Path("phase5") / "campaign.py").is_file()
    assert (Path("phase5") / "checkpoints" / "__init__.py").is_file()
    assert (Path("phase5") / "checkpoints" / "schema.py").is_file()
    assert (Path("phase5") / "checkpoints" / "schemas" / "checkpoint.schema.json").is_file()
    assert (Path("phase5") / "configs" / "sync_allowlist.yaml").is_file()
    assert (Path("phase5") / "sync" / "__init__.py").is_file()
    assert (Path("phase5") / "sync" / "credential_scope.py").is_file()
    assert (Path("phase5") / "sync" / "github_checkpoint.py").is_file()
    assert (Path("phase5") / "sync" / "path_allowlist.py").is_file()
    assert (Path("phase5") / "sync" / "sync_receipt.py").is_file()
