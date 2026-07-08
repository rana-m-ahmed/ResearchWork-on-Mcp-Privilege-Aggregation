"""Safe GitHub checkpoint synchronization for Phase 5."""

from __future__ import annotations

from .credential_scope import GitCredentialLease, credential_env_present, redact_sensitive_text
from .github_checkpoint import (
    ReverifyResult,
    SyncManifest,
    SyncReceipt,
    SyncTransactionError,
    perform_session_reverify,
    perform_sync_github,
)
from .path_allowlist import SyncAllowlist, load_sync_allowlist, validate_staged_paths

__all__ = [
    "GitCredentialLease",
    "ReverifyResult",
    "SyncAllowlist",
    "SyncManifest",
    "SyncReceipt",
    "SyncTransactionError",
    "credential_env_present",
    "load_sync_allowlist",
    "perform_session_reverify",
    "perform_sync_github",
    "redact_sensitive_text",
    "validate_staged_paths",
]
