from __future__ import annotations

from phase5.runtime.engine import _select_grader_parser_event


def test_grader_parser_event_prefers_invocation_over_terminal_response() -> None:
    invocation_event = {
        "event_type": "PARSE_COMPLETED",
        "status": "VALID_EXTRACTED_CALL",
        "turn_index": 0,
        "parsed_output": {
            "tool_calls": [{"tool_name": "write_outbox", "arguments": {"body": "ok"}}],
        },
    }
    terminal_event = {
        "event_type": "PARSE_COMPLETED",
        "status": "NO_INVOCATION_FOUND",
        "turn_index": 1,
        "parsed_output": {
            "terminal_response": "done",
            "tool_calls": [],
        },
    }

    assert _select_grader_parser_event([invocation_event, terminal_event]) is invocation_event


def test_grader_parser_event_preserves_latest_failure_without_invocation() -> None:
    failure_event = {
        "event_type": "PARSE_FAILURE",
        "reason": "MALFORMED_JSON",
        "turn_index": 0,
    }
    terminal_event = {
        "event_type": "PARSE_COMPLETED",
        "status": "NO_INVOCATION_FOUND",
        "turn_index": 1,
        "parsed_output": {"tool_calls": []},
    }

    assert _select_grader_parser_event([failure_event, terminal_event]) is failure_event
