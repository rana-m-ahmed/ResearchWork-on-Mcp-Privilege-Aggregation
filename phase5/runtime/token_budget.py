"""Exact token accounting and overflow classification for Phase 5 prompts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..domain.errors import (
    InfrastructureInvalidAttemptError,
    MissingFrozenSettingError,
    Phase5Error,
    SchemaInvariantError,
    TokenProtocolDefectError,
)
from ..guards import repo_root
from .model_backend_adapter import load_frozen_model_backend_identity
from .prompt_serialization import ConversationTurn, normalize_turns, render_turn_stream


DEFAULT_INPUT_TOKEN_LIMIT = 3584
DEFAULT_RESERVED_OUTPUT_TOKENS = 512
DEFAULT_TOTAL_TOKEN_LIMIT = DEFAULT_INPUT_TOKEN_LIMIT + DEFAULT_RESERVED_OUTPUT_TOKENS
FROZEN_MODEL_SLOT = "M1"
EXPECTED_TOKENIZER_IDENTITY = "Qwen/Qwen2.5-7B-Instruct"


class TokenizerIdentityMismatchError(TokenProtocolDefectError):
    """The loaded tokenizer is not the frozen tokenizer identity."""


class TokenizerLoadError(TokenProtocolDefectError):
    """The frozen tokenizer could not be loaded exactly."""


class TokenBudgetExceededError(TokenProtocolDefectError):
    """The compiled prompt exceeds the frozen model input budget."""


class InfrastructureOversizeError(InfrastructureInvalidAttemptError):
    """A tool or infrastructure result exceeded the frozen input budget."""


class OverflowClassification(str, Enum):
    INITIAL_FROZEN_PROMPT_OVERFLOW = "initial_frozen_prompt_overflow"
    EXPECTED_VALID_TOOL_RESULT_OVERFLOW = "expected_valid_tool_result_overflow"
    MODEL_CREATED_LOOP_OVERFLOW = "model_created_loop_overflow"
    INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT = "infrastructure_generated_oversized_result"


@dataclass(frozen=True, slots=True)
class TokenBudgetPolicy:
    input_limit: int = DEFAULT_INPUT_TOKEN_LIMIT
    reserved_output_tokens: int = DEFAULT_RESERVED_OUTPUT_TOKENS

    def __post_init__(self) -> None:
        if self.input_limit <= 0:
            raise SchemaInvariantError("input_limit must be positive")
        if self.reserved_output_tokens <= 0:
            raise SchemaInvariantError("reserved_output_tokens must be positive")

    @property
    def total_budget(self) -> int:
        return self.input_limit + self.reserved_output_tokens


@dataclass(frozen=True, slots=True)
class TextTokenCount:
    label: str
    token_count: int
    byte_length: int
    sha256: str
    source: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "byte_length": self.byte_length,
            "label": self.label,
            "sha256": self.sha256,
            "source": self.source,
            "token_count": self.token_count,
        }


@dataclass(frozen=True, slots=True)
class TurnTokenCount:
    turn_index: int
    role: str
    token_count: int
    byte_length: int
    sha256: str
    source: str
    turn_kind: str

    def to_mapping(self) -> dict[str, Any]:
        return {
            "byte_length": self.byte_length,
            "role": self.role,
            "sha256": self.sha256,
            "source": self.source,
            "token_count": self.token_count,
            "turn_index": self.turn_index,
            "turn_kind": self.turn_kind,
        }


@dataclass(frozen=True, slots=True)
class TokenBudgetDecision:
    allowed: bool
    classification: OverflowClassification | None
    input_tokens: int
    reserved_output_tokens: int
    limit: int
    total_budget: int
    over_by: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "classification": None if self.classification is None else self.classification.value,
            "input_tokens": self.input_tokens,
            "limit": self.limit,
            "over_by": self.over_by,
            "reserved_output_tokens": self.reserved_output_tokens,
            "total_budget": self.total_budget,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_frozen_tokenizer_identity(root: Path | None = None, *, model_slot: str | None = None) -> str:
    """Resolve the tokenizer from the same selected-model authority as the backend."""

    if model_slot is None:
        return load_frozen_model_backend_identity(root).tokenizer_identity
    return load_frozen_model_backend_identity(root, model_slot=model_slot).tokenizer_identity


def _tokenizer_name(tokenizer: Any) -> str | None:
    for attribute in ("name_or_path", "_name_or_path"):
        value = getattr(tokenizer, attribute, None)
        if isinstance(value, str) and value:
            return value
    init_kwargs = getattr(tokenizer, "init_kwargs", None)
    if isinstance(init_kwargs, Mapping):
        value = init_kwargs.get("name_or_path")
        if isinstance(value, str) and value:
            return value
    return None


def build_exact_tokenizer(
    *,
    root: Path | None = None,
    tokenizer_loader: Callable[..., Any] | None = None,
    local_files_only: bool = False,
    revision: str | None = None,
    model_slot: str | None = None,
) -> Any:
    """Load the exact frozen tokenizer or fail closed."""

    tokenizer_identity = (
        load_frozen_tokenizer_identity(root)
        if model_slot is None
        else load_frozen_tokenizer_identity(root, model_slot=model_slot)
    )
    try:
        if tokenizer_loader is None:
            try:
                from transformers import AutoTokenizer
            except Exception as exc:  # pragma: no cover - validated by failure tests
                raise TokenizerLoadError("transformers is required to load the frozen tokenizer") from exc
            tokenizer = AutoTokenizer.from_pretrained(
                tokenizer_identity,
                revision=revision,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
        else:
            tokenizer = tokenizer_loader(
                tokenizer_identity,
                revision=revision,
                trust_remote_code=True,
                local_files_only=local_files_only,
            )
    except Phase5Error:
        raise
    except Exception as exc:
        raise TokenizerLoadError(
            f"failed to load the frozen tokenizer {tokenizer_identity!r}"
            f" at revision {revision!r}: {type(exc).__name__}: {exc}"
        ) from exc

    loaded_name = _tokenizer_name(tokenizer)
    if loaded_name != tokenizer_identity:
        raise TokenizerIdentityMismatchError(
            f"loaded tokenizer identity mismatch: expected {tokenizer_identity!r}, got {loaded_name!r}"
        )
    return tokenizer


def _encode(tokenizer: Any, text: str) -> list[int]:
    try:
        encoded = tokenizer.encode(text, add_special_tokens=False)
    except TypeError:
        encoded = tokenizer.encode(text)
    if not isinstance(encoded, Sequence):
        raise SchemaInvariantError("tokenizer.encode must return a sequence")
    return list(encoded)


def count_tokens(tokenizer: Any, text: str) -> int:
    return len(_encode(tokenizer, text))


def summarize_text_token_count(tokenizer: Any, *, label: str, text: str, source: str) -> TextTokenCount:
    raw_bytes = text.encode("utf-8")
    return TextTokenCount(
        label=label,
        token_count=count_tokens(tokenizer, text),
        byte_length=len(raw_bytes),
        sha256=_sha256_bytes(raw_bytes),
        source=source,
    )


def summarize_turn_token_counts(
    tokenizer: Any,
    turns: Sequence[ConversationTurn | Mapping[str, Any]] | None,
    *,
    tool_result_template: str,
    source: str = "conversation_history",
) -> tuple[TurnTokenCount, ...]:
    normalized = normalize_turns(turns)
    if not normalized:
        return ()
    rendered_turns = render_turn_stream(normalized, tool_result_template=tool_result_template)
    summary: list[TurnTokenCount] = []
    for turn, rendered in zip(normalized, rendered_turns, strict=True):
        rendered_bytes = rendered.encode("utf-8")
        summary.append(
            TurnTokenCount(
                turn_index=turn.turn_index,
                role=turn.role,
                token_count=count_tokens(tokenizer, rendered),
                byte_length=len(rendered_bytes),
                sha256=_sha256_bytes(rendered_bytes),
                source=source,
                turn_kind=turn.turn_kind,
            )
        )
    return tuple(summary)


def classify_overflow(
    *,
    initial_prompt_overflow: bool = False,
    expected_valid_tool_result_overflow: bool = False,
    model_created_loop_overflow: bool = False,
    infrastructure_generated_oversized_result: bool = False,
) -> OverflowClassification:
    selected = [
        initial_prompt_overflow,
        expected_valid_tool_result_overflow,
        model_created_loop_overflow,
        infrastructure_generated_oversized_result,
    ]
    if sum(1 for item in selected if item) != 1:
        raise SchemaInvariantError("exactly one overflow classification flag must be set")
    if infrastructure_generated_oversized_result:
        return OverflowClassification.INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT
    if model_created_loop_overflow:
        return OverflowClassification.MODEL_CREATED_LOOP_OVERFLOW
    if expected_valid_tool_result_overflow:
        return OverflowClassification.EXPECTED_VALID_TOOL_RESULT_OVERFLOW
    return OverflowClassification.INITIAL_FROZEN_PROMPT_OVERFLOW


def enforce_token_budget(
    *,
    input_tokens: int,
    policy: TokenBudgetPolicy | None = None,
    classification: OverflowClassification | None = None,
) -> TokenBudgetDecision:
    current_policy = policy or TokenBudgetPolicy()
    if input_tokens < 0:
        raise SchemaInvariantError("input_tokens must be non-negative")

    over_by = max(0, input_tokens - current_policy.input_limit)
    if over_by == 0:
        return TokenBudgetDecision(
            allowed=True,
            classification=None,
            input_tokens=input_tokens,
            reserved_output_tokens=current_policy.reserved_output_tokens,
            limit=current_policy.input_limit,
            total_budget=current_policy.total_budget,
            over_by=0,
        )

    if classification is None:
        raise SchemaInvariantError("budget overflow requires an explicit classification")

    if classification is OverflowClassification.INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT:
        raise InfrastructureOversizeError(
            f"input budget exceeded by {over_by} tokens for infrastructure-generated result"
        )

    raise TokenBudgetExceededError(f"input budget exceeded by {over_by} tokens: {classification.value}")


def budget_decision_for_turn(
    *,
    input_tokens: int,
    policy: TokenBudgetPolicy | None = None,
    classification: OverflowClassification | None = None,
) -> TokenBudgetDecision:
    """Alias with a turn-oriented name for call sites that enforce per-turn budgets."""

    return enforce_token_budget(input_tokens=input_tokens, policy=policy, classification=classification)
