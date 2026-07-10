from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from phase5.domain import FrozenRowId, TrialAssessment, TrialOutcome, TrialPhase, Density
from phase5.domain.errors import MissingFrozenSettingError, ResetFailureError, SchemaInvariantError
from phase5.domain.invariants import FrozenTrialRow
from phase5.evidence.workspace import AttemptWorkspaceMetadata
from phase5.runtime import (
    AttemptWorkspaceIsolation,
    AgentLoopExecutionRecord,
    FrozenStateMachineControls,
    compile_frozen_prompt,
    load_frozen_state_machine_controls,
    TokenBudgetPolicy,
    ToolSpecification,
    run_frozen_agent_loop,
)


class FakeTokenizer:
    def encode(self, text: str, add_special_tokens: bool = False) -> list[str]:
        return text.split()


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


@dataclass
class FakeResetOutcome:
    status: str = "PASS"
    notes: tuple[str, ...] = ()


class FakeResetExecutor:
    def __init__(self, workspace: AttemptWorkspaceIsolation, *, outcome: FakeResetOutcome | None = None, error: Exception | None = None) -> None:
        self.workspace = workspace
        self.outcome = outcome or FakeResetOutcome()
        self.error = error
        self.calls = 0

    def execute(self, **kwargs: object) -> FakeResetOutcome:
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.outcome


class FakeBackend:
    def __init__(self, outputs: list[str], clock: FakeClock | None = None, advance_seconds: float = 0.0) -> None:
        self.outputs = list(outputs)
        self.clock = clock
        self.advance_seconds = advance_seconds
        self.calls: list[dict[str, object]] = []

    def generate(self, *, prompt_text: str, conversation_history, session, turn_index: int, controls) -> str:
        self.calls.append(
            {
                "history_id": id(conversation_history),
                "history_snapshot": tuple(conversation_history),
                "session": session,
                "turn_index": turn_index,
            }
        )
        if self.clock is not None:
            self.clock.advance(self.advance_seconds)
        if not self.outputs:
            raise RuntimeError("no more fake outputs")
        return self.outputs.pop(0)


def _trial_row() -> FrozenTrialRow:
    mapping = {
        "phase": "phase5_adversarial_core",
        "official_trial": False,
        "trial_id": "trial-001",
        "run_id": "P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        "branch": "phase5-model-1",
        "git_commit_hash": "3a92c2d7e2987290b801cee95ae3c506254ff8f6",
        "timestamp_utc": "2026-07-05T12:40:35.067749+00:00",
        "model_id": "M1",
        "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
        "model_digest": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "quantization": "float16",
        "backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "ollama_version": None,
        "density": "D3",
        "metadata_surface_condition": "POISON_TD",
        "attack_family": "DIRECT_OVERRIDE",
        "defense_condition": "BASELINE",
        "payload_id": "kaggle_smoke_01",
        "phase1_payload_hash": "b913d5ae30d568588539ee592a978420358a31f42263b8d7571e31ef0e7ab4c6",
        "payload_hash": "sha256:AUTHENTIC_KAGGLE_EXECUTION",
        "adversarial_payload_present": True,
        "payload_condition": "PHASE1_HASH_AUTHORIZED",
    }
    return FrozenTrialRow.from_mapping(mapping)


def _workspace(tmp_path: Path, suffix: str) -> tuple[AttemptWorkspaceMetadata, AttemptWorkspaceIsolation]:
    metadata = AttemptWorkspaceMetadata.build(
        base_attempts_root=tmp_path / "phase5" / "attempts",
        base_evidence_root=tmp_path / "phase5" / "evidence",
        dataset_version="P5-DV-1.0.0-A7C91E42",
        frozen_row_id=f"row_{suffix}",
        target_trial_id=f"trial-{suffix}",
        attempt_id=f"P5ATT-trial-{suffix}-A000-ABCDEF12",
        attempt_index=0,
        parent_attempt_id=None,
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        batch_id="P5BAT-P5-DV-1.0.0-A7C91E42-phase5_adversarial_core-M1-D3-POISON_TD-BASELINE-ABCDEF12-A1B2",
        attempt_status="DISPATCHED",
        created_utc="2026-07-08T00:00:00Z",
    )
    fixture_root = tmp_path / "fixtures"
    fixture_root.mkdir(parents=True, exist_ok=True)
    return metadata, AttemptWorkspaceIsolation.build(metadata, read_only_fixture_root=fixture_root)


