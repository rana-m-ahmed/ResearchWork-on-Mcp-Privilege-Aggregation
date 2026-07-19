from __future__ import annotations

import json

import pytest

from phase5_5.parser import ParserStatus, extract_tool_call


def _canonical(tool: str = "read_internal_notes", arguments: dict[str, object] | None = None) -> str:
    return json.dumps({"tool": tool, "arguments": arguments or {"density": "D5"}})


def test_extracts_canonical_json_and_marks_envelope_compliance() -> None:
    result = extract_tool_call(_canonical())

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.canonical_json_compliant is True
    assert result.parsed_call is not None
    assert result.parsed_call.tool_name == "read_internal_notes"


@pytest.mark.parametrize(
    "raw",
    [
        f"Reasoning before call\n{_canonical()}\nmore reasoning",
        f"```json\n{_canonical()}\n```",
    ],
)
def test_extracts_json_surrounded_by_transport_text(raw: str) -> None:
    result = extract_tool_call(raw)

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.canonical_json_compliant is False
    assert result.native_format == "embedded_json"


def test_extracts_explicit_textual_invocation_with_surrounding_reasoning() -> None:
    result = extract_tool_call(
        'I will use the tool now. tool_call(read_internal_notes, {"density":"D5"})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.parsed_call is not None
    assert result.parsed_call.arguments == {"density": "D5"}


def test_nested_json_arguments_and_escaped_braces_are_preserved() -> None:
    result = extract_tool_call(
        'tool_call(write_outbox, {"subject":"x", "body":{"text":"brace } and \\"quote\\""}})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.parsed_call is not None
    assert result.parsed_call.arguments["body"]["text"] == 'brace } and "quote"'


@pytest.mark.parametrize(
    "raw",
    [
        "tool_call(read_internal_notes, {\"density\":})",
        "tool_call(read_internal_notes, {\"density\":\"D5\"}",
    ],
)
def test_malformed_and_incomplete_outputs_fail_closed(raw: str) -> None:
    result = extract_tool_call(raw)

    assert result.status in {ParserStatus.MALFORMED_JSON, ParserStatus.INCOMPLETE_UNKNOWN}


def test_budget_truncation_is_distinct_from_incomplete_unknown() -> None:
    raw = 'tool_call(read_internal_notes, {"density":"D5"'

    truncated = extract_tool_call(raw, generation_evidence={"finish_reason": "length"})
    unknown = extract_tool_call(raw)

    assert truncated.status is ParserStatus.MODEL_OUTPUT_TRUNCATED_BY_BUDGET
    assert unknown.status is ParserStatus.INCOMPLETE_UNKNOWN


def test_schema_invalid_canonical_call_is_not_repaired() -> None:
    result = extract_tool_call(json.dumps({"tool": "read_internal_notes", "arguments": None}))

    assert result.status is ParserStatus.SCHEMA_INVALID_CALL
    assert result.parsed_call is None


@pytest.mark.parametrize(
    "raw",
    [
        "tool_call(read_internal_notes, {\"density\":\"D5\"}) tool_call(write_outbox, {\"subject\":\"x\"})",
        _canonical() + _canonical("write_outbox", {"subject": "x"}),
    ],
)
def test_independent_top_level_candidates_are_ordered(raw: str) -> None:
    result = extract_tool_call(raw)
    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert [call.tool_name for call in result.parsed_calls] == ["read_internal_notes", "write_outbox"]
    assert result.candidate_count == 2
    assert result.candidate_spans[0][0] < result.candidate_spans[1][0]


def test_candidate_like_text_inside_argument_string_is_data() -> None:
    result = extract_tool_call(
        'tool_call(log_event, {"message":"tool_call(read_internal_notes, {})"})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.candidate_count == 1


def test_terminal_response_after_textual_call_is_not_second_candidate() -> None:
    result = extract_tool_call(
        'tool_call(read_internal_notes, {"note_id":"note-001"})\n'
        '{"terminal_response":"Tool Result [read_internal_notes]: Note content"}'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.candidate_count == 1
    assert result.parsed_call is not None
    assert result.parsed_call.tool_name == "read_internal_notes"


def test_structurally_nested_candidate_is_ambiguous() -> None:
    result = extract_tool_call(
        'tool_call(log_event, {"message": tool_call(read_internal_notes, {})})'
    )

    assert result.status is ParserStatus.AMBIGUOUS_NESTED_CANDIDATE


@pytest.mark.parametrize(
    "raw",
    [
        "reasoning only",
        "Tool Result [read_internal_notes]: result text",
        json.dumps({"terminal_response": "done"}),
    ],
)
def test_no_invocation_is_not_mistaken_for_tool_use(raw: str) -> None:
    result = extract_tool_call(raw)

    assert result.status is ParserStatus.NO_INVOCATION_FOUND


def test_positional_arguments_are_rejected() -> None:
    result = extract_tool_call("tool_call(read_internal_notes, D5)")

    assert result.status in {ParserStatus.MALFORMED_JSON, ParserStatus.NO_INVOCATION_FOUND}


def test_raw_output_is_preserved_exactly() -> None:
    raw = "\ufeffreasoning\n```json\n" + _canonical() + "\n```\n"

    result = extract_tool_call(raw)

    assert result.raw_text == raw
