"""Verbatim conversation and tool-result serialization helpers for Phase 5."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ..domain.errors import SchemaInvariantError


def _require_string(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaInvariantError(f"{field_name} must be a non-empty string")
    return value


def _require_optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_string(value, field_name)


@dataclass(frozen=True, slots=True)
class ConversationTurn:
    """A single conversation or tool-result turn preserved without normalization."""

    turn_index: int
    role: str
    content: str | None
    turn_kind: str = "conversation"
    tool_name: str | None = None
    tool_call_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.turn_index < 0:
            raise SchemaInvariantError("turn_index must be non-negative")
        _require_string(self.role, "role")
        _require_string(self.turn_kind, "turn_kind")
        _require_optional_string(self.content, "content")
        _require_optional_string(self.tool_name, "tool_name")
        _require_optional_string(self.tool_call_id, "tool_call_id")
        if not isinstance(self.metadata, Mapping):
            raise SchemaInvariantError("metadata must be a mapping")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "content": self.content,
            "metadata": dict(self.metadata),
            "role": self.role,
            "tool_call_id": self.tool_call_id,
            "tool_name": self.tool_name,
            "turn_index": self.turn_index,
            "turn_kind": self.turn_kind,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ConversationTurn":
        try:
            metadata = mapping.get("metadata", {})
            if not isinstance(metadata, Mapping):
                raise SchemaInvariantError("metadata must be a mapping")
            return cls(
                turn_index=mapping["turn_index"],
                role=_require_string(mapping["role"], "role"),
                content=_require_optional_string(mapping.get("content"), "content"),
                turn_kind=_require_string(mapping.get("turn_kind", "conversation"), "turn_kind"),
                tool_name=_require_optional_string(mapping.get("tool_name"), "tool_name"),
                tool_call_id=_require_optional_string(mapping.get("tool_call_id"), "tool_call_id"),
                metadata=metadata,
            )
        except KeyError as exc:
            raise SchemaInvariantError(f"missing conversation field: {exc.args[0]}") from exc


def normalize_turns(turns: Sequence[ConversationTurn | Mapping[str, Any]] | None) -> tuple[ConversationTurn, ...]:
    if not turns:
        return ()
    normalized: list[ConversationTurn] = []
    for turn in turns:
        if isinstance(turn, ConversationTurn):
            normalized.append(turn)
        elif isinstance(turn, Mapping):
            normalized.append(ConversationTurn.from_mapping(turn))
        else:
            raise SchemaInvariantError(f"unsupported turn type: {type(turn).__name__}")
    return tuple(normalized)


def serialize_turn(turn: ConversationTurn) -> str:
    """Serialize a turn verbatim without trimming or reformatting content."""

    return json.dumps(turn.to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def render_turn(turn: ConversationTurn, *, tool_result_template: str) -> str:
    """Render a single turn using the frozen tool-result template when needed."""

    if turn.role == "tool":
        tool_name = turn.tool_name or ""
        tool_output = turn.content or ""
        rendered = tool_result_template.replace("{{tool_name}}", tool_name)
        rendered = rendered.replace("{{tool_output}}", tool_output)
        if "{{" in rendered or "}}" in rendered:
            raise SchemaInvariantError("tool result template contains unresolved placeholders")
        return rendered
    if turn.content is None:
        return f"{turn.role}:\n"
    return f"{turn.role}:\n{turn.content}"


def render_history(turns: Sequence[ConversationTurn | Mapping[str, Any]] | None, *, tool_result_template: str) -> str:
    normalized = normalize_turns(turns)
    if not normalized:
        return ""
    rendered = [render_turn(turn, tool_result_template=tool_result_template) for turn in normalized]
    return "\n\n".join(rendered)


def render_turn_stream(
    turns: Sequence[ConversationTurn | Mapping[str, Any]] | None,
    *,
    tool_result_template: str,
) -> tuple[str, ...]:
    normalized = normalize_turns(turns)
    return tuple(render_turn(turn, tool_result_template=tool_result_template) for turn in normalized)
