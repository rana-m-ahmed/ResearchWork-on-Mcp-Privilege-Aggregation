"""Frozen parser adapter for Phase 5 model outputs."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..domain.errors import Phase5Error, SchemaInvariantError, TokenProtocolDefectError


class ModelOutputFailure(TokenProtocolDefectError):
    """Model output did not satisfy the frozen parser contract."""


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ModelOutputFailure(f"{field_name} must be a non-empty string")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field_name)


def _require_mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ModelOutputFailure(f"{field_name} must be a mapping")
    return value


def _require_sequence(value: Any, field_name: str) -> Sequence[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise ModelOutputFailure(f"{field_name} must be a sequence")
    return value


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    except TypeError as exc:  # pragma: no cover - defensive
        raise SchemaInvariantError("model output contains non-serializable values") from exc


@dataclass(frozen=True, slots=True)
class ParsedToolCall:
    """A single parsed tool call preserved in the original order."""

    call_index: int
    tool_name: str
    arguments: Mapping[str, Any]
    tool_call_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.call_index < 0:
            raise ModelOutputFailure("call_index must be non-negative")
        _require_string(self.tool_name, "tool_name")
        if not isinstance(self.arguments, Mapping):
            raise ModelOutputFailure("arguments must be a mapping")
        if not isinstance(self.metadata, Mapping):
            raise ModelOutputFailure("metadata must be a mapping")
        _require_optional_string(self.tool_call_id, "tool_call_id")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "arguments": dict(self.arguments),
            "call_index": self.call_index,
            "metadata": dict(self.metadata),
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
        }


@dataclass(frozen=True, slots=True)
class ParsedModelOutput:
    """Strictly parsed model output and any preserved metadata."""

    raw_text: str
    parser_version: str | None
    terminal_response: str | None
    tool_calls: tuple[ParsedToolCall, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _require_string(self.raw_text, "raw_text")
        if self.parser_version is not None:
            _require_string(self.parser_version, "parser_version")
        if not isinstance(self.metadata, Mapping):
            raise ModelOutputFailure("metadata must be a mapping")
        if not isinstance(self.payload, Mapping):
            raise ModelOutputFailure("payload must be a mapping")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "metadata": dict(self.metadata),
            "parser_version": self.parser_version,
            "payload": dict(self.payload),
            "raw_text": self.raw_text,
            "terminal_response": self.terminal_response,
            "tool_calls": [item.to_mapping() for item in self.tool_calls],
        }

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)

    @property
    def is_terminal(self) -> bool:
        return self.terminal_response is not None and not self.tool_calls


def _parse_raw_payload(raw_output: str | Mapping[str, Any]) -> tuple[str, Mapping[str, Any]]:
    if isinstance(raw_output, Mapping):
        payload = raw_output
        raw_text = raw_output.get("raw_text") if isinstance(raw_output.get("raw_text"), str) else _canonical_json(raw_output)
        return raw_text, payload

    if not isinstance(raw_output, str):
        raise ModelOutputFailure(f"model output must be raw text or a mapping, not {type(raw_output).__name__}")

    raw_text = raw_output
    try:
        payload = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        raise ModelOutputFailure("invalid JSON model output") from exc
    if not isinstance(payload, Mapping):
        raise ModelOutputFailure("model output must decode to a mapping")
    return raw_text, payload


def parse_model_output(
    raw_output: str | Mapping[str, Any],
    *,
    parser_version: str | None,
) -> ParsedModelOutput:
    """Parse model output without repair or heuristic rewriting."""

    raw_text, payload = _parse_raw_payload(raw_output)
    terminal_response = payload.get("terminal_response")
    if terminal_response is not None:
        terminal_response = _require_string(terminal_response, "terminal_response")

    metadata = payload.get("metadata", {})
    if metadata is None:
        metadata = {}
    metadata = _require_mapping(metadata, "metadata")

    tool_calls_value = payload.get("tool_calls", ())
    if tool_calls_value is None:
        tool_calls_value = ()
    tool_calls_raw = _require_sequence(tool_calls_value, "tool_calls")
    tool_calls: list[ParsedToolCall] = []
    for call_index, call_mapping in enumerate(tool_calls_raw):
        if not isinstance(call_mapping, Mapping):
            raise ModelOutputFailure("each tool call must be a mapping")
        tool_name = _require_string(call_mapping.get("tool_name"), "tool_name")
        arguments = _require_mapping(call_mapping.get("arguments"), "arguments")
        tool_call_id = _require_optional_string(call_mapping.get("tool_call_id"), "tool_call_id")
        call_metadata = call_mapping.get("metadata", {})
        if call_metadata is None:
            call_metadata = {}
        call_metadata = _require_mapping(call_metadata, "metadata")
        raw_call_index = call_mapping.get("call_index", call_index)
        if not isinstance(raw_call_index, int) or raw_call_index < 0:
            raise ModelOutputFailure("call_index must be a non-negative integer")
        tool_calls.append(
            ParsedToolCall(
                call_index=raw_call_index,
                tool_name=tool_name,
                arguments=arguments,
                tool_call_id=tool_call_id,
                metadata=call_metadata,
            )
        )

    if terminal_response is None and not tool_calls:
        raise ModelOutputFailure("model output must contain either terminal_response or tool_calls")

    return ParsedModelOutput(
        raw_text=raw_text,
        parser_version=parser_version,
        terminal_response=terminal_response,
        tool_calls=tuple(tool_calls),
        metadata=metadata,
        payload=payload,
    )


def serialize_parsed_output(parsed_output: ParsedModelOutput) -> str:
    return json.dumps(parsed_output.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))

