"""Safe GitHub checkpoint synchronization for Phase 5."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping, Sequence

from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SessionTransitionError, SyncSafetyError
from ..domain.session import Phase5Session
from ..domain.enums import SessionState
from .credential_scope import GitCredentialLease, credential_env_present
from .path_allowlist import load_sync_allowlist, validate_staged_paths
from .sync_receipt import SyncManifest, SyncReceipt


class SyncTransactionError(SyncSafetyError):
    """A GitHub sync transaction failed closed."""


def _file_sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run_git(
    args: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        check=False,
    )
    if check and result.returncode != 0:
        raise SyncTransactionError(
            f"git {' '.join(args)} failed with exit code {result.returncode}: {result.stderr.strip()}"
        )
    return result


def _git_output(args: Sequence[str], *, cwd: Path, env: Mapping[str, str] | None = None) -> str:
    return _run_git(args, cwd=cwd, env=env).stdout.strip()


def _git_remote_head(repo: Path, remote: str, branch: str, *, env: Mapping[str, str] | None = None) -> str:
    result = _run_git(["ls-remote", remote, branch], cwd=repo, env=env)
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return ""
    head = lines[0].split()[0]
    if not head:
        raise SyncTransactionError(f"remote head lookup returned an empty SHA for {remote}/{branch}")
    return head.strip()


def _load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise MissingFrozenSettingError(f"sync manifest is missing: {path.as_posix()}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SyncTransactionError("sync manifest must be a JSON object")
    return data


def _load_strings_from_status(repo: Path) -> list[str]:
    status = _run_git(["status", "--porcelain"], cwd=repo)
    paths: list[str] = []
    for line in status.stdout.splitlines():
        if not line.strip():
            continue
        candidate = line[3:] if len(line) > 3 else line
        candidate = candidate.strip()
        if candidate.startswith('"') and candidate.endswith('"'):
            candidate = candidate[1:-1]
        paths.append(Path(candidate).as_posix())
    return paths


def _normalise_sha(value: str, field: str) -> str:
    value = value.strip()
    if len(value) not in {40, 64} or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SyncTransactionError(f"{field} must be a git SHA hex digest")
    return value.lower()


def _validate_runtime_hash(path: Path, expected_sha256: str) -> str:
    if not path.is_file():
        raise MissingFrozenSettingError(f"runtime config is missing: {path.as_posix()}")
    actual = _file_sha256(path)
    if actual.lower() != expected_sha256.lower():
        raise FrozenArtifactHashError(
            f"runtime config hash mismatch for {path.as_posix()}: expected {expected_sha256}, got {actual}"
        )
    return actual


def _validate_frozen_hashes(repo: Path, mapping: Mapping[str, str]) -> dict[str, str]:
    verified: dict[str, str] = {}
    for relative_path, expected_sha256 in mapping.items():
        path = repo / Path(relative_path)
        if not path.is_file():
            raise MissingFrozenSettingError(f"required frozen file is missing: {Path(relative_path).as_posix()}")
        actual = _file_sha256(path)
        if actual.lower() != expected_sha256.lower():
            raise FrozenArtifactHashError(
                f"frozen hash mismatch for {Path(relative_path).as_posix()}: expected {expected_sha256}, got {actual}"
            )
        verified[Path(relative_path).as_posix()] = actual
    return verified


def _validate_no_credentials(env: Mapping[str, str]) -> None:
    if credential_env_present(env):
        raise SyncSafetyError("Git write credential must not be present outside the sync credential scope")


def _sync_commit_message(manifest: SyncManifest) -> str:
    return f"phase5-checkpoint({manifest.branch}): {manifest.run_id} {manifest.batch_id}"


def _commit_with_deterministic_metadata(repo: Path, manifest: SyncManifest, env: MutableMapping[str, str]) -> str:
    env.update(
        {
            "GIT_AUTHOR_NAME": "phase5-sync",
            "GIT_AUTHOR_EMAIL": "phase5-sync@example.invalid",
            "GIT_COMMITTER_NAME": "phase5-sync",
            "GIT_COMMITTER_EMAIL": "phase5-sync@example.invalid",
            "GIT_AUTHOR_DATE": manifest.commit_utc,
            "GIT_COMMITTER_DATE": manifest.commit_utc,
        }
    )
    _run_git(["commit", "-m", _sync_commit_message(manifest)], cwd=repo, env=env)
    return _git_output(["rev-parse", "HEAD"], cwd=repo, env=env)


def _configure_ephemeral_credential_scope(env: MutableMapping[str, str], lease: GitCredentialLease) -> None:
    lease.export_env(env)


def _write_receipt(path: Path, receipt: SyncReceipt) -> None:
    receipt.write_json(path)


@dataclass(frozen=True, slots=True)
class ReverifyResult:
    session: Phase5Session
    source_commit: str
    common_source_hash: str
    runtime_config_sha256: str
    checkpoint_head: str
    frozen_hashes: Mapping[str, str]
    credential_absent: bool


def perform_sync_github(
    *,
    session: Phase5Session,
    repo: Path,
    manifest_path: Path,
    allowlist_path: Path,
    receipt_path: Path,
    trial_process_running: bool = False,
    env: MutableMapping[str, str] | None = None,
    credential_env_name: str = "GITHUB_TOKEN",
) -> tuple[Phase5Session, SyncReceipt]:
    if session.state is not SessionState.CLOSED_AFTER_FINALIZATION:
        raise SessionTransitionError(f"sync-github requires CLOSED_AFTER_FINALIZATION, not {session.state.value}")
    if not repo.is_dir():
        raise MissingFrozenSettingError(f"repository path is missing: {repo.as_posix()}")

    manifest = SyncManifest.from_mapping(_load_json(manifest_path))
    allowlist = load_sync_allowlist(allowlist_path)
    working_env: MutableMapping[str, str] = env if env is not None else os.environ

    syncing_session = session.begin_sync(trial_process_running=trial_process_running)

    if tuple(allowlist.allowed_staged_prefixes) != tuple(manifest.allowed_staged_prefixes):
        raise SyncSafetyError("sync manifest allowlist does not match the sync allowlist configuration")

    current_source_commit = _git_output(["rev-parse", "HEAD"], cwd=repo, env=working_env)
    if current_source_commit != manifest.source_commit:
        raise FrozenArtifactHashError("sync-github source commit does not match the manifest")
    _normalise_sha(manifest.source_commit, "source_commit")
    _normalise_sha(manifest.expected_remote_head_before_push, "expected_remote_head_before_push")

    _validate_runtime_hash(repo / manifest.runtime_config_path, manifest.runtime_config_sha256)
    _validate_frozen_hashes(repo, manifest.frozen_hashes)

    changed_paths = _load_strings_from_status(repo)
    rejected = validate_staged_paths(changed_paths, allowlist)
    if rejected:
        raise SyncSafetyError(f"sync-github refuses to stage non-allowlisted paths: {rejected}")
    if not changed_paths:
        raise SyncSafetyError("sync-github requires at least one allowlisted staged path")

    lease: GitCredentialLease | None = None
    lease = GitCredentialLease.acquire(working_env, token_env_name=credential_env_name)
    _configure_ephemeral_credential_scope(working_env, lease)

    credential_purged = False
    try:
        _run_git(["fetch", manifest.remote_name, manifest.branch], cwd=repo, env=working_env)
        remote_head_before = _git_remote_head(repo, manifest.remote_name, manifest.branch, env=working_env)
        if remote_head_before != manifest.expected_remote_head_before_push:
            raise SyncTransactionError(
                "remote head diverged before sync: "
                f"expected {manifest.expected_remote_head_before_push}, got {remote_head_before}"
            )

        _run_git(["add", "--", *changed_paths], cwd=repo, env=working_env)
        local_commit = _commit_with_deterministic_metadata(repo, manifest, dict(working_env))
        _run_git(["push", manifest.remote_name, f"HEAD:{manifest.branch}"], cwd=repo, env=working_env)
        remote_head_after = _git_remote_head(repo, manifest.remote_name, manifest.branch, env=working_env)
        if remote_head_after != local_commit:
            raise FrozenArtifactHashError(
                f"remote SHA mismatch after push: expected {local_commit}, got {remote_head_after}"
            )

        receipt = SyncReceipt(
            run_id=manifest.run_id,
            batch_id=manifest.batch_id,
            remote_name=manifest.remote_name,
            branch=manifest.branch,
            commit_utc=manifest.commit_utc,
            source_commit=manifest.source_commit,
            common_source_hash=manifest.common_source_hash,
            expected_remote_head_before_push=manifest.expected_remote_head_before_push,
            remote_head_after_push=remote_head_after,
            local_commit_sha=local_commit,
            runtime_config_path=manifest.runtime_config_path,
            runtime_config_sha256=manifest.runtime_config_sha256,
            frozen_hashes=manifest.frozen_hashes,
            allowed_staged_prefixes=manifest.allowed_staged_prefixes,
            staged_paths=tuple(changed_paths),
            session_state_before=session.state.value,
            session_state_after=SessionState.UNSEALED_SYNCED.value,
            credential_purged=False,
        )
        if lease is not None:
            lease.purge(working_env)
        credential_purged = True
        receipt = SyncReceipt.from_mapping({**receipt.to_mapping(), "credential_purged": True})
        _write_receipt(receipt_path, receipt)
        syncing_session = syncing_session.finish_sync()
        _validate_no_credentials(working_env)
        if lease is not None:
            lease.ensure_purged(working_env)
        return syncing_session, receipt
    finally:
        if not credential_purged:
            if lease is not None:
                lease.purge(working_env)
        try:
            _run_git(["config", "--local", "--unset-all", "credential.helper"], cwd=repo, env=working_env, check=False)
        except Exception:  # pragma: no cover - best-effort cleanup
            pass


def perform_session_reverify(
    *,
    session: Phase5Session,
    repo: Path,
    receipt_path: Path,
    env: Mapping[str, str] | None = None,
) -> tuple[Phase5Session, ReverifyResult]:
    if not repo.is_dir():
        raise MissingFrozenSettingError(f"repository path is missing: {repo.as_posix()}")
    receipt = SyncReceipt.from_mapping(_load_json(receipt_path))
    working_env = env if env is not None else os.environ
    _validate_no_credentials(working_env)

    if session.state is not SessionState.UNSEALED_SYNCED:
        raise SessionTransitionError(
            f"session-reverify requires UNSEALED_SYNCED, not {session.state.value}"
        )

    current_head = _git_output(["rev-parse", "HEAD"], cwd=repo, env=working_env)
    if current_head != receipt.local_commit_sha:
        raise FrozenArtifactHashError(
            f"checkpoint head changed after sync: expected {receipt.local_commit_sha}, got {current_head}"
        )
    checkpoint_parent = _git_output(["rev-parse", f"{current_head}^"], cwd=repo, env=working_env)
    if checkpoint_parent != receipt.source_commit:
        raise FrozenArtifactHashError(
            f"source commit changed after sync: expected parent {receipt.source_commit}, got {checkpoint_parent}"
        )
    if receipt.remote_head_after_push != receipt.local_commit_sha:
        raise FrozenArtifactHashError("receipt remote SHA does not match the local checkpoint SHA")

    runtime_sha = _validate_runtime_hash(repo / receipt.runtime_config_path, receipt.runtime_config_sha256)
    frozen_hashes = _validate_frozen_hashes(repo, receipt.frozen_hashes)
    checkpoint_head = _git_remote_head(repo, receipt.remote_name, receipt.branch, env=working_env)
    if checkpoint_head != receipt.remote_head_after_push:
        raise FrozenArtifactHashError(
            f"checkpoint head changed after sync: expected {receipt.remote_head_after_push}, got {checkpoint_head}"
        )

    reverified = session.reverify_after_sync(hashes_match=True)
    return reverified, ReverifyResult(
        session=reverified,
        source_commit=receipt.source_commit,
        common_source_hash=receipt.common_source_hash,
        runtime_config_sha256=runtime_sha,
        checkpoint_head=checkpoint_head,
        frozen_hashes=frozen_hashes,
        credential_absent=not credential_env_present(working_env),
    )
