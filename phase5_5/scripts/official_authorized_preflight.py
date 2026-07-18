"""Authorize official execution only through an additive Phase 5.5 record."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise RuntimeError(f"expected object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-slot", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    auth = load(root / "phase5_5/authorization/official_execution_authorization.json")
    slot = args.model_slot.upper()
    branch = f"phase5_5-model-{slot.removeprefix('M')}"
    config = load_from_git(root, branch, "phase5_5/branch_config.json")
    checks: dict[str, Any] = {}
    failures: list[str] = []
    expected = {
        "authorization_status": "AUTHORIZED_FOR_BOUNDED_EXECUTION",
        "model_slot": slot,
        "branch": branch,
        "dataset_version": "P5-DV-1.0.2-A7C91E42",
        "common_source_commit": "b90158e6",
        "parser_version": "phase5.5-parser-v2",
        "multiple_tool_call_policy": "serial",
        "official_trial": True,
        "counts_for_phase5": True,
        "publication_evidence": True,
        "synthetic_fixture": False,
    }
    for key, value in expected.items():
        if auth.get(key) != value:
            failures.append(f"authorization:{key}")
    if auth.get("exact_model_identifier") != config.get("exact_model_identifier"):
        failures.append("model-identity-mismatch")
    current_head = git(root, "rev-parse", "HEAD")
    base_head = auth.get("base_branch_head")
    ancestor = subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", str(base_head), current_head],
        check=False,
    ).returncode == 0
    if not ancestor:
        failures.append("authorization-base-is-not-ancestor")
    status = git(root, "status", "--porcelain")
    if status:
        failures.append("checkout-dirty")

    preflight_path = args.output.with_name(args.output.stem + "_frozen.json")
    frozen = subprocess.run(
        [
            sys.executable,
            "phase5_5/scripts/official_preflight.py",
            "--root",
            str(root),
            "--output",
            str(preflight_path),
        ],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    frozen_report = load(preflight_path)
    frozen_failures = frozen_report.get("failures", [])
    if frozen_failures != ["official-dispatch-disabled"]:
        failures.extend(f"frozen-preflight:{item}" for item in frozen_failures)
    checks["frozen_preflight"] = frozen_report
    checks["authorization"] = auth
    checks["current_head"] = current_head
    checks["base_branch_head"] = base_head
    report = {
        "artifact": "phase5_5_official_authorized_preflight_v1",
        "model_slot": slot,
        "branch": branch,
        "pass": not failures,
        "failures": failures,
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "output": args.output.as_posix()}))
    return 0 if report["pass"] else 1


def load_from_git(root: Path, branch: str, relative: str) -> dict[str, Any]:
    value = subprocess.check_output(["git", "-C", str(root), "show", f"{branch}:{relative}"])
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise RuntimeError(f"expected object: {branch}:{relative}")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
