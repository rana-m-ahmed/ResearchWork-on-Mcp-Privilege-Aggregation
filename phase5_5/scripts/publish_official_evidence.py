"""Append-only publisher for one bounded official model-branch run."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_git(root: Path, args: list[str], *, env: dict[str, str]) -> str:
    result = subprocess.run(["git", *args], cwd=root, env=env, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def status_paths(root: Path) -> list[str]:
    status = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True)
    paths = []
    for line in status.splitlines():
        if line.strip():
            paths.append(line[3:].strip().replace("\\", "/"))
    return paths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--model-slot", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--expected-parent", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    slot = args.model_slot.upper()
    branch = f"phase5_5-model-{slot.removeprefix('M')}"
    token_name = "PHASE5_GITHUB_TOKEN"
    token = os.environ.get(token_name)
    if not token:
        raise RuntimeError(f"missing Kaggle secret environment variable {token_name}")
    if run_git(root, ["rev-parse", "HEAD"], env=os.environ.copy()) != args.expected_parent:
        raise RuntimeError("official evidence parent head does not match the authorized branch head")
    paths = status_paths(root)
    allowed = ("phase5_5/attempts/", "phase5_5/evidence/")
    rejected = [path for path in paths if not path.startswith(allowed)]
    if rejected:
        raise RuntimeError(f"refusing to publish non-evidence paths: {rejected}")
    if not paths:
        raise RuntimeError("official execution produced no evidence paths")

    files = []
    for relative in sorted(paths):
        path = root / relative
        if path.is_file():
            files.append({"path": relative, "sha256": sha256(path), "bytes": path.stat().st_size})
    manifest = {
        "artifact": "phase5_5_official_evidence_publication_v1",
        "model_slot": slot,
        "branch": branch,
        "run_id": args.run_id,
        "parent_head": args.expected_parent,
        "published_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }
    manifest_path = root / "phase5_5/evidence" / "official_publication_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    env = os.environ.copy()
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: bearer {token}"
    try:
        remote_before = run_git(root, ["ls-remote", "origin", branch], env=env).split()[0]
        if remote_before != args.expected_parent:
            raise RuntimeError(f"remote branch diverged: expected {args.expected_parent}, got {remote_before}")
        run_git(root, ["add", "--", *paths, "phase5_5/evidence/official_publication_manifest.json"], env=env)
        run_git(root, ["-c", "user.name=phase5.5-sync", "-c", "user.email=phase5.5-sync@example.invalid", "commit", "-m", f"phase5.5 official evidence {slot} {args.run_id}"], env=env)
        first_commit = run_git(root, ["rev-parse", "HEAD"], env=env)
        run_git(root, ["push", "origin", f"HEAD:{branch}"], env=env)
        receipt = {
            "artifact": "phase5_5_official_evidence_publication_receipt_v1",
            "model_slot": slot,
            "branch": branch,
            "run_id": args.run_id,
            "expected_parent": args.expected_parent,
            "publication_commit": first_commit,
            "remote_head_after_push": first_commit,
            "published_utc": datetime.now(timezone.utc).isoformat(),
            "credential_purged": True,
        }
        receipt_path = root / "phase5_5/evidence" / "official_publication_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        run_git(root, ["add", "--", "phase5_5/evidence/official_publication_receipt.json"], env=env)
        run_git(root, ["-c", "user.name=phase5.5-sync", "-c", "user.email=phase5.5-sync@example.invalid", "commit", "-m", f"phase5.5 publication receipt {slot} {args.run_id}"], env=env)
        receipt_commit = run_git(root, ["rev-parse", "HEAD"], env=env)
        run_git(root, ["push", "origin", f"HEAD:{branch}"], env=env)
        receipt["receipt_commit"] = receipt_commit
        receipt["credential_purged"] = True
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps({"branch": branch, "publication_commit": first_commit, "receipt_commit": receipt_commit}))
        return 0
    finally:
        env.pop("GIT_CONFIG_VALUE_0", None)
        os.environ.pop(token_name, None)


if __name__ == "__main__":
    raise SystemExit(main())
