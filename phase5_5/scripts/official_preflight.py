"""Fail-closed preflight for the transition from qualification to official runs."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.runtime.model_backend_adapter import load_frozen_model_backend_identity


SLOTS = ("M1", "M2", "M3", "M4")
BRANCHES = {slot: f"phase5_5-model-{slot.removeprefix('M')}" for slot in SLOTS}


def digest(path: Path, *, root: Path, source_commit: str) -> str:
    relative = path.relative_to(root).as_posix()
    committed = subprocess.check_output(["git", "-C", str(root), "show", f"{source_commit}:{relative}"])
    return hashlib.sha256(committed).hexdigest()


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def git_json(root: Path, branch: str, path: str) -> dict[str, Any]:
    value = subprocess.check_output(["git", "-C", str(root), "show", f"{branch}:{path}"])
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise ValueError(f"{branch}:{path} must contain an object")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    failures: list[str] = []
    checks: dict[str, Any] = {}

    freeze_path = root / "phase5_5/manifests/phase5_5_source_freeze.json"
    freeze = json.loads(freeze_path.read_text(encoding="utf-8"))
    freeze_failures = []
    source_commit = freeze.get("source_commit")
    for relative, expected in freeze["bound_files"].items():
        path = root / relative
        if not path.is_file():
            freeze_failures.append(f"missing:{relative}")
        else:
            try:
                actual = digest(path, root=root, source_commit=source_commit)
            except subprocess.CalledProcessError:
                freeze_failures.append(f"missing-commit-file:{relative}")
            else:
                if actual != expected:
                    freeze_failures.append(f"hash:{relative}")
    checks["source_freeze"] = {"source_commit": source_commit, "bound_file_failures": freeze_failures}
    failures.extend(f"source-freeze:{item}" for item in freeze_failures)

    status = git_output(root, "status", "--porcelain")
    checks["checkout_clean"] = not bool(status)
    if status and not args.allow_dirty:
        failures.append("checkout-dirty")

    branch_results = []
    for slot in SLOTS:
        branch = BRANCHES[slot]
        try:
            config = git_json(root, branch, "phase5_5/branch_config.json")
            receipt = git_json(root, branch, "phase5_5/evidence/qualification/qualification_receipt.json")
            identity = load_frozen_model_backend_identity(root, model_slot=slot)
            result = {
                "slot": slot,
                "branch": branch,
                "branch_head": git_output(root, "rev-parse", branch),
                "model_id": config.get("exact_model_identifier"),
                "identity_match": config.get("exact_model_identifier") == identity.exact_model_identifier,
                "source_match": config.get("common_source_commit") == freeze.get("source_commit"),
                "qualification_receipt": receipt.get("within_turn_attack_outcome"),
                "receipt_official": receipt.get("official_trial"),
            }
            branch_results.append(result)
            if not result["identity_match"]:
                failures.append(f"{slot}:model-identity-mismatch")
            if not result["source_match"]:
                failures.append(f"{slot}:source-mismatch")
            if result["receipt_official"] is not False:
                failures.append(f"{slot}:qualification-receipt-not-synthetic")
        except Exception as exc:
            failures.append(f"{slot}:branch-check:{type(exc).__name__}:{exc}")
    checks["branches"] = branch_results

    reconciliation_path = root / "phase5_5/forensics/historical_closure_v2/historical_orphan_reconciliation.json"
    reconciliation = json.loads(reconciliation_path.read_text(encoding="utf-8"))
    checks["historical_closure"] = reconciliation
    if reconciliation.get("reconciliation_pass") is not True or reconciliation.get("index_hash_mismatch_count") != 0:
        failures.append("historical-closure-failed")

    canary_path = root / "phase5_5/qualification/qualification_canary.json"
    canary = json.loads(canary_path.read_text(encoding="utf-8"))
    checks["synthetic_canary"] = {"pass": canary.get("pass"), "model_count": len(canary.get("records", []))}
    if canary.get("pass") is not True or len(canary.get("records", [])) != 4:
        failures.append("synthetic-canary-failed")

    cuda_available = False
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
    except Exception as exc:
        checks["cuda_error"] = f"{type(exc).__name__}: {exc}"
    checks["cuda_available"] = cuda_available
    checks["nvidia_smi_available"] = shutil.which("nvidia-smi") is not None
    if not cuda_available:
        failures.append("cuda-unavailable")

    policy = json.loads((root / "phase5_5/configs/evidence_policy.json").read_text(encoding="utf-8"))
    official_dispatch_enabled = policy.get("official_dispatch_enabled") is True
    checks["evidence_policy"] = {
        "official_dispatch_enabled": official_dispatch_enabled,
        "publication_evidence": policy.get("synthetic_evidence_counts_toward_publication") is False,
    }
    if not official_dispatch_enabled:
        failures.append("official-dispatch-disabled")
    checks["ready_for_official_authorization"] = not failures
    report = {
        "artifact": "phase5_5_official_execution_preflight",
        "source_commit": freeze.get("source_commit"),
        "checks": checks,
        "failures": failures,
        "pass": not failures,
        "official_evidence_created": False,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"pass": report["pass"], "failure_count": len(failures), "output": args.output.as_posix()}))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
