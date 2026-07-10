"""Phase 5 error types and stable exit codes."""

from __future__ import annotations

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GATE0_FAILURE = 10
    FROZEN_ARTIFACT_HASH_FAILURE = 20
    RUNTIME_MISMATCH = 30
    TOKEN_PROTOCOL_DEFECT = 40
    INFRASTRUCTURE_INVALID_ATTEMPT = 50
    RESET_FAILURE = 60
    SCHEMA_INVARIANT_FAILURE = 70
    SYNC_SAFETY_FAILURE = 80
    NOT_IMPLEMENTED = 90


EXIT_CODE_REGISTRY = {item.name: int(item) for item in ExitCode}


class Phase5Error(Exception):
    """Base class for fail-closed Phase 5 errors."""

    exit_code = ExitCode.SCHEMA_INVARIANT_FAILURE

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.details = details


class FrozenArtifactHashError(Phase5Error):
    exit_code = ExitCode.FROZEN_ARTIFACT_HASH_FAILURE


class RuntimeMismatchError(Phase5Error):
    exit_code = ExitCode.RUNTIME_MISMATCH


class TokenProtocolDefectError(Phase5Error):
    exit_code = ExitCode.TOKEN_PROTOCOL_DEFECT


class InfrastructureInvalidAttemptError(Phase5Error):
    exit_code = ExitCode.INFRASTRUCTURE_INVALID_ATTEMPT


class ResetFailureError(Phase5Error):
    exit_code = ExitCode.RESET_FAILURE


class SchemaInvariantError(Phase5Error):
    exit_code = ExitCode.SCHEMA_INVARIANT_FAILURE


class OfficialDispatchBlockedError(SchemaInvariantError):
    """Official-capable dispatch was attempted without complete authorization."""


class SyncSafetyError(Phase5Error):
    exit_code = ExitCode.SYNC_SAFETY_FAILURE


class NotImplementedCommandError(Phase5Error):
    exit_code = ExitCode.NOT_IMPLEMENTED


class MissingFrozenSettingError(SchemaInvariantError):
    """A required frozen setting or path is absent or ambiguous."""


class ProhibitedAliasError(SchemaInvariantError):
    """A prohibited field alias was provided instead of the canonical name."""


class UnknownEnumValueError(SchemaInvariantError):
    """A value was not part of a frozen enum contract."""


class IdentifierValidationError(SchemaInvariantError):
    """An identifier did not match the frozen grammar."""


class DuplicateAcceptedAttemptError(SchemaInvariantError):
    """More than one accepted attempt was found for the same target row."""


class SessionTransitionError(SyncSafetyError):
    """A session transition was attempted in an invalid state."""
