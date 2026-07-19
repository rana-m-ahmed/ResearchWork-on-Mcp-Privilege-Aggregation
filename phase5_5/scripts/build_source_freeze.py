"""Build a hash-bound Phase 5.5 implementation/source authority manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def sha256(data: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(data)
    return digest.hexdigest()


def committed_bytes(root: Path, source_commit: str, relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "-C", str(root), "show", f"{source_commit}:{relative}"],
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--variant", choices=("legacy", "v3"), default="legacy")
    args = parser.parse_args()
    paths = (
        "phase5/manifests/batch_partition_manifest_v3.json",
        "phase5/manifests/model_runtime_authority_v2.json",
        "phase5/configs/upstream_artifact_registry.json",
        "phase5/implementation/prompts/task_execution_template.md",
        "phase5/attempts/schemas/attempt_workspace_metadata.schema.json",
        "docs/Phase5_Revised_Execution_Plan_v3_2.md",
        "phase5/grading/frozen_grader.py",
        "phase5/runtime/agent_loop.py",
        "phase5/runtime/engine.py",
        "phase5_5/parser.py",
        "phase5_5/runtime.py",
        "phase5_5/scripts/rebuild_historical_closure.py",
        "phase5_5/scripts/official_preflight.py",
        "phase5_5/configs/frozen_state_machine_controls.json",
        "phase5_5/configs/branch_mapping.json",
        "phase5_5/configs/model_roster.json",
        "phase5_5/configs/evidence_policy.json",
    )
    if args.variant == "v3":
        paths = paths + (
            "phase5/runtime/mcp_server_launcher.py",
            "phase5/runtime/model_backend_adapter.py",
            "phase5/runtime/prompt_compiler.py",
            "phase5/runtime/tool_dispatch.py",
            "phase5/runtime/official_execution.py",
            "phase5/campaign.py",
            "phase5_5/configs/schema_variant_manifest_v3.json",
            "phase5_5/configs/task_argument_bindings_v1.json",
            "phase5_5/configs/treatment_and_analysis_contract_v3.json",
            "phase5_5/scripts/build_source_freeze.py",
            "phase5/implementation/reports/phase5_5/phase5_5_zero_acceptance_root_cause_audit.md",
            "phase5/implementation/reports/phase5_5/phase5_5_treatment_accounting_amendment.md",
            "phase5_5/scripts/build_treatment_manifests.py",
            "phase5_5/scripts/build_kaggle_runner.py",
            "phase5_5/scripts/build_official_runner.py",
            "phase5_5/scripts/official_preflight.py",
            "phase5_5/scripts/official_authorized_preflight.py",
            "phase5_5/scripts/run_qualification_canary.py",
            "phase5_5/authorization/official_execution_authorization.json",
            "phase5_5/branch_config.json",
            "phase5_5/configs/evidence_policy.json",
            "phase5/manifests/batch_partition_manifest_v3_treatment.json",
            "phase5/validation/kaggle_run_plan_v3_treatment.json",
            "phase5_5/kaggle/phase5_5_runner.ipynb",
            "phase5_5/kaggle/phase5_5_official_runner.ipynb",
        )
    files = {}
    for relative in paths:
        path = args.root / relative
        if not path.is_file():
            raise SystemExit(f"missing source-freeze input: {relative}")
        try:
            files[relative] = sha256(committed_bytes(args.root, args.source_commit, relative))
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"source-freeze commit is missing bound file: {args.source_commit}:{relative}") from exc
    payload = {
        "artifact": "phase5_5_source_freeze" if args.variant == "legacy" else "phase5_5_source_freeze_v3",
        "official_dispatch": False,
        "publication_evidence": False,
        "scientific_inputs_regenerated": False,
        "source_commit": args.source_commit,
        "bound_files": files,
        "queue_authority": "phase5/manifests/batch_partition_manifest_v3.json",
        "model_authority": "phase5/manifests/model_runtime_authority_v2.json",
        "parser_version": "phase5.5-parser-v2" if args.variant == "legacy" else "phase5.5-parser-v3-mcp-schema",
        "multiple_tool_call_policy": "serial",
        "extraction_contract": "ordered_non_overlapping_top_level_candidates",
    }
    if args.variant == "v3":
        payload["dataset_version"] = "P5-DV-1.1.0-TREATMENT-V3"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
