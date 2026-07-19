"""Deterministic Phase 5.5 tool-call extraction and diagnostics.

The extractor tolerates transport wrappers, but it never repairs or infers a
tool call.  A candidate must be complete, unique, and schema-valid before it
can reach dispatch.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

from phase5.runtime.parser_adapter import ModelOutputFailure, ParsedToolCall, parse_model_output


class ParserStatus(str, Enum):
    VALID_EXTRACTED_CALL = "VALID_EXTRACTED_CALL"
    MALFORMED_JSON = "MALFORMED_JSON"
    MODEL_OUTPUT_TRUNCATED_BY_BUDGET = "MODEL_OUTPUT_TRUNCATED_BY_BUDGET"
    INCOMPLETE_UNKNOWN = "INCOMPLETE_UNKNOWN"
    AMBIGUOUS_MULTIPLE_CANDIDATES = "AMBIGUOUS_MULTIPLE_CANDIDATES"
    AMBIGUOUS_NESTED_CANDIDATE = "AMBIGUOUS_NESTED_CANDIDATE"
    SCHEMA_INVALID_CALL = "SCHEMA_INVALID_CALL"
    NO_INVOCATION_FOUND = "NO_INVOCATION_FOUND"


@dataclass(frozen=True, slots=True)
class GenerationEvidence:
    """Authoritative generation termination information.

    A status is considered authoritative only when the producer explicitly
    records one of the supported boolean or finish-reason fields.
    """

    finish_reason: str | None = None
    max_new_tokens_reached: bool | None = None
    token_limit_reached: bool | None = None
    turn_limit_reached: bool | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "GenerationEvidence":
        if not value:
            return cls()
        finish_reason = value.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            finish_reason = None
        return cls(
            finish_reason=finish_reason,
            max_new_tokens_reached=_optional_bool(value, "max_new_tokens_reached"),
            token_limit_reached=_optional_bool(value, "token_limit_reached"),
            turn_limit_reached=_optional_bool(value, "turn_limit_reached"),
        )

    @property
    def budget_exhausted(self) -> bool:
        return any(
            item is True
            for item in (
                self.max_new_tokens_reached,
                self.token_limit_reached,
                self.turn_limit_reached,
            )
        ) or (self.finish_reason or "").lower() in {
            "length",
            "max_tokens",
            "max_new_tokens",
            "token_limit",
            "turn_limit",
        }


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    raw_text: str
    parser_version: str
    status: ParserStatus
    native_format: str
    canonical_json_compliant: bool
    parsed_call: ParsedToolCall | None = None
    parsed_calls: tuple[ParsedToolCall, ...] = ()
    candidate_spans: tuple[tuple[int, int], ...] = ()
    diagnostic: str | None = None
    candidate_count: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def valid(self) -> bool:
        return self.status is ParserStatus.VALID_EXTRACTED_CALL and bool(self.parsed_calls)

    def to_mapping(self) -> dict[str, Any]:
        return {
            "candidate_count": self.candidate_count,
            "canonical_json_compliant": self.canonical_json_compliant,
            "diagnostic": self.diagnostic,
            "metadata": dict(self.metadata),
            "native_format": self.native_format,
            "parsed_call": self.parsed_call.to_mapping() if self.parsed_call else None,
            "parsed_calls": [item.to_mapping() for item in self.parsed_calls],
            "candidate_spans": [list(item) for item in self.candidate_spans],
            "parser_version": self.parser_version,
            "raw_text": self.raw_text,
            "status": self.status.value,
        }


_TOOL_CALL_START = re.compile(r"\btool_call\s*\(", re.IGNORECASE)
_TOOL_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_BUDGET_KEYS = {
    "max_new_tokens_reached",
    "token_limit_reached",
    "turn_limit_reached",
    "finish_reason",
}


def _optional_bool(value: Mapping[str, Any], key: str) -> bool | None:
    item = value.get(key)
    return item if isinstance(item, bool) else None


def _balanced_end(text: str, start: int, opening: str = "{") -> int | None:
    closing = {"{": "}", "[": "]", "(": ")"}[opening]
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return index + 1
    return None


def _has_unclosed_candidate(text: str) -> bool:
    return _TOOL_CALL_START.search(text) is not None and text.count("(") > text.count(")")


def _is_inside_string(text: str, position: int) -> bool:
    in_string = False
    escaped = False
    for char in text[:position]:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
    return in_string


def _outside_string_tool_call(text: str) -> bool:
    """Detect a structural nested candidate inside an argument fragment."""

    for match in _TOOL_CALL_START.finditer(text):
        if not _is_inside_string(text, match.start()):
            return True
    return False


def _candidate_objects(text: str) -> list[tuple[int, int, Mapping[str, Any]]]:
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for index, char in enumerate(text):
        if char != "{":
            continue
        end = _balanced_end(text, index)
        if end is None:
            continue
        fragment = text[index:end]
        try:
            payload = json.loads(fragment)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, Mapping):
            continue
        keys = set(payload)
        if keys.intersection({"tool", "tool_calls", "terminal_response"}):
            candidates.append((index, end, payload))
    return candidates


def _text_candidates(text: str) -> tuple[list[tuple[int, int, str, Mapping[str, Any]]], bool]:
    candidates: list[tuple[int, int, str, Mapping[str, Any]]] = []
    nested = False
    for match in _TOOL_CALL_START.finditer(text):
        if _is_inside_string(text, match.start()):
            continue
        cursor = match.end()
        name_match = _TOOL_NAME.match(text, cursor)
        if not name_match:
            continue
        tool_name = name_match.group(0)
        cursor = name_match.end()
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] != ",":
            continue
        cursor += 1
        while cursor < len(text) and text[cursor].isspace():
            cursor += 1
        if cursor >= len(text) or text[cursor] != "{":
            continue
        end = _balanced_end(text, cursor)
        if end is None:
            continue
        argument_text = text[cursor:end]
        if _outside_string_tool_call(argument_text):
            nested = True
        try:
            arguments = json.loads(argument_text)
        except json.JSONDecodeError:
            continue
        if not isinstance(arguments, Mapping):
            continue
        close = end
        while close < len(text) and text[close].isspace():
            close += 1
        if close >= len(text) or text[close] != ")":
            continue
        candidates.append((match.start(), close + 1, tool_name, arguments))
    return candidates, nested


def _result(
    raw_text: str,
    *,
    status: ParserStatus,
    native_format: str,
    canonical: bool,
    parser_version: str,
    diagnostic: str,
    count: int,
    parsed_calls: tuple[ParsedToolCall, ...] = (),
    candidate_spans: tuple[tuple[int, int], ...] = (),
    metadata: Mapping[str, Any] = {},
) -> ExtractionResult:
    return ExtractionResult(
        raw_text=raw_text,
        parser_version=parser_version,
        status=status,
        native_format=native_format,
        canonical_json_compliant=canonical,
        diagnostic=diagnostic,
        candidate_count=count,
        parsed_calls=parsed_calls,
        parsed_call=parsed_calls[0] if parsed_calls else None,
        candidate_spans=candidate_spans,
        metadata=metadata,
    )


def _extract_syntax_tool_call(
    raw_text: str,
    *,
    parser_version: str = "phase5.5-parser-v2",
    generation_evidence: Mapping[str, Any] | GenerationEvidence | None = None,
) -> ExtractionResult:
    """Extract ordered, explicit, non-overlapping tool calls without repair."""

    if not isinstance(raw_text, str) or not raw_text:
        return _result(
            str(raw_text),
            status=ParserStatus.NO_INVOCATION_FOUND,
            native_format="empty",
            canonical=False,
            parser_version=parser_version,
            diagnostic="raw output is empty",
            count=0,
        )

    evidence = generation_evidence if isinstance(generation_evidence, GenerationEvidence) else GenerationEvidence.from_mapping(generation_evidence)
    stripped = raw_text.strip()
    canonical_json = False

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None
    else:
        canonical_json = isinstance(payload, Mapping)

    if canonical_json:
        try:
            parsed = parse_model_output(stripped, parser_version=parser_version)
        except ModelOutputFailure as exc:
            return _result(
                raw_text,
                status=ParserStatus.SCHEMA_INVALID_CALL,
                native_format="canonical_json",
                canonical=True,
                parser_version=parser_version,
                diagnostic=str(exc),
                count=1,
            )
        if len(parsed.tool_calls) >= 1:
            calls = tuple(parsed.tool_calls)
            return ExtractionResult(
                raw_text=raw_text,
                parser_version=parser_version,
                status=ParserStatus.VALID_EXTRACTED_CALL,
                native_format="canonical_json",
                canonical_json_compliant=True,
                parsed_call=calls[0],
                parsed_calls=calls,
                candidate_count=len(calls),
            )
        return _result(
            raw_text,
            status=ParserStatus.NO_INVOCATION_FOUND,
            native_format="canonical_json",
            canonical=True,
            parser_version=parser_version,
            diagnostic="canonical envelope contains no tool invocation",
            count=0,
            parsed_calls=(),
            metadata={"terminal_response": parsed.terminal_response},
        )

    text_calls, nested = _text_candidates(raw_text)
    object_candidates = _candidate_objects(raw_text)
    candidate_count = len(text_calls) + len(object_candidates)
    if nested:
        return _result(
            raw_text,
            status=ParserStatus.AMBIGUOUS_NESTED_CANDIDATE,
            native_format="textual_invocation",
            canonical=False,
            parser_version=parser_version,
            diagnostic="structurally nested tool invocation detected",
            count=max(2, candidate_count),
        )
    if text_calls and object_candidates:
        return _result(
            raw_text,
            status=ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES,
            native_format="mixed_text",
            canonical=False,
            parser_version=parser_version,
            diagnostic="textual and JSON invocation candidates overlap in the same output",
            count=candidate_count,
        )
    if len(text_calls) > 0:
        calls = tuple(
            ParsedToolCall(call_index=index, tool_name=tool_name, arguments=arguments)
            for index, (_, _, tool_name, arguments) in enumerate(text_calls)
        )
        return ExtractionResult(
            raw_text=raw_text,
            parser_version=parser_version,
            status=ParserStatus.VALID_EXTRACTED_CALL,
            native_format="textual_invocation",
            canonical_json_compliant=False,
            parsed_call=calls[0],
            parsed_calls=calls,
            candidate_count=len(calls),
            candidate_spans=tuple((start, end) for start, end, _, _ in text_calls),
        )
    if object_candidates:
        spans = tuple((start, end) for start, end, _ in object_candidates)
        for index, (start, end, _) in enumerate(object_candidates):
            if any(
                other_start <= start and end <= other_end and (other_start, other_end) != (start, end)
                for other_start, other_end, _ in object_candidates
            ):
                return _result(
                    raw_text,
                    status=ParserStatus.AMBIGUOUS_NESTED_CANDIDATE,
                    native_format="embedded_json",
                    canonical=False,
                    parser_version=parser_version,
                    diagnostic="a JSON invocation candidate is structurally nested in another candidate",
                    count=len(object_candidates),
                    candidate_spans=spans,
                )
        parsed_calls: list[ParsedToolCall] = []
        for start, end, payload in object_candidates:
            try:
                parsed = parse_model_output(payload, parser_version=parser_version)
            except ModelOutputFailure as exc:
                return _result(
                    raw_text,
                    status=ParserStatus.SCHEMA_INVALID_CALL,
                    native_format="embedded_json",
                    canonical=False,
                    parser_version=parser_version,
                    diagnostic=str(exc),
                    count=len(object_candidates),
                    candidate_spans=spans,
                )
            if not parsed.tool_calls:
                return _result(
                    raw_text,
                    status=ParserStatus.NO_INVOCATION_FOUND,
                    native_format="embedded_json",
                    canonical=False,
                    parser_version=parser_version,
                    diagnostic="embedded JSON contains no tool invocation",
                    count=0,
                    candidate_spans=spans,
                )
            parsed_calls.extend(parsed.tool_calls)
        calls = tuple(
            ParsedToolCall(call_index=index, tool_name=call.tool_name, arguments=call.arguments,
                           tool_call_id=call.tool_call_id, metadata=call.metadata)
            for index, call in enumerate(parsed_calls)
        )
        return ExtractionResult(
            raw_text=raw_text,
            parser_version=parser_version,
            status=ParserStatus.VALID_EXTRACTED_CALL,
            native_format="embedded_json",
            canonical_json_compliant=False,
            parsed_call=calls[0],
            parsed_calls=calls,
            candidate_count=len(calls),
            candidate_spans=spans,
        )
    if evidence.budget_exhausted and ("{" in raw_text or "tool_call" in raw_text):
        status = ParserStatus.MODEL_OUTPUT_TRUNCATED_BY_BUDGET
        diagnostic = "authoritative generation evidence reports budget or turn-limit exhaustion"
    elif ("{" in raw_text and raw_text.count("{") > raw_text.count("}")) or _has_unclosed_candidate(raw_text):
        status = ParserStatus.INCOMPLETE_UNKNOWN
        diagnostic = "candidate appears incomplete without authoritative truncation evidence"
    elif "{" in raw_text or "}" in raw_text or "tool_call" in raw_text:
        status = ParserStatus.MALFORMED_JSON
        diagnostic = "candidate syntax was present but no valid invocation could be parsed"
    else:
        status = ParserStatus.NO_INVOCATION_FOUND
        diagnostic = "no explicit tool invocation found"
    return _result(
        raw_text,
        status=status,
        native_format="text",
        canonical=False,
        parser_version=parser_version,
        diagnostic=diagnostic,
        count=0,
    )


def _json_value_matches_schema(value: Any, schema: Mapping[str, Any]) -> bool:
    schema_type = schema.get("type")
    if schema_type == "string":
        return isinstance(value, str)
    if schema_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if schema_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if schema_type == "boolean":
        return isinstance(value, bool)
    if schema_type == "object":
        return isinstance(value, Mapping)
    if schema_type == "array":
        return isinstance(value, list)
    return True


def _validate_tool_schema(
    result: ExtractionResult,
    *,
    tool_schemas: Mapping[str, Any],
    forbidden_tool_names: tuple[str, ...],
) -> str | None:
    for call in result.parsed_calls:
        if call.tool_name in forbidden_tool_names:
            return f"forbidden tool requested: {call.tool_name!r}"
        specification = tool_schemas.get(call.tool_name)
        if specification is None:
            return f"unknown tool requested: {call.tool_name!r}"
        schema = getattr(specification, "parameter_schema", specification)
        if not isinstance(schema, Mapping):
            return f"tool schema is invalid for {call.tool_name!r}"
        required = schema.get("required", ())
        properties = schema.get("properties", {})
        if not isinstance(required, (list, tuple)) or not isinstance(properties, Mapping):
            return f"tool schema is invalid for {call.tool_name!r}"
        missing = [name for name in required if name not in call.arguments]
        if missing:
            return f"tool {call.tool_name!r} is missing required argument {missing[0]!r}"
        if schema.get("additionalProperties") is False:
            unknown = [name for name in call.arguments if name not in properties]
            if unknown:
                return f"tool {call.tool_name!r} has unknown argument {unknown[0]!r}"
        for name, value in call.arguments.items():
            property_schema = properties.get(name)
            if isinstance(property_schema, Mapping) and not _json_value_matches_schema(value, property_schema):
                return f"tool {call.tool_name!r} argument {name!r} has the wrong type"
    return None


def extract_tool_call(
    raw_text: str,
    *,
    parser_version: str = "phase5.5-parser-v2",
    generation_evidence: Mapping[str, Any] | GenerationEvidence | None = None,
    tool_schemas: Mapping[str, Any] | None = None,
    forbidden_tool_names: tuple[str, ...] = (),
) -> ExtractionResult:
    """Extract and, when supplied, validate calls against the discovered MCP contract."""

    result = _extract_syntax_tool_call(
        raw_text,
        parser_version=parser_version,
        generation_evidence=generation_evidence,
    )
    if result.status is not ParserStatus.VALID_EXTRACTED_CALL or tool_schemas is None:
        return result
    diagnostic = _validate_tool_schema(
        result,
        tool_schemas=tool_schemas,
        forbidden_tool_names=tuple(forbidden_tool_names),
    )
    if diagnostic is None:
        return result
    return _result(
        raw_text,
        status=ParserStatus.SCHEMA_INVALID_CALL,
        native_format=result.native_format,
        canonical=result.canonical_json_compliant,
        parser_version=parser_version,
        diagnostic=diagnostic,
        count=result.candidate_count,
        candidate_spans=result.candidate_spans,
    )
