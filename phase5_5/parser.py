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
from collections.abc import Sequence
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


def _parse_text_tool_name(text: str, cursor: int) -> tuple[str, int] | None:
    """Parse an explicit textual tool name, bare or as a JSON string."""

    bare_match = _TOOL_NAME.match(text, cursor)
    if bare_match:
        return bare_match.group(0), bare_match.end()
    if cursor >= len(text) or text[cursor] != '"':
        return None
    try:
        decoded, consumed = json.JSONDecoder().raw_decode(text[cursor:])
    except json.JSONDecodeError:
        return None
    if not isinstance(decoded, str) or not _TOOL_NAME.fullmatch(decoded):
        return None
    return decoded, cursor + consumed


def _normalise_explicit_alias_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    """Map explicit Phase 5.5 alias envelopes onto the frozen adapter shape.

    This is intentionally narrow: singular ``tool_call`` is accepted only as a
    complete ordered sequence of call mappings and only when the canonical
    ``tool``/``tool_calls`` fields are absent.
    """

    if "tool_call" not in payload:
        return payload
    if "tool" in payload or "tool_calls" in payload:
        raise ModelOutputFailure("tool_call alias cannot be mixed with canonical tool or tool_calls envelopes")
    tool_call_value = payload.get("tool_call")
    if not isinstance(tool_call_value, Sequence) or isinstance(tool_call_value, (str, bytes, bytearray)):
        raise ModelOutputFailure("tool_call alias must be an ordered sequence of tool-call mappings")
    normalised: dict[str, Any] = dict(payload)
    normalised["tool_calls"] = tool_call_value
    del normalised["tool_call"]
    return normalised


def _duplicate_call_keys(calls: tuple[ParsedToolCall, ...]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for call in calls:
        key = json.dumps(
            {
                "arguments": call.arguments,
                "tool_call_id": call.tool_call_id,
                "tool_name": call.tool_name,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if key in seen:
            duplicates.add(key)
        seen.add(key)
    return duplicates


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
        if keys.intersection({"tool", "tool_calls", "tool_call", "terminal_response"}):
            candidates.append((index, end, payload))
    return candidates


def _text_candidates(text: str) -> tuple[list[tuple[int, int, str, Mapping[str, Any]]], bool]:
    candidates: list[tuple[int, int, str, Mapping[str, Any]]] = []
    nested = False
    for match in _TOOL_CALL_START.finditer(text):
        if _is_inside_string(text, match.start()):
            continue
        cursor = match.end()
        parsed_name = _parse_text_tool_name(text, cursor)
        if not parsed_name:
            continue
        tool_name, cursor = parsed_name
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


def extract_tool_call(
    raw_text: str,
    *,
    parser_version: str = "phase5.5-parser-v2",
    generation_evidence: Mapping[str, Any] | GenerationEvidence | None = None,
    tool_schemas: Mapping[str, Any] | None = None,
    forbidden_tool_names: frozenset[str] | set[str] | None = None,
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

    if "Tool Result [" in raw_text:
        return _result(
            raw_text,
            status=ParserStatus.NO_INVOCATION_FOUND,
            native_format="text",
            canonical=False,
            parser_version=parser_version,
            diagnostic="candidate generated simulated environment responses",
            count=0,
        )

    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError:
        payload = None
    else:
        canonical_json = isinstance(payload, Mapping)

    alias_only_json = (
        isinstance(payload, Mapping)
        and "tool_call" in payload
        and "tool" not in payload
        and "tool_calls" not in payload
    )
    if canonical_json and "tool_call" in payload and not alias_only_json:
        return _result(
            raw_text,
            status=ParserStatus.SCHEMA_INVALID_CALL,
            native_format="canonical_json",
            canonical=False,
            parser_version=parser_version,
            diagnostic="tool_call alias cannot be mixed with canonical tool or tool_calls envelopes",
            count=1,
        )

    if canonical_json and not alias_only_json:
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
            if _duplicate_call_keys(calls):
                return _result(
                    raw_text,
                    status=ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES,
                    native_format="canonical_json",
                    canonical=True,
                    parser_version=parser_version,
                    diagnostic="duplicate tool invocation candidates detected",
                    count=len(calls),
                )
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
        # If object_candidates ONLY contains terminal responses, ignore them to maintain M1/M2 compatibility where text calls take precedence
        has_tool_objects = any(
            set(obj).intersection({"tool", "tool_calls", "tool_call"}) 
            for _, _, obj in object_candidates
        )
        if has_tool_objects:
            return _result(
                raw_text,
                status=ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES,
                native_format="mixed_text",
                canonical=False,
                parser_version=parser_version,
                diagnostic="textual and JSON invocation candidates overlap in the same output",
                count=candidate_count,
            )
        else:
            # We only have text_calls, pure terminal responses are ignored
            object_candidates = []
            candidate_count = len(text_calls)
    if len(text_calls) > 0:
        calls = tuple(
            ParsedToolCall(call_index=index, tool_name=tool_name, arguments=arguments)
            for index, (_, _, tool_name, arguments) in enumerate(text_calls)
        )
        if _duplicate_call_keys(calls):
            return _result(
                raw_text,
                status=ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES,
                native_format="textual_invocation",
                canonical=False,
                parser_version=parser_version,
                diagnostic="duplicate tool invocation candidates detected",
                count=len(calls),
                candidate_spans=tuple((start, end) for start, end, _, _ in text_calls),
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
                parsed = parse_model_output(_normalise_explicit_alias_payload(payload), parser_version=parser_version)
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
                continue
            parsed_calls.extend(parsed.tool_calls)
            
        if not parsed_calls:
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
        calls = tuple(
            ParsedToolCall(call_index=index, tool_name=call.tool_name, arguments=call.arguments,
                           tool_call_id=call.tool_call_id, metadata=call.metadata)
            for index, call in enumerate(parsed_calls)
        )
        if _duplicate_call_keys(calls):
            return _result(
                raw_text,
                status=ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES,
                native_format="embedded_json",
                canonical=False,
                parser_version=parser_version,
                diagnostic="duplicate tool invocation candidates detected",
                count=len(calls),
                candidate_spans=spans,
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
