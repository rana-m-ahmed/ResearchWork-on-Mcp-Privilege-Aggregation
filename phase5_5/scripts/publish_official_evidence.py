"""Append-only publisher for one bounded official model-branch run."""

from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


ALLOWED_ROOTS = ("phase5_5/attempts/", "phase5_5/evidence/")


def run_git(root: Path, args: list[str], *, env: dict[str, str], input_text: str | None = None) -> str:
    result = subprocess.run(["git", *args], cwd=root, env=env, input=input_text, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_auth_environment(token: str, base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    env["GIT_CONFIG_COUNT"] = "1"
    env["GIT_CONFIG_KEY_0"] = "http.extraHeader"
    credentials = base64.b64encode(f"x-access-token:{token}".encode("utf-8")).decode("ascii")
    env["GIT_CONFIG_VALUE_0"] = f"AUTHORIZATION: basic {credentials}"
    return env


def parse_porcelain_paths(raw: str) -> list[str]:
    """Parse porcelain-v1 output, including both sides of a rename."""
    paths: list[str] = []
    for record in raw.split("\0"):
        if not record:
            continue
        if len(record) < 4:
            raise RuntimeError(f"invalid git status record: {record!r}")
        paths.extend(part.replace("\\", "/") for part in record[3:].split("\t"))
    return paths


def status_paths(root: Path) -> list[str]:
    raw = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain=v1", "-z"], text=True)
    return parse_porcelain_paths(raw)


def _relative_under(root: Path, path: Path) -> str:
    expected = (root / "phase5_5/evidence/attempts").resolve()
    try:
        relative = path.resolve().relative_to(expected)
    except ValueError as exc:
        raise RuntimeError(f"evidence path escapes approved root: {path}") from exc
    return f"phase5_5/evidence/attempts/{relative.as_posix()}"


def _resolve_lineage_attempt(root: Path, raw: str) -> Path:
    """Relocate an absolute path from a prior checkout without widening scope."""
    evidence_attempts = (root / "phase5_5/evidence/attempts").resolve()
    candidate = Path(raw)
    if not candidate.is_absolute() and not raw.startswith("/"):
        return (root / candidate).resolve()
    try:
        candidate.resolve().relative_to(evidence_attempts)
        return candidate.resolve()
    except ValueError:
        pass

    parts = candidate.as_posix().split("/")
    marker = ("phase5_5", "evidence", "attempts")
    marker_start = next(
        (index for index in range(len(parts) - len(marker) + 1) if tuple(parts[index:index + len(marker)]) == marker),
        None,
    )
    if marker_start is None:
        raise RuntimeError("lineage raw_attempt_directory is outside phase5_5 evidence")
    suffix = parts[marker_start + len(marker):]
    if not suffix or any(part in {"", ".", ".."} for part in suffix):
        raise RuntimeError("lineage raw_attempt_directory is not canonical")
    return (evidence_attempts.joinpath(*suffix)).resolve()


def run_evidence_files(root: Path, run_id: str) -> list[str]:
    """Reconcile evidence for a run even when checkpoint commits made the tree clean."""
    lineage = root / "phase5_5/evidence/lineage.csv"
    if not lineage.is_file():
        raise RuntimeError("official execution produced no lineage evidence")
    with lineage.open("r", encoding="utf-8", newline="") as handle:
        matching = [row for row in csv.DictReader(handle) if row.get("run_id") == run_id]
    if not matching:
        raise RuntimeError(f"official execution produced no lineage rows for run {run_id}")

    files: set[str] = {"phase5_5/evidence/lineage.csv"}
    evidence_attempts = (root / "phase5_5/evidence/attempts").resolve()
    for row in matching:
        raw = row.get("raw_attempt_directory", "")
        if not raw:
            raise RuntimeError("lineage row is missing raw_attempt_directory")
        attempt_dir = _resolve_lineage_attempt(root, raw)
        try:
            attempt_dir.relative_to(evidence_attempts)
        except ValueError as exc:
            raise RuntimeError("lineage raw_attempt_directory is outside phase5_5 evidence") from exc
        if not attempt_dir.is_dir():
            raise RuntimeError(f"lineage attempt directory is missing: {attempt_dir}")
        attempt_files = sorted(path for path in attempt_dir.rglob("*") if path.is_file())
        if not attempt_files:
            raise RuntimeError(f"lineage attempt directory is empty: {attempt_dir}")
        files.update(_relative_under(root, path) for path in attempt_files)
    return sorted(files)


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
    if Path(args.run_id).name != args.run_id or any(separator in args.run_id for separator in ("/", "\\")):
        raise RuntimeError("run ID is not safe for an evidence publication path")
    branch = f"phase5_5-model-{slot.removeprefix('M')}"
    token_name = "PHASE5_GITHUB_TOKEN"
    token = os.environ.get(token_name)
    if not token:
        raise RuntimeError(f"missing Kaggle secret environment variable {token_name}")
    env = os.environ.copy()
    if run_git(root, ["rev-parse", "HEAD"], env=env) != args.expected_parent:
        raise RuntimeError("official evidence parent head does not match the authorized branch head")
    rejected = [path for path in status_paths(root) if not path.startswith(ALLOWED_ROOTS)]
    if rejected:
        raise RuntimeError(f"refusing to publish non-evidence paths: {rejected}")

    files = run_evidence_files(root, args.run_id)
    manifest = {
        "artifact": "phase5_5_official_evidence_publication_v1",
        "model_slot": slot,
        "branch": branch,
        "run_id": args.run_id,
        "parent_head": args.expected_parent,
        "published_utc": datetime.now(timezone.utc).isoformat(),
        "files": [{"path": path, "sha256": sha256(root / path), "bytes": (root / path).stat().st_size} for path in files],
    }
    publication_root = root / "phase5_5/evidence/publications" / args.run_id
    publication_root.mkdir(parents=True, exist_ok=True)
    manifest_path = publication_root / "official_publication_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_relative = manifest_path.relative_to(root).as_posix()

    env = git_auth_environment(token, env)
    try:
        # NUL-delimited pathspec input keeps argv bounded and prevents unrelated
        # evidence from being staged when checkpointed runs share a checkout.
        stage_paths = [*files, manifest_relative]
        run_git(root, ["add", "--pathspec-from-file=-", "--pathspec-file-nul"], env=env, input_text="\0".join(stage_paths) + "\0")
        run_git(root, ["-c", "user.name=phase5.5-sync", "-c", "user.email=phase5.5-sync@example.invalid", "commit", "-m", f"phase5.5 official evidence {slot} {args.run_id}"], env=env)
        first_commit = run_git(root, ["rev-parse", "HEAD"], env=env)
        remote_before = run_git(root, ["ls-remote", "origin", branch], env=env).split()[0]
        if remote_before != args.expected_parent:
            raise RuntimeError(f"remote branch diverged: expected {args.expected_parent}, got {remote_before}")
        run_git(root, ["push", "origin", f"HEAD:{branch}"], env=env)
        receipt = {"artifact": "phase5_5_official_evidence_publication_receipt_v1", "model_slot": slot, "branch": branch, "run_id": args.run_id, "expected_parent": args.expected_parent, "publication_commit": first_commit, "remote_head_after_push": first_commit, "published_utc": datetime.now(timezone.utc).isoformat(), "credential_purged": False}
        receipt_path = publication_root / "official_publication_receipt.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        receipt_relative = receipt_path.relative_to(root).as_posix()
        run_git(root, ["add", "--", receipt_relative], env=env)
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
        os.environ.pop(token_name, None)


if __name__ == "__main__":
    raise SystemExit(main())