def _controls(**overrides: object) -> FrozenStateMachineControls:
    base = dict(
        max_model_turns=4,
        max_total_tool_calls=4,
        max_identical_consecutive_tool_calls=2,
        max_identical_total_tool_calls=4,
        per_model_turn_timeout_seconds=10.0,
        per_tool_call_timeout_seconds=10.0,
        whole_trial_timeout_seconds=30.0,
        multiple_tool_call_policy="serial",
        tool_error_reinsertion_policy="reinsert_raw",
        malformed_output_policy="syntax failure",
        terminal_response_policy="success",
        conversation_serialization_version=None,
        tool_result_serialization_version="tool-result-v1",
        parser_version="parser-v1",
        trial_stop_conditions=("success", "syntax failure", "semantic failure", "timeout", "maximum tool-call count", "infrastructure failure"),
        max_tool_calls_by_density={"D1": 1, "D3": 3, "D5": 4},
        timeout_subclasses=("model_generation_timeout", "tool_execution_timeout", "backend_hang_timeout", "reset_timeout"),
        forbidden_tool_names=("reset", "reset_state", "admin_reset", "set_schema_variant", "debug", "teardown"),
    )
    base.update(overrides)
    return FrozenStateMachineControls(**base)


def _tool_catalog(clock: FakeClock | None = None) -> dict[str, ToolSpecification]:
    def echo(arguments: dict[str, object]) -> str:
        if clock is not None:
            clock.advance(0.1)
        return f"echo:{arguments['value']}"

    def pair(arguments: dict[str, object]) -> dict[str, object]:
        if clock is not None:
            clock.advance(0.1)
        return {"left": arguments["left"], "right": arguments["right"]}

    return {
        "echo": ToolSpecification(
            exposed_tool_name="echo",
            logical_tool_name="logical_echo",
            required_arguments=("value",),
            handler=echo,
        ),
        "pair": ToolSpecification(
            exposed_tool_name="pair",
            logical_tool_name="logical_pair",
            required_arguments=("left", "right"),
            handler=pair,
        ),
    }


def _run(
    *,
    tmp_path: Path,
    suffix: str,
    backend_outputs: list[str],
    controls: FrozenStateMachineControls | None = None,
    budget_policy: TokenBudgetPolicy | None = None,
    clock: FakeClock | None = None,
    reset_error: Exception | None = None,
    advance_seconds: float = 0.0,
) -> tuple[AgentLoopExecutionRecord, FakeBackend, FakeResetExecutor, AttemptWorkspaceIsolation]:
    metadata, workspace = _workspace(tmp_path, suffix)
    fake_clock = clock or FakeClock()
    backend = FakeBackend(backend_outputs, fake_clock, advance_seconds=advance_seconds)
    reset_executor = FakeResetExecutor(workspace, error=reset_error)
    record = run_frozen_agent_loop(
        workspace=workspace,
        frozen_row=_trial_row(),
        task_description="Return the answer.",
        controls=controls or _controls(),
        backend=backend,
        tokenizer=FakeTokenizer(),
        budget_policy=budget_policy or TokenBudgetPolicy(input_limit=10_000, reserved_output_tokens=512),
        tool_catalog=_tool_catalog(fake_clock),
        reset_executor=reset_executor,
        retrieved_content=None,
        root=Path.cwd(),
        clock=fake_clock,
        allow_grading=False,
    )
    return record, backend, reset_executor, workspace


