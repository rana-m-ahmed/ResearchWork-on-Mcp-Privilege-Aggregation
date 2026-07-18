"""Build a hash-bound Phase 5.5 implementation/source authority manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    paths = (
        "phase5/manifests/batch_partition_manifest_v3.json",
        "phase5/manifests/model_runtime_authority_v2.json",
        "phase5/implementation/prompts/task_execution_template.md",
        "phase5/attempts/schemas/attempt_workspace_metadata.schema.json",
        "docs/Phase5_Revised_Execution_Plan_v3_2.md",
        "phase5/grading/frozen_grader.py",
        "phase5/runtime/agent_loop.py",
        "phase5/runtime/engine.py",
        "phase5_5/parser.py",
        "phase5_5/runtime.py",
        "phase5_5/scripts/rebuild_historical_closure.py",
        "phase5_5/configs/frozen_state_machine_controls.json",
        "phase5_5/configs/branch_mapping.json",
        "phase5_5/configs/model_roster.json",
        "phase5_5/configs/evidence_policy.json",
    )
    files = {}
    for relative in paths:
        path = args.root / relative
        if not path.is_file():
            raise SystemExit(f"missing source-freeze input: {relative}")
        files[relative] = sha256(path)
    payload = {
        "artifact": "phase5_5_source_freeze",
        "official_dispatch": False,
        "publication_evidence": False,
        "scientific_inputs_regenerated": False,
        "source_commit": args.source_commit,
        "bound_files": files,
        "queue_authority": "phase5/manifests/batch_partition_manifest_v3.json",
        "model_authority": "phase5/manifests/model_runtime_authority_v2.json",
        "parser_version": "phase5.5-parser-v2",
        "multiple_tool_call_policy": "serial",
        "extraction_contract": "ordered_non_overlapping_top_level_candidates",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
