from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from phase5.domain import Phase5Session, SessionState
from phase5.domain.errors import FrozenArtifactHashError, SessionTransitionError, SyncSafetyError
from phase5.sync.credential_scope import GitCredentialLease, credential_env_present, redact_sensitive_text
from phase5.sync.github_checkpoint import perform_session_reverify, perform_sync_github
from phase5.sync.path_allowlist import load_sync_allowlist, validate_staged_paths


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def _run_git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = _git(repo, *args, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _init_git_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    _run_git(tmp_path, "init", "--bare", remote.as_posix())
    _run_git(tmp_path, "init", repo.as_posix())
    _run_git(repo, "config", "user.name", "Phase 5 Sync")
    _run_git(repo, "config", "user.email", "phase5-sync@example.invalid")
    _run_git(repo, "remote", "add", "origin", remote.as_posix())

    (repo / "phase5" / "implementation" / "reports").mkdir(parents=True, exist_ok=True)
    (repo / "phase5" / "configs").mkdir(parents=True, exist_ok=True)
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v1\"}\n",
        encoding="utf-8",
    )
    (repo / "phase5" / "configs" / "runtime.json").write_text("{\"runtime\":\"ok\"}\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    _run_git(repo, "branch", "-M", "evidence")
    _run_git(repo, "push", "-u", "origin", "evidence")
    _run_git(tmp_path, "--git-dir", remote.as_posix(), "symbolic-ref", "HEAD", "refs/heads/evidence")
    initial_sha = _run_git(repo, "rev-parse", "HEAD")
    return repo, remote, initial_sha


def _write_sync_allowlist(path: Path) -> None:
    path.write_text(
        "allowed_staged_prefixes:\n"
        "  - phase5/implementation/reports/\n"
        "  - phase5/checkpoints/\n"
        "  - phase5/evidence/\n"
        "  - phase5/manifests/\n",
        encoding="utf-8",
    )


def _write_sync_manifest(repo: Path, *, source_commit: str, remote_head: str, manifest_path: Path) -> None:
    artifact_path = Path("phase5/implementation/reports/artifact.json")
    runtime_path = Path("phase5/configs/runtime.json")
    manifest = {
        "run_id": "run-001",
        "batch_id": "batch-001",
        "remote_name": "origin",
        "branch": "evidence",
        "commit_utc": "2026-07-08T00:00:00Z",
        "source_commit": source_commit,
        "common_source_hash": "a" * 64,
        "expected_remote_head_before_push": remote_head,
        "runtime_config_path": runtime_path.as_posix(),
        "runtime_config_sha256": _sha256(repo / runtime_path),
        "frozen_hashes": {
            artifact_path.as_posix(): _sha256(repo / artifact_path),
        },
        "allowed_staged_prefixes": [
            "phase5/implementation/reports/",
            "phase5/checkpoints/",
            "phase5/evidence/",
            "phase5/manifests/",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")


def _write_pre_receive_hook(remote: Path) -> None:
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")


def _write_post_receive_reset_hook(remote: Path, branch: str, sha: str) -> None:
    hook = remote / "hooks" / "post-receive"
    hook.write_text(
        "#!/bin/sh\n"
        f"git update-ref refs/heads/{branch} {sha}\n",
        encoding="utf-8",
    )


def test_sync_allowlist_blocks_source_paths() -> None:
    allowlist = load_sync_allowlist(Path("phase5/configs/sync_allowlist.yaml"))
    assert validate_staged_paths(["phase5/implementation/reports/a.json"], allowlist) == []
    assert validate_staged_paths(["src/main.py"], allowlist) == ["src/main.py"]


def test_credential_lease_redacts_and_purges_environment() -> None:
    env = {"GITHUB_TOKEN": "token-123", "GIT_TERMINAL_PROMPT": "1"}
    assert credential_env_present(env) is True

    lease = GitCredentialLease.acquire(env)
    lease.export_env(env)
    redacted = redact_sensitive_text("token-123 was present", ("token-123",))
    assert redacted == "[REDACTED] was present"

    lease.purge(env)
    assert credential_env_present(env) is False
    assert lease.purged is True


def test_sync_github_rejects_sealed_session(tmp_path: Path) -> None:
    repo, _remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_allowlist(allowlist_path)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)

    with pytest.raises(SessionTransitionError):
        perform_sync_github(
            session=Phase5Session.initial().seal(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            env={"GITHUB_TOKEN": "token-123"},
        )


def test_sync_github_rejects_live_trial_process(tmp_path: Path) -> None:
    repo, _remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_allowlist(allowlist_path)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)

    with pytest.raises(SyncSafetyError):
        perform_sync_github(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            trial_process_running=True,
            env={"GITHUB_TOKEN": "token-123"},
        )


def test_sync_github_rejects_source_path_staging(tmp_path: Path) -> None:
    repo, _remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    _write_sync_allowlist(allowlist_path)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)
    (repo / "src").mkdir(parents=True, exist_ok=True)
    (repo / "src" / "source.py").write_text("print('drift')\n", encoding="utf-8")

    with pytest.raises(SyncSafetyError):
        perform_sync_github(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            env={"GITHUB_TOKEN": "token-123"},
        )


def test_sync_github_rejects_remote_divergence(tmp_path: Path) -> None:
    repo, remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    _write_sync_allowlist(allowlist_path)

    drift_repo = tmp_path / "drift"
    _run_git(tmp_path, "clone", "--branch", "evidence", remote.as_posix(), drift_repo.as_posix())
    _run_git(drift_repo, "config", "user.name", "Phase 5 Drift")
    _run_git(drift_repo, "config", "user.email", "phase5-drift@example.invalid")
    (drift_repo / "phase5" / "implementation" / "reports").mkdir(parents=True, exist_ok=True)
    (drift_repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"remote-drift\"}\n",
        encoding="utf-8",
    )
    _run_git(drift_repo, "add", ".")
    _run_git(drift_repo, "commit", "-m", "remote drift")
    _run_git(drift_repo, "push", "origin", "HEAD:evidence")

    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)

    with pytest.raises(SyncSafetyError):
        perform_sync_github(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            env={"GITHUB_TOKEN": "token-123"},
        )