def test_agent_loop_terminal_answer_emits_expected_state_order(tmp_path: Path) -> None:
    record, backend, reset_executor, workspace = _run(
        tmp_path=tmp_path,
        suffix="terminal",
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
    )

    assert record.status == "PASS"
    assert record.termination_reason == "success"
    assert record.evidence_ready is True
    assert record.grader_invoked is False
    assert backend.calls[0]["history_id"] != 0
    assert reset_executor.calls == 2
    assert [item.state_code for item in record.state_transitions[:14]] == [
        "S0",
        "S1",
        "S2",
        "S3",
        "S4",
        "S5",
        "S6",
        "S7",
        "S8",
        "S9",
        "S10",
        "S11",
        "S12",
        "S13",
    ]
    assert record.state_transitions[-2].state_code == "S20"
    assert record.state_transitions[-1].state_code == "S21"
    assert (workspace.workspace_root / "parser_events.jsonl").is_file()
    assert (workspace.workspace_root / "model_outputs.jsonl").is_file()


def test_frozen_state_machine_control_loader_fails_closed() -> None:
    with pytest.raises(MissingFrozenSettingError):
        load_frozen_state_machine_controls()


def test_agent_loop_handles_one_and_multiple_tool_calls_in_parser_order(tmp_path: Path) -> None:
    record, backend, _, workspace = _run(
        tmp_path=tmp_path,
        suffix="multi",
        backend_outputs=[
            json.dumps(
                {
                    "tool_calls": [
                        {"tool_name": "echo", "arguments": {"value": "A"}, "tool_call_id": "call-1"},
                        {"tool_name": "pair", "arguments": {"left": "L", "right": "R"}, "tool_call_id": "call-2"},
                    ]
                },
                ensure_ascii=False,
            ),
            json.dumps({"terminal_response": "done"}, ensure_ascii=False),
        ],
    )

    assert record.status == "PASS"
    assert [item.exposed_tool_name for item in record.tool_results] == ["echo", "pair"]
    assert [call.tool_name for call in record.parsed_outputs[0].tool_calls] == ["echo", "pair"]
    assert backend.calls[0]["history_snapshot"] == ()
    assert (workspace.workspace_root / "tool_transcript.jsonl").is_file()


def test_agent_loop_rejects_malformed_hallucinated_and_missing_parameter_calls(tmp_path: Path) -> None:
    malformed, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="malformed",
        backend_outputs=["not-json"],
    )
    assert malformed.status == "FAIL"
    assert malformed.termination_reason == "syntax failure"

    hallucinated, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="hallucinated",
        backend_outputs=[json.dumps({"tool_calls": [{"tool_name": "hallucinated", "arguments": {}}]}, ensure_ascii=False)],
    )
    assert hallucinated.status == "FAIL"
    assert hallucinated.termination_reason == "semantic failure"

    missing, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="missing",
        backend_outputs=[json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {}}]}, ensure_ascii=False)],
    )
    assert missing.status == "FAIL"
    assert missing.termination_reason == "semantic failure"


def test_agent_loop_detects_repeated_loop_and_max_limits(tmp_path: Path) -> None:
    repeated, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="repeat",
        controls=_controls(max_identical_consecutive_tool_calls=1),
        backend_outputs=[
            json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "same"}}]}, ensure_ascii=False),
            json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "same"}}]}, ensure_ascii=False),
        ],
    )
    assert repeated.status == "FAIL"
    assert repeated.termination_reason == "repeated-call limit reached"

    max_turns, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="turns",
        controls=_controls(max_model_turns=1),
        backend_outputs=[json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "same"}}]}, ensure_ascii=False)],
    )
    assert max_turns.status == "FAIL"
    assert max_turns.termination_reason == "max model turns reached"

    max_calls, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="calls",
        controls=_controls(max_total_tool_calls=1),
        backend_outputs=[
            json.dumps(
                {
                    "tool_calls": [
                        {"tool_name": "echo", "arguments": {"value": "a"}},
                        {"tool_name": "pair", "arguments": {"left": "b", "right": "c"}},
                    ]
                },
                ensure_ascii=False,
            )
        ],
    )
    assert max_calls.status == "FAIL"
    assert max_calls.termination_reason == "maximum tool-call count"


