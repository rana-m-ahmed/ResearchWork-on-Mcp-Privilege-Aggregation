from __future__ import annotations

import json
from pathlib import Path

import pytest

from phase5.runtime import (
    ForbiddenToolCallError,
    MissingToolParameterError,
    ModelOutputFailure,
    ParsedToolCall,
    ToolDispatchPolicy,
    ToolSpecification,
    UnknownToolCallError,
    dispatch_tool_calls,
    parse_model_output,
)


def test_parse_terminal_response_preserves_metadata_and_terminal_state() -> None:
    parsed = parse_model_output(
        json.dumps({"terminal_response": "done", "metadata": {"turn": 1}}, ensure_ascii=False),
        parser_version="p10-v1",
    )

    assert parsed.is_terminal is True
    assert parsed.terminal_response == "done"
    assert parsed.metadata["turn"] == 1
    assert parsed.tool_calls == ()


def test_parse_tool_calls_preserves_order_and_call_ids() -> None:
    parsed = parse_model_output(
        json.dumps(
            {
                "tool_calls": [
                    {"tool_name": "alpha", "arguments": {"x": 1}, "tool_call_id": "call-1"},
                    {"tool_name": "beta", "arguments": {"y": 2}, "tool_call_id": "call-2"},
                ],
                "metadata": {"mode": "tool"},
            },
            ensure_ascii=False,
        ),
        parser_version="p10-v1",
    )

    assert [call.tool_name for call in parsed.tool_calls] == ["alpha", "beta"]
    assert [call.tool_call_id for call in parsed.tool_calls] == ["call-1", "call-2"]
    assert parsed.metadata["mode"] == "tool"


@pytest.mark.parametrize(
    "raw_output",
    [
        "not-json",
        json.dumps(["not", "a", "mapping"], ensure_ascii=False),
        json.dumps({"tool_calls": [{"tool_name": "alpha"}]}, ensure_ascii=False),
    ],
)
def test_parse_malformed_model_output_fails_closed(raw_output: str) -> None:
    with pytest.raises(ModelOutputFailure):
        parse_model_output(raw_output, parser_version="p10-v1")


def _policy() -> ToolDispatchPolicy:
    return ToolDispatchPolicy(
        multiple_tool_call_policy="serial",
        tool_error_reinsertion_policy="reinsert_raw",
        forbidden_tool_names=("reset", "debug"),
        max_total_tool_calls=4,
        max_identical_consecutive_tool_calls=2,
        max_identical_total_tool_calls=4,
    )


def test_dispatch_serializes_tool_results_and_preserves_logical_names() -> None:
    calls = (
        ParsedToolCall(call_index=0, tool_name="alpha", arguments={"x": 1}, tool_call_id="call-1"),
        ParsedToolCall(call_index=1, tool_name="beta", arguments={"y": 2}, tool_call_id="call-2"),
    )
    catalog = {
        "alpha": ToolSpecification(
            exposed_tool_name="alpha",
            logical_tool_name="logical_alpha",
            required_arguments=("x",),
            handler=lambda arguments: {"seen": arguments["x"]},
        ),
        "beta": ToolSpecification(
            exposed_tool_name="beta",
            logical_tool_name="logical_beta",
            required_arguments=("y",),
            handler=lambda arguments: f"beta:{arguments['y']}",
        ),
    }

    records = dispatch_tool_calls(
        calls,
        tool_catalog=catalog,
        policy=_policy(),
        tool_result_serialization_version="tool-result-v1",
        clock=lambda: 0.0,
    )

    assert [record.exposed_tool_name for record in records] == ["alpha", "beta"]
    assert [record.logical_tool_name for record in records] == ["logical_alpha", "logical_beta"]
    assert records[0].result_text == '{"seen":1}'
    assert records[1].result_text == "beta:2"
    assert records[0].to_conversation_turn(tool_result_serialization_version="tool-result-v1").role == "tool"


def test_dispatch_rejects_hallucinated_forbidden_and_missing_parameters() -> None:
    catalog = {
        "alpha": ToolSpecification(
            exposed_tool_name="alpha",
            required_arguments=("x",),
            handler=lambda arguments: arguments["x"],
        )
    }

    with pytest.raises(UnknownToolCallError):
        dispatch_tool_calls(
            (ParsedToolCall(call_index=0, tool_name="hallucinated", arguments={}, tool_call_id=None),),
            tool_catalog=catalog,
            policy=_policy(),
        )

    with pytest.raises(ForbiddenToolCallError):
        dispatch_tool_calls(
            (ParsedToolCall(call_index=0, tool_name="debug", arguments={}, tool_call_id=None),),
            tool_catalog={"debug": catalog["alpha"]},
            policy=_policy(),
        )

    with pytest.raises(MissingToolParameterError):
        dispatch_tool_calls(
            (ParsedToolCall(call_index=0, tool_name="alpha", arguments={}, tool_call_id=None),),
            tool_catalog=catalog,
            policy=_policy(),
        )

