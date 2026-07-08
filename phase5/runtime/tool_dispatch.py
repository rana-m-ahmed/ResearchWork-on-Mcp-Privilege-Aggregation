"""Frozen tool dispatch helpers for Phase 5."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from time import monotonic
from typing import Any, Callable, Mapping, Sequence

from ..domain.errors import Phase5Error, SchemaInvariantError, TokenProtocolDefectError
from .parser_adapter import ParsedToolCall
from .prompt_serialization import ConversationTurn


class ToolDispatchError(Phase5Error):
    """Base class for frozen tool dispatch failures."""


class ForbiddenToolCallError(ToolDispatchError):
    """A forbidden tool was requested by the model."""


class UnknownToolCallError(ToolDispatchError):
    """A requested tool is not in the frozen tool catalog."""


class MissingToolParameterError(ToolDispatchError):
    """A requested tool call omitted a frozen required parameter."""


class ToolExecutionFailure(ToolDispatchError):
    """A tool handler raised or returned an unsupported result."""


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaInvariantError(f"{field_name} must be a non-empty string")
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:  # pragma: no cover - defensive
        raise ToolExecutionFailure("tool result is not JSON-serializable") from exc


def _serialize_tool_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    if isinstance(result, (dict, list, int, float, bool)) or result is None:
        return _canonical_json(result)
    if hasattr(result, "to_mapping"):
        return _canonical_json(result.to_mapping())
    raise ToolExecutionFailure(f"unsupported tool result type: {type(result).__name__}")


@dataclass(frozen=True, slots=True)
class ToolSpecification:
    """A frozen, serializable tool contract."""

    exposed_tool_name: str
    handler: Callable[[Mapping[str, Any]], Any]
    required_arguments: tuple[str, ...] = ()
    logical_tool_name: str | None = None

    def __post_init__(self) -> None:
        _require_string(self.exposed_tool_name, "exposed_tool_name")
        if self.logical_tool_name is not None:
            _require_string(self.logical_tool_name, "logical_tool_name")
        if not isinstance(self.required_arguments, tuple):
            raise SchemaInvariantError("required_arguments must be a tuple")
        for argument in self.required_arguments:
            _require_string(argument, "required_argument")

    @property
    def logical_name(self) -> str:
        return self.logical_tool_name or self.exposed_tool_name


@dataclass(frozen=True, slots=True)
class ToolDispatchPolicy:
    """Frozen dispatch controls consumed from the registry."""

    multiple_tool_call_policy: str
    tool_error_reinsertion_policy: str
    forbidden_tool_names: tuple[str, ...]
    max_total_tool_calls: int
    max_identical_consecutive_tool_calls: int
    max_identical_total_tool_calls: int

    def __post_init__(self) -> None:
        _require_string(self.multiple_tool_call_policy, "multiple_tool_call_policy")
        _require_string(self.tool_error_reinsertion_policy, "tool_error_reinsertion_policy")
        if self.max_total_tool_calls <= 0:
            raise SchemaInvariantError("max_total_tool_calls must be positive")
        if self.max_identical_consecutive_tool_calls <= 0:
            raise SchemaInvariantError("max_identical_consecutive_tool_calls must be positive")
        if self.max_identical_total_tool_calls <= 0:
            raise SchemaInvariantError("max_identical_total_tool_calls must be positive")
        if not isinstance(self.forbidden_tool_names, tuple):
            raise SchemaInvariantError("forbidden_tool_names must be a tuple")
        for name in self.forbidden_tool_names:
            _require_string(name, "forbidden_tool_name")


@dataclass(frozen=True, slots=True)
class ToolDispatchRecord:
    """A single dispatch record with both logical and exposed tool names."""

    call_index: int
    exposed_tool_name: str
    logical_tool_name: str
    tool_call_id: str | None
    arguments: Mapping[str, Any]
    result_text: str
    elapsed_seconds: float
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.call_index < 0:
            raise SchemaInvariantError("call_index must be non-negative")
        if self.elapsed_seconds < 0:
            raise SchemaInvariantError("elapsed_seconds must be non-negative")
        _require_string(self.exposed_tool_name, "exposed_tool_name")
        _require_string(self.logical_tool_name, "logical_tool_name")
        if not isinstance(self.arguments, Mapping):
            raise SchemaInvariantError("arguments must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise SchemaInvariantError("metadata must be a mapping")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "arguments": dict(self.arguments),
            "call_index": self.call_index,
            "elapsed_seconds": self.elapsed_seconds,
            "exposed_tool_name": self.exposed_tool_name,
            "logical_tool_name": self.logical_tool_name,
            "metadata": dict(self.metadata),
            "result_text": self.result_text,
            "tool_call_id": self.tool_call_id,
        }

    def to_conversation_turn(self, *, tool_result_serialization_version: str | None = None) -> ConversationTurn:
        metadata = dict(self.metadata)
        if tool_result_serialization_version is not None:
            metadata["tool_result_serialization_version"] = tool_result_serialization_version
        return ConversationTurn(
            turn_index=self.call_index,
            role="tool",
            content=self.result_text,
            turn_kind="tool_result",
            tool_name=self.exposed_tool_name,
            tool_call_id=self.tool_call_id,
            metadata=metadata,
        )


def dispatch_tool_calls(
    tool_calls: Sequence[ParsedToolCall],
    *,
    tool_catalog: Mapping[str, ToolSpecification],
    policy: ToolDispatchPolicy,
    tool_result_serialization_version: str | None = None,
    clock: Callable[[], float] = monotonic,
) -> tuple[ToolDispatchRecord, ...]:
    """Dispatch tool calls serially in parser order without repair or retries."""

    records: list[ToolDispatchRecord] = []
    for call in tool_calls:
        if call.tool_name in policy.forbidden_tool_names:
            raise ForbiddenToolCallError(f"forbidden tool requested: {call.tool_name!r}")
        try:
            specification = tool_catalog[call.tool_name]
        except KeyError as exc:
            raise UnknownToolCallError(f"unknown tool requested: {call.tool_name!r}") from exc

        missing = tuple(name for name in specification.required_arguments if name not in call.arguments)
        if missing:
            raise MissingToolParameterError(
                f"missing required parameter(s) for {call.tool_name!r}: {', '.join(missing)}"
            )

        start = clock()
        result = specification.handler(dict(call.arguments))
        elapsed = clock() - start
        if elapsed < 0:
            raise SchemaInvariantError("clock moved backwards during tool execution")
        records.append(
            ToolDispatchRecord(
                call_index=call.call_index,
                exposed_tool_name=call.tool_name,
                logical_tool_name=specification.logical_name,
                tool_call_id=call.tool_call_id,
                arguments=call.arguments,
                result_text=_serialize_tool_result(result),
                elapsed_seconds=elapsed,
                metadata={
                    "tool_error_reinsertion_policy": policy.tool_error_reinsertion_policy,
                    "tool_result_serialization_version": tool_result_serialization_version,
                },
            )
        )
    return tuple(records)