def test_agent_loop_timeout_and_infrastructure_failures(tmp_path: Path) -> None:
    turn_clock = FakeClock()
    model_timeout, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="model-timeout",
        clock=turn_clock,
        advance_seconds=20.0,
        controls=_controls(per_model_turn_timeout_seconds=1.0),
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
    )
    assert model_timeout.status == "FAIL"
    assert model_timeout.termination_reason == "model_generation_timeout"

    tool_clock = FakeClock()
    tool_timeout, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="tool-timeout",
        clock=tool_clock,
        controls=_controls(per_tool_call_timeout_seconds=0.05),
        backend_outputs=[json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "A"}}]}, ensure_ascii=False)],
    )
    assert tool_timeout.status == "FAIL"
    assert tool_timeout.termination_reason == "tool_execution_timeout"

    model_time = FakeClock()
    with pytest.raises(ResetFailureError):
        _run(
            tmp_path=tmp_path,
            suffix="reset-failure",
            clock=model_time,
            reset_error=ResetFailureError("boom"),
            backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
        )


def test_agent_loop_rejects_token_overflow_and_no_session_reuse(tmp_path: Path) -> None:
    base_artifact = compile_frozen_prompt(
        task_description="Return the answer.",
        retrieved_content=None,
        history=(),
        tool_results=(),
        root=Path.cwd(),
        tokenizer=FakeTokenizer(),
        budget_policy=TokenBudgetPolicy(input_limit=10_000, reserved_output_tokens=512),
    )
    overflow_limit = base_artifact.prompt_token_count + 1
    overflow, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="overflow",
        controls=_controls(max_model_turns=4, max_identical_consecutive_tool_calls=4, max_identical_total_tool_calls=4),
        budget_policy=TokenBudgetPolicy(input_limit=overflow_limit, reserved_output_tokens=512),
        backend_outputs=[
            json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "A A A A"}}]}, ensure_ascii=False),
        ],
    )
    assert overflow.status == "FAIL"
    assert overflow.termination_reason == "model_created_loop_overflow"

    record_one, backend_one, _, _ = _run(
        tmp_path=tmp_path,
        suffix="reuse-1",
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
    )
    record_two, backend_two, _, _ = _run(
        tmp_path=tmp_path,
        suffix="reuse-2",
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
    )
    assert backend_one.calls[0]["history_snapshot"] == ()
    assert backend_two.calls[0]["history_snapshot"] == ()
    assert backend_one.calls[0]["session"] is not backend_two.calls[0]["session"]
    assert record_one.session_token != record_two.session_token


@pytest.mark.parametrize("failure_event", ["PREPARED", "DISPATCHED"])
def test_durability_failure_prevents_model_invocation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_event: str,
) -> None:
    backend_calls: list[int] = []
    original_append = __import__("phase5.runtime.agent_loop", fromlist=["AttemptEventLogWriter"]).AttemptEventLogWriter.append

    def fail_event_write(writer, event):
        if event.event_type.value == failure_event:
            raise OSError(f"synthetic {failure_event} durability failure")
        return original_append(writer, event)

    def record_generate(self, **kwargs):
        backend_calls.append(1)
        return json.dumps({"terminal_response": "done"})

    monkeypatch.setattr("phase5.runtime.agent_loop.AttemptEventLogWriter.append", fail_event_write)
    monkeypatch.setattr(FakeBackend, "generate", record_generate)

    with pytest.raises(OSError, match="durability failure"):
        _run(
            tmp_path=tmp_path,
            suffix=f"durability-{failure_event.lower()}",
            backend_outputs=[json.dumps({"terminal_response": "done"})],
        )
    assert backend_calls == []
