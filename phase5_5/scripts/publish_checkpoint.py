"""Publish one append-only Phase 5.5 evidence checkpoint."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_git(root: Path, args: list[str], *, env: dict[str, str], input_text: str | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=root, env=env, input=input_text, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def status_paths(root: Path) -> list[str]:
    status = subprocess.check_output(
        ["git", "-C", str(root), "status", "--porcelain=v1", "-z", "--untracked-files=all"], text=True
    )
    paths: list[str] = []
    for record in status.split("\0"):
        if not record:
            continue
        if len(record) < 4:
            raise RuntimeError(f"invalid git status record: {record!r}")
        paths.extend(part.replace("\\", "/") for part in record[3:].split("\t"))
    return paths


def validate_evidence_path(root: Path, relative: str) -> str:
    """Reject absolute, traversal, and symlink-escaping evidence paths."""
    normalized = Path(relative).as_posix()
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise RuntimeError(f"checkpoint path is not canonical: {relative}")
    evidence_root = (root / "phase5_5/evidence").resolve()
    candidate = (root / normalized).resolve()
    try:
        candidate.relative_to(evidence_root)
    except ValueError as exc:
        raise RuntimeError(f"checkpoint path escapes phase5_5/evidence: {relative}") from exc
    return normalized


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-slot", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--checkpoint-sequence", type=int, required=True)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--expected-parent", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root.resolve()
    slot = args.model_slot.upper()
    branch = f"phase5_5-model-{slot.removeprefix('M')}"
    token = os.environ.get("PHASE5_GITHUB_TOKEN")
    if not token:
        raise RuntimeError("missing Kaggle secret environment variable PHASE5_GITHUB_TOKEN")
    if args.checkpoint_sequence <= 0:
        raise RuntimeError("checkpoint sequence must be positive")

    expected_parent = args.expected_parent.strip()
    if run_git(root, ["rev-parse", "HEAD"], env=os.environ.copy()) != expected_parent:
        raise RuntimeError("local checkpoint parent does not match the expected branch head")

    checkpoint_relative = validate_evidence_path(root, args.checkpoint)
    checkpoint_path = root / checkpoint_relative
    if not checkpoint_path.is_file() or not checkpoint_relative.startswith("phase5_5/evidence/"):
        raise RuntimeError("checkpoint must be an existing Phase 5.5 evidence file")

    paths = status_paths(root)
    allowed = ("phase5_5/attempts/", "phase5_5/evidence/")
    rejected = [path for path in paths if not path.startswith(allowed)]
    if rejected:
        raise RuntimeError(f"checkpoint refuses to publish non-evidence paths: {rejected}")
    if checkpoint_relative not in paths:
        raise RuntimeError("checkpoint file is not a pending working-tree change")
    if not paths:
        raise RuntimeError("checkpoint has no evidence changes to publish")

    env = os.environ.copy()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
    basic_credentials = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {basic_credentials}"
    remote_before = run_git(root, ["ls-remote", "origin", branch], env=env).split()[0]
    if remote_before != expected_parent:
        raise RuntimeError(f"remote branch diverged: expected {expected_parent}, got {remote_before}")

    # Feed pathspecs over stdin so checkpoint size cannot hit the OS argv limit.
    run_git(
        root,
        ["add", "--pathspec-from-file=-", "--pathspec-file-nul"],
        env=env,
        input_text="\0".join(paths) + "\0",
    )
    run_git(
        root,
        [
            "-c",
            "user.name=phase5.5-checkpoint",
            "-c",
            "user.email=phase5.5-checkpoint@example.invalid",
            "commit",
            "-m",
            f"phase5.5 checkpoint {slot} {args.run_id} {args.checkpoint_sequence}",
        ],
        env=env,
    )
    publication_commit = run_git(root, ["rev-parse", "HEAD"], env=env)
    run_git(root, ["push", "origin", f"HEAD:{branch}"], env=env)
    remote_after = run_git(root, ["ls-remote", "origin", branch], env=env).split()[0]
    if remote_after != publication_commit:
        raise RuntimeError("remote checkpoint head did not match the local publication commit")

    receipt = {
        "artifact": "phase5_5_trial_checkpoint_receipt_v1",
        "branch": branch,
        "checkpoint": checkpoint_relative,
        "checkpoint_sha256": sha256(checkpoint_path),
        "checkpoint_sequence": args.checkpoint_sequence,
        "expected_parent": expected_parent,
        "model_slot": slot,
        "publication_commit": publication_commit,
        "published_utc": datetime.now(timezone.utc).isoformat(),
        "remote_head_after_push": remote_after,
        "run_id": args.run_id,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"checkpoint_sequence": args.checkpoint_sequence, "remote_head": remote_after}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
