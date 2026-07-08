"""Ephemeral credential handling for safe GitHub synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, MutableMapping

from ..domain.errors import SyncSafetyError


GIT_CREDENTIAL_ENV_VARS = (
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "GIT_ASKPASS",
    "GIT_USERNAME",
    "GIT_PASSWORD",
)


def credential_env_present(env: Mapping[str, str]) -> bool:
    return any(env.get(name) for name in GIT_CREDENTIAL_ENV_VARS)


def redact_sensitive_text(text: str, secrets: tuple[str, ...]) -> str:
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


@dataclass(slots=True)
class GitCredentialLease:
    """In-memory credential lease that can be purged after a sync."""

    token_env_name: str
    token_value: str
    helper_env_name: str = "GIT_ASKPASS"
    helper_path: str | None = None
    purged: bool = False

    @classmethod
    def acquire(cls, env: Mapping[str, str], *, token_env_name: str = "GITHUB_TOKEN") -> "GitCredentialLease":
        token = env.get(token_env_name)
        if not token:
            raise SyncSafetyError(f"missing Git write credential in {token_env_name}")
        return cls(token_env_name=token_env_name, token_value=token)

    def export_env(self, env: MutableMapping[str, str]) -> None:
        env[self.token_env_name] = self.token_value
        env.setdefault("GIT_TERMINAL_PROMPT", "0")
        if self.helper_path:
            env[self.helper_env_name] = self.helper_path

    def purge(self, env: MutableMapping[str, str]) -> None:
        env.pop(self.token_env_name, None)
        env.pop(self.helper_env_name, None)
        env.pop("GIT_TERMINAL_PROMPT", None)
        env.pop("GIT_USERNAME", None)
        env.pop("GIT_PASSWORD", None)
        self.token_value = ""
        self.helper_path = None
        self.purged = True

    def ensure_purged(self, env: Mapping[str, str]) -> None:
        if env.get(self.token_env_name) or env.get(self.helper_env_name):
            raise SyncSafetyError("credential purge verification failed")
