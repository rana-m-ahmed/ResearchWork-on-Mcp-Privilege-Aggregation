"""Sync receipt records for GitHub checkpoint synchronization."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_bool(value: Any, field: str) -> bool:
    if not isinstance(value, bool):
        raise SchemaInvariantError(f"{field} must be a boolean")
    return value


def _require_mapping(value: Any, field: str) -> dict[str, str]:
    if not isinstance(value, dict):
        raise SchemaInvariantError(f"{field} must be a mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key.strip():
            raise SchemaInvariantError(f"{field} keys must be non-empty strings")
        result[key] = _require_string(item, f"{field}[{key}]")
    return result


def _require_list(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise SchemaInvariantError(f"{field} must be a list")
    return tuple(_require_string(item, f"{field}[]") for item in value)


def _sha256_string(value: str, field: str) -> str:
    if len(value) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SchemaInvariantError(f"{field} must be a sha256 hex digest")
    return value.lower()


def _git_sha_string(value: str, field: str) -> str:
    if len(value) not in {40, 64} or any(ch not in "0123456789abcdefABCDEF" for ch in value):
        raise SchemaInvariantError(f"{field} must be a git SHA hex digest")
    return value.lower()


@dataclass(frozen=True, slots=True)
class SyncManifest:
    run_id: str
    batch_id: str
    remote_name: str
    branch: str
    commit_utc: str
    source_commit: str
    common_source_hash: str
    expected_remote_head_before_push: str
    runtime_config_path: str
    runtime_config_sha256: str
    frozen_hashes: Mapping[str, str]
    allowed_staged_prefixes: tuple[str, ...]

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "SyncManifest":
        required = (
            "run_id",
            "batch_id",
            "remote_name",
            "branch",
            "commit_utc",
            "source_commit",
            "common_source_hash",
            "expected_remote_head_before_push",
            "runtime_config_path",
            "runtime_config_sha256",
            "frozen_hashes",
            "allowed_staged_prefixes",
        )
        missing = [item for item in required if item not in mapping]
        if missing:
            raise MissingFrozenSettingError(f"sync manifest is missing required fields: {missing}")

        return cls(
            run_id=_require_string(mapping["run_id"], "run_id"),
            batch_id=_require_string(mapping["batch_id"], "batch_id"),
            remote_name=_require_string(mapping["remote_name"], "remote_name"),
            branch=_require_string(mapping["branch"], "branch"),
            commit_utc=_require_string(mapping["commit_utc"], "commit_utc"),
            source_commit=_git_sha_string(_require_string(mapping["source_commit"], "source_commit"), "source_commit"),
            common_source_hash=_sha256_string(
                _require_string(mapping["common_source_hash"], "common_source_hash"), "common_source_hash"
            ),
            expected_remote_head_before_push=_git_sha_string(
                _require_string(mapping["expected_remote_head_before_push"], "expected_remote_head_before_push"),
                "expected_remote_head_before_push",
            ),
            runtime_config_path=_require_string(mapping["runtime_config_path"], "runtime_config_path"),
            runtime_config_sha256=_sha256_string(
                _require_string(mapping["runtime_config_sha256"], "runtime_config_sha256"),
                "runtime_config_sha256",
            ),
            frozen_hashes=_require_mapping(mapping["frozen_hashes"], "frozen_hashes"),
            allowed_staged_prefixes=_require_list(mapping["allowed_staged_prefixes"], "allowed_staged_prefixes"),
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "allowed_staged_prefixes": list(self.allowed_staged_prefixes),
            "batch_id": self.batch_id,
            "branch": self.branch,
            "common_source_hash": self.common_source_hash,
            "commit_utc": self.commit_utc,
            "expected_remote_head_before_push": self.expected_remote_head_before_push,
            "frozen_hashes": dict(self.frozen_hashes),
            "remote_name": self.remote_name,
            "run_id": self.run_id,
            "runtime_config_path": self.runtime_config_path,
            "runtime_config_sha256": self.runtime_config_sha256,
            "source_commit": self.source_commit,
        }


@dataclass(frozen=True, slots=True)
class SyncReceipt:
    run_id: str
    batch_id: str
    remote_name: str
    branch: str
    commit_utc: str
    source_commit: str
    common_source_hash: str
    expected_remote_head_before_push: str
    remote_head_after_push: str
    local_commit_sha: str
    runtime_config_path: str
    runtime_config_sha256: str
    frozen_hashes: Mapping[str, str]
    allowed_staged_prefixes: tuple[str, ...]
    staged_paths: tuple[str, ...]
    session_state_before: str
    session_state_after: str
    credential_purged: bool

    def to_mapping(self) -> dict[str, Any]:
        return {
            "allowed_staged_prefixes": list(self.allowed_staged_prefixes),
            "batch_id": self.batch_id,
            "branch": self.branch,
            "commit_utc": self.commit_utc,
            "common_source_hash": self.common_source_hash,
            "credential_purged": self.credential_purged,
            "expected_remote_head_before_push": self.expected_remote_head_before_push,
            "frozen_hashes": dict(self.frozen_hashes),
            "local_commit_sha": self.local_commit_sha,
            "remote_head_after_push": self.remote_head_after_push,
            "remote_name": self.remote_name,
            "run_id": self.run_id,
            "runtime_config_path": self.runtime_config_path,
            "runtime_config_sha256": self.runtime_config_sha256,
            "session_state_after": self.session_state_after,
            "session_state_before": self.session_state_before,
            "source_commit": self.source_commit,
            "staged_paths": list(self.staged_paths),
        }

    def write_json(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_mapping(), sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "SyncReceipt":
        required = (
            "allowed_staged_prefixes",
            "batch_id",
            "branch",
            "commit_utc",
            "common_source_hash",
            "credential_purged",
            "expected_remote_head_before_push",
            "frozen_hashes",
            "local_commit_sha",
            "remote_head_after_push",
            "remote_name",
            "run_id",
            "runtime_config_path",
            "runtime_config_sha256",
            "session_state_after",
            "session_state_before",
            "source_commit",
            "staged_paths",
        )
        missing = [item for item in required if item not in mapping]
        if missing:
            raise MissingFrozenSettingError(f"sync receipt is missing required fields: {missing}")

        return cls(
            allowed_staged_prefixes=_require_list(mapping["allowed_staged_prefixes"], "allowed_staged_prefixes"),
            batch_id=_require_string(mapping["batch_id"], "batch_id"),
            branch=_require_string(mapping["branch"], "branch"),
            commit_utc=_require_string(mapping["commit_utc"], "commit_utc"),
            common_source_hash=_sha256_string(
                _require_string(mapping["common_source_hash"], "common_source_hash"), "common_source_hash"
            ),
            credential_purged=_require_bool(mapping["credential_purged"], "credential_purged"),
            expected_remote_head_before_push=_git_sha_string(
                _require_string(mapping["expected_remote_head_before_push"], "expected_remote_head_before_push"),
                "expected_remote_head_before_push",
            ),
            frozen_hashes=_require_mapping(mapping["frozen_hashes"], "frozen_hashes"),
            local_commit_sha=_git_sha_string(_require_string(mapping["local_commit_sha"], "local_commit_sha"), "local_commit_sha"),
            remote_head_after_push=_git_sha_string(
                _require_string(mapping["remote_head_after_push"], "remote_head_after_push"), "remote_head_after_push"
            ),
            remote_name=_require_string(mapping["remote_name"], "remote_name"),
            run_id=_require_string(mapping["run_id"], "run_id"),
            runtime_config_path=_require_string(mapping["runtime_config_path"], "runtime_config_path"),
            runtime_config_sha256=_sha256_string(
                _require_string(mapping["runtime_config_sha256"], "runtime_config_sha256"),
                "runtime_config_sha256",
            ),
            session_state_after=_require_string(mapping["session_state_after"], "session_state_after"),
            session_state_before=_require_string(mapping["session_state_before"], "session_state_before"),
            source_commit=_git_sha_string(_require_string(mapping["source_commit"], "source_commit"), "source_commit"),
            staged_paths=_require_list(mapping["staged_paths"], "staged_paths"),
        )
