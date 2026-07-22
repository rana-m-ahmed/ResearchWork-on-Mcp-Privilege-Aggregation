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


def test_extracts_textual_invocation_with_json_string_tool_name() -> None:
    result = extract_tool_call(
        'Reasoning first. tool_call("log_event", {"detail":"done", "event_type":"benign_task"})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.parsed_call is not None
    assert result.parsed_call.tool_name == "log_event"
    assert result.parsed_call.arguments == {"detail": "done", "event_type": "benign_task"}


def test_nested_json_arguments_and_escaped_braces_are_preserved() -> None:
    result = extract_tool_call(
        'tool_call(write_outbox, {"subject":"x", "body":{"text":"brace } and \\"quote\\""}})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.parsed_call is not None
    assert result.parsed_call.arguments["body"]["text"] == 'brace } and "quote"'


def test_extracts_singular_tool_call_alias_as_ordered_embedded_json() -> None:
    raw = """```json
{
  "tool_call": [
    {
      "tool_name": "write_outbox",
      "arguments": {
        "body": "Phase 5.5 benign task confirmation.",
        "recipient": "local-reviewer"
      }
    },
    {
      "tool_name": "read_internal_notes",
      "arguments": {
        "note_id": "note-001"
      }
    }
  ],
  "terminal_response": "done"
}
```"""

    result = extract_tool_call(raw)

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.native_format == "embedded_json"
    assert result.canonical_json_compliant is False
    assert [call.tool_name for call in result.parsed_calls] == [
        "write_outbox",
        "read_internal_notes",
    ]
    assert result.parsed_calls[0].arguments["recipient"] == "local-reviewer"
    assert result.parsed_calls[1].arguments["note_id"] == "note-001"
    assert result.candidate_count == 2


def test_embedded_terminal_response_block_does_not_ambiguous_real_tool_call_block() -> None:
    raw = """```json
{
  "tool_call": [
    {"tool_name": "query_local_inventory", "arguments": {"item_id": "INV-1001"}},
    {"tool_name": "log_event", "arguments": {"detail": "done", "event_type": "benign_task"}}
  ]
}
```

```json
{"terminal_response": "done"}
```"""

    result = extract_tool_call(raw)

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert [call.tool_name for call in result.parsed_calls] == [
        "query_local_inventory",
        "log_event",
    ]
    assert result.candidate_count == 2


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
        json.dumps(
            {
                "tool_call": [{"tool_name": "alpha", "arguments": {}}],
                "tool_calls": [{"tool_name": "beta", "arguments": {}}],
            }
        ),
        json.dumps({"tool_call": {"tool_name": "alpha", "arguments": {}}}),
        'tool_call("bad name", {"x": 1})',
        "tool_call('log_event', {\"detail\":\"done\"})",
    ],
)
def test_alias_and_quoted_name_extensions_still_fail_closed_when_invalid(raw: str) -> None:
    result = extract_tool_call(raw)

    assert result.status in {
        ParserStatus.SCHEMA_INVALID_CALL,
        ParserStatus.MALFORMED_JSON,
        ParserStatus.NO_INVOCATION_FOUND,
    }
    assert not result.valid


def test_independent_top_level_candidates_are_ordered_textual() -> None:
    raw = "tool_call(read_internal_notes, {\"density\":\"D5\"}) tool_call(write_outbox, {\"subject\":\"x\"})"
    result = extract_tool_call(raw)
    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert [call.tool_name for call in result.parsed_calls] == ["read_internal_notes", "write_outbox"]
    assert result.candidate_count == 2
    assert result.candidate_spans[0][0] < result.candidate_spans[1][0]

def test_independent_top_level_candidates_are_ordered_embedded() -> None:
    raw = _canonical() + _canonical("write_outbox", {"subject": "x"})
    result = extract_tool_call(raw)
    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert [call.tool_name for call in result.parsed_calls] == ["read_internal_notes", "write_outbox"]
    assert result.candidate_count == 2


def test_m2_alias_list_with_premature_terminal_response_preserves_source_to_sink_order() -> None:
    raw = """M2 reasoning before the fenced JSON.

```json
{
  "tool_call": [
    {
      "tool_name": "write_outbox",
      "arguments": {
        "body": "Phase 5.5 benign task confirmation.",
        "recipient": "local-reviewer"
      }
    },
    {
      "tool_name": "read_internal_notes",
      "arguments": {
        "note_id": "note-001"
      }
    }
  ],
  "terminal_response": "premature completion text"
}
```"""

    result = extract_tool_call(raw, parser_version="phase5.5-parser-v3-mcp-schema")

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.native_format == "embedded_json"
    assert [call.tool_name for call in result.parsed_calls] == [
        "write_outbox",
        "read_internal_notes",
    ]
    assert result.candidate_count == 2


def test_candidate_like_text_inside_argument_string_is_data() -> None:
    result = extract_tool_call(
        'tool_call(log_event, {"message":"tool_call(read_internal_notes, {})"})'
    )

    assert result.status is ParserStatus.VALID_EXTRACTED_CALL
    assert result.candidate_count == 1


def test_duplicate_top_level_candidates_fail_closed() -> None:
    raw = (
        'The call should be tool_call("log_event", {"detail":"done", "event_type":"benign_task"}). '
        '```json\n'
        'tool_call("log_event", {"detail":"done", "event_type":"benign_task"})\n'
        '```'
    )

    result = extract_tool_call(raw)

    assert result.status is ParserStatus.AMBIGUOUS_MULTIPLE_CANDIDATES
    assert not result.valid
    assert result.candidate_count == 2


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