def test_sync_github_rejects_push_failure(tmp_path: Path) -> None:
    repo, remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    _write_sync_allowlist(allowlist_path)
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_pre_receive_hook(remote)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)

    with pytest.raises(SyncSafetyError):
        perform_sync_github(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            env={"GITHUB_TOKEN": "token-123"},
        )


def test_sync_github_detects_remote_sha_mismatch_and_cleans_credentials(tmp_path: Path) -> None:
    repo, remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    _write_sync_allowlist(allowlist_path)
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_post_receive_reset_hook(remote, "evidence", initial_sha)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)
    env = {"GITHUB_TOKEN": "token-123"}

    with pytest.raises(FrozenArtifactHashError):
        perform_sync_github(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            manifest_path=manifest_path,
            allowlist_path=allowlist_path,
            receipt_path=receipt_path,
            env=env,
        )

    assert credential_env_present(env) is False


def test_sync_github_success_writes_receipt_and_supports_reverify_and_reseal(tmp_path: Path) -> None:
    repo, _remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_allowlist(allowlist_path)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)
    env = {"GITHUB_TOKEN": "token-123"}

    session, receipt = perform_sync_github(
        session=Phase5Session.initial().seal().close_after_finalization(),
        repo=repo,
        manifest_path=manifest_path,
        allowlist_path=allowlist_path,
        receipt_path=receipt_path,
        env=env,
    )

    assert session.state is SessionState.UNSEALED_SYNCED
    assert receipt.credential_purged is True
    assert credential_env_present(env) is False
    assert receipt_path.is_file()
    written = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert written["credential_purged"] is True
    assert written["remote_head_after_push"] == written["local_commit_sha"]

    remote_head = _run_git(repo, "ls-remote", "origin", "evidence").split()[0]
    assert remote_head == receipt.local_commit_sha
    commit_line = _run_git(repo, "rev-list", "--parents", "-n", "1", receipt.local_commit_sha)
    assert initial_sha in commit_line

    reverified_session, reverify_result = perform_session_reverify(
        session=session,
        repo=repo,
        receipt_path=receipt_path,
        env=env,
    )
    assert reverified_session.state is SessionState.REVERIFIED_AFTER_SYNC
    assert reverify_result.credential_absent is True
    assert reverify_result.checkpoint_head == receipt.local_commit_sha
    assert reverify_result.source_commit == initial_sha

    resealed = reverified_session.seal()
    assert resealed.state is SessionState.SEALED
    assert resealed.seal_epoch == 2


def test_session_reverify_fails_before_sync_and_after_source_drift(tmp_path: Path) -> None:
    repo, _remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_allowlist(allowlist_path)
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)
    env = {"GITHUB_TOKEN": "token-123"}

    session, _receipt = perform_sync_github(
        session=Phase5Session.initial().seal().close_after_finalization(),
        repo=repo,
        manifest_path=manifest_path,
        allowlist_path=allowlist_path,
        receipt_path=receipt_path,
        env=env,
    )

    with pytest.raises(SessionTransitionError):
        perform_session_reverify(
            session=Phase5Session.initial().seal().close_after_finalization(),
            repo=repo,
            receipt_path=receipt_path,
            env={},
        )

    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v3\"}\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "phase5/implementation/reports/artifact.json")
    _run_git(repo, "commit", "-m", "source drift after sync")

    with pytest.raises(FrozenArtifactHashError):
        perform_session_reverify(
            session=session,
            repo=repo,
            receipt_path=receipt_path,
            env={},
        )
