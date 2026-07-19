"""Frozen multi-turn agent loop and state-machine orchestration for Phase 5."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from time import monotonic
from typing import Any, Callable, Mapping, Protocol, Sequence

from ..domain.config import load_upstream_artifact_registry
from ..domain.errors import MissingFrozenSettingError, ResetFailureError, SchemaInvariantError
from ..domain.session import Phase5Session
from ..evidence import AttemptEvent, AttemptEventLogWriter, AttemptEventType
from ..evidence.io import append_jsonl_record
from ..evidence.workspace import AttemptWorkspaceMetadata
from ..guards import repo_root
from .parser_adapter import ParsedModelOutput, ParsedToolCall, serialize_parsed_output
from .prompt_compiler import CompiledPromptArtifact, compile_frozen_prompt
from .prompt_serialization import ConversationTurn
from .tool_dispatch import (
    ForbiddenToolCallError,
    MissingToolParameterError,
    ToolDispatchPolicy,
    ToolDispatchRecord,
    ToolExecutionFailure,
    ToolSpecification,
    UnknownToolCallError,
    dispatch_tool_calls,
)
from .token_budget import (
    DEFAULT_INPUT_TOKEN_LIMIT,
    DEFAULT_RESERVED_OUTPUT_TOKENS,
    InfrastructureOversizeError,
    OverflowClassification,
    TokenBudgetDecision,
    TokenBudgetExceededError,
    TokenBudgetPolicy,
    budget_decision_for_turn,
)


STATE_ORDER = (
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
    "S14",
    "S15",
    "S16",
    "S17",
    "S18",
    "S19",
    "S20",
    "S21",
    "S22",
    "S23",
    "S24",
    "S25",
    "S26",
    "S27",
)


@dataclass(frozen=True, slots=True)
class FrozenStateMachineControls:
    """Frozen state-machine limits and policies."""

    max_model_turns: int
    max_total_tool_calls: int
    max_identical_consecutive_tool_calls: int
    max_identical_total_tool_calls: int
    per_model_turn_timeout_seconds: float
    per_tool_call_timeout_seconds: float
    whole_trial_timeout_seconds: float
    multiple_tool_call_policy: str
    tool_error_reinsertion_policy: str
    malformed_output_policy: str
    terminal_response_policy: str
    conversation_serialization_version: str | None = None
    tool_result_serialization_version: str | None = None
    parser_version: str | None = None
    trial_stop_conditions: tuple[str, ...] = ()
    max_tool_calls_by_density: Mapping[str, int] = field(default_factory=dict)
    timeout_subclasses: tuple[str, ...] = ()
    forbidden_tool_names: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_model_turns <= 0:
            raise SchemaInvariantError("max_model_turns must be positive")
        if self.max_total_tool_calls <= 0:
            raise SchemaInvariantError("max_total_tool_calls must be positive")
        if self.max_identical_consecutive_tool_calls <= 0:
            raise SchemaInvariantError("max_identical_consecutive_tool_calls must be positive")
        if self.max_identical_total_tool_calls <= 0:
            raise SchemaInvariantError("max_identical_total_tool_calls must be positive")
        if self.per_model_turn_timeout_seconds <= 0:
            raise SchemaInvariantError("per_model_turn_timeout_seconds must be positive")
        if self.per_tool_call_timeout_seconds <= 0:
            raise SchemaInvariantError("per_tool_call_timeout_seconds must be positive")
        if self.whole_trial_timeout_seconds <= 0:
            raise SchemaInvariantError("whole_trial_timeout_seconds must be positive")
        if not isinstance(self.max_tool_calls_by_density, Mapping):
            raise SchemaInvariantError("max_tool_calls_by_density must be a mapping")
        for key, value in self.max_tool_calls_by_density.items():
            if not isinstance(key, str) or value <= 0:
                raise SchemaInvariantError("max_tool_calls_by_density must map density labels to positive integers")
        for value in self.trial_stop_conditions:
            if not isinstance(value, str) or not value:
                raise SchemaInvariantError("trial_stop_conditions must contain non-empty strings")
        for value in self.timeout_subclasses:
            if not isinstance(value, str) or not value:
                raise SchemaInvariantError("timeout_subclasses must contain non-empty strings")
        for value in self.forbidden_tool_names:
            if not isinstance(value, str) or not value:
                raise SchemaInvariantError("forbidden_tool_names must contain non-empty strings")
        for version_name, version_value in (
            ("multiple_tool_call_policy", self.multiple_tool_call_policy),
            ("tool_error_reinsertion_policy", self.tool_error_reinsertion_policy),
            ("malformed_output_policy", self.malformed_output_policy),
            ("terminal_response_policy", self.terminal_response_policy),
        ):
            if not isinstance(version_value, str) or not version_value:
                raise SchemaInvariantError(f"{version_name} must be a non-empty string")
        for label, value in (
            ("conversation_serialization_version", self.conversation_serialization_version),
            ("tool_result_serialization_version", self.tool_result_serialization_version),
            ("parser_version", self.parser_version),
        ):
            if value is not None and not isinstance(value, str):
                raise SchemaInvariantError(f"{label} must be a string or null")

    def max_tool_calls_for_density(self, density: str) -> int:
        try:
            return int(self.max_tool_calls_by_density[density])
        except KeyError as exc:
            raise MissingFrozenSettingError(f"missing tool-call limit for density {density!r}") from exc


@dataclass(frozen=True, slots=True)
class StateTransitionRecord:
    state_index: int
    state_code: str
    description: str
    timestamp_seconds: float
    details: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.state_index < 0:
            raise SchemaInvariantError("state_index must be non-negative")
        if not isinstance(self.state_code, str) or not self.state_code:
            raise SchemaInvariantError("state_code must be a non-empty string")
        if not isinstance(self.description, str) or not self.description:
            raise SchemaInvariantError("description must be a non-empty string")
        if self.timestamp_seconds < 0:
            raise SchemaInvariantError("timestamp_seconds must be non-negative")
        if not isinstance(self.details, Mapping):
            raise SchemaInvariantError("details must be a mapping")

    def to_mapping(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "details": dict(self.details),
            "state_code": self.state_code,
            "state_index": self.state_index,
            "timestamp_seconds": self.timestamp_seconds,
        }


@dataclass(frozen=True, slots=True)
class AgentLoopExecutionRecord:
    """Structured, evidence-ready record for a single P10 loop execution."""

    attempt_id: str
    frozen_row_id: str
    target_trial_id: str
    run_id: str
    batch_id: str
    session_token: str
    status: str
    termination_reason: str
    termination_state: str
    evidence_ready: bool
    grader_invoked: bool
    elapsed_seconds: float
    model_turn_count: int
    tool_call_count: int
    parsed_outputs: tuple[ParsedModelOutput, ...]
    tool_results: tuple[ToolDispatchRecord, ...]
    state_transitions: tuple[StateTransitionRecord, ...]
    prompt_artifact: CompiledPromptArtifact
    reset_notes: tuple[str, ...] = ()
    terminal_response: str | None = None
    notes: tuple[str, ...] = ()

    def to_mapping(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "batch_id": self.batch_id,
            "evidence_ready": self.evidence_ready,
            "elapsed_seconds": self.elapsed_seconds,
            "frozen_row_id": self.frozen_row_id,
            "grader_invoked": self.grader_invoked,
            "model_turn_count": self.model_turn_count,
            "notes": list(self.notes),
            "parsed_outputs": [item.to_mapping() for item in self.parsed_outputs],
            "prompt_artifact": self.prompt_artifact.metadata_mapping(),
            "reset_notes": list(self.reset_notes),
            "run_id": self.run_id,
            "session_token": self.session_token,
            "state_transitions": [item.to_mapping() for item in self.state_transitions],
            "status": self.status,
            "target_trial_id": self.target_trial_id,
            "terminal_response": self.terminal_response,
            "termination_reason": self.termination_reason,
            "termination_state": self.termination_state,
            "tool_call_count": self.tool_call_count,
            "tool_results": [item.to_mapping() for item in self.tool_results],
        }


class ModelBackend(Protocol):
    def generate(
        self,
        *,
        prompt_text: str,
        conversation_history: Sequence[ConversationTurn],
        session: Phase5Session,
        turn_index: int,
        controls: FrozenStateMachineControls,
    ) -> str | Mapping[str, Any]:
        ...


class ResetExecutor(Protocol):
    workspace: Any

    def execute(self, **kwargs: Any) -> Any:
        ...


def _load_int(value: Any, label: str) -> int:
    if not isinstance(value, int) or value <= 0:
        raise SchemaInvariantError(f"{label} must be a positive integer")
    return value


def _load_float(value: Any, label: str) -> float:
    if not isinstance(value, (int, float)) or value <= 0:
        raise SchemaInvariantError(f"{label} must be a positive number")
    return float(value)


def _load_string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise SchemaInvariantError(f"{label} must be a non-empty string")
    return value


def load_frozen_state_machine_controls(
    root: Path | None = None,
    *,
    registry_path: Path | None = None,
) -> FrozenStateMachineControls:
    """Load the frozen controls from the registry and fail closed on missing values."""

    repository_root = (root or repo_root()).resolve()
    registry_path = registry_path or repository_root / "phase5" / "configs" / "frozen_state_machine_controls_v2.json"
    if not registry_path.is_file():
        raise MissingFrozenSettingError(f"frozen state machine controls registry is missing: {registry_path.as_posix()}")
    
    with open(registry_path, "r", encoding="utf-8") as f:
        controls_data = json.load(f)
        
    return FrozenStateMachineControls(
        max_model_turns=_load_int(controls_data.get("max_model_turns"), "max_model_turns"),
        max_total_tool_calls=_load_int(controls_data.get("max_total_tool_calls"), "max_total_tool_calls"),
        max_identical_consecutive_tool_calls=_load_int(controls_data.get("max_identical_consecutive_tool_calls"), "max_identical_consecutive_tool_calls"),
        max_identical_total_tool_calls=_load_int(controls_data.get("max_identical_total_tool_calls"), "max_identical_total_tool_calls"),
        per_model_turn_timeout_seconds=_load_float(controls_data.get("per_model_turn_timeout_seconds"), "per_model_turn_timeout_seconds"),
        per_tool_call_timeout_seconds=_load_float(controls_data.get("per_tool_call_timeout_seconds"), "per_tool_call_timeout_seconds"),
        whole_trial_timeout_seconds=_load_float(controls_data.get("whole_trial_timeout_seconds"), "whole_trial_timeout_seconds"),
        multiple_tool_call_policy=_load_string(controls_data.get("multiple_tool_call_policy"), "multiple_tool_call_policy"),
        tool_error_reinsertion_policy=_load_string(controls_data.get("tool_error_reinsertion_policy"), "tool_error_reinsertion_policy"),
        malformed_output_policy=_load_string(controls_data.get("malformed_output_policy"), "malformed_output_policy"),
        terminal_response_policy=_load_string(controls_data.get("terminal_response_policy"), "terminal_response_policy"),
        conversation_serialization_version=controls_data.get("conversation_serialization_version"),
        tool_result_serialization_version=controls_data.get("tool_result_serialization_version"),
        parser_version=controls_data.get("parser_version"),
        trial_stop_conditions=tuple(controls_data.get("trial_stop_conditions", ())),
        max_tool_calls_by_density=controls_data.get("max_tool_calls_by_density", {}),
        timeout_subclasses=tuple(controls_data.get("timeout_subclasses", ())),
        forbidden_tool_names=tuple(controls_data.get("forbidden_tool_names", ()))
    )


def _state_transition(
    state_transitions: list[StateTransitionRecord],
    parser_events_path: Path,
    *,
    state_index: int,
    state_code: str,
    description: str,
    details: Mapping[str, Any] | None = None,
    clock: Callable[[], float] = monotonic,
) -> StateTransitionRecord:
    record = StateTransitionRecord(
        state_index=state_index,
        state_code=state_code,
        description=description,
        timestamp_seconds=clock(),
        details=details or {},
    )
    state_transitions.append(record)
    append_jsonl_record(parser_events_path, {"event_type": "STATE_TRANSITION", **record.to_mapping()})
    return record


def _frozen_row_snapshot(row: Any) -> dict[str, Any]:
    def _value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    fields = (
        "phase",
        "official_trial",
        "trial_id",
        "run_id",
        "branch",
        "git_commit_hash",
        "timestamp_utc",
        "model_id",
        "exact_model_identifier",
        "model_digest",
        "quantization",
        "backend",
        "backend_version",
        "ollama_version",
        "density",
        "metadata_surface_condition",
        "attack_family",
        "defense_condition",
        "payload_id",
        "phase1_payload_hash",
        "payload_hash",
        "adversarial_payload_present",
        "payload_condition",
    )
    snapshot = {}
    for field_name in fields:
        snapshot[field_name] = _value(getattr(row, field_name))
    return snapshot


def _build_event(
    workspace: AttemptWorkspaceMetadata,
    *,
    event_sequence: int,
    event_type: AttemptEventType,
    artifact_ref: str | None = None,
    artifact_sha256: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> AttemptEvent:
    from ..domain.identifiers import EventId

    return AttemptEvent(
        event_id=EventId.build(workspace.attempt_id, event_sequence),
        dataset_version=workspace.dataset_version,
        frozen_row_id=workspace.frozen_row_id,
        target_trial_id=workspace.target_trial_id,
        attempt_id=workspace.attempt_id,
        run_id=workspace.run_id,
        batch_id=workspace.batch_id,
        event_sequence=event_sequence,
        event_type=event_type,
        timestamp_utc=f"2026-07-08T00:00:{event_sequence:02d}Z",
        artifact_ref=artifact_ref,
        artifact_sha256=artifact_sha256,
        details=dict(details or {}),
    )


def _check_timeout(elapsed_seconds: float, limit_seconds: float, *, label: str) -> None:
    if elapsed_seconds > limit_seconds:
        raise TimeoutError(f"{label} exceeded frozen limit by {elapsed_seconds - limit_seconds:.6f} seconds")


def _write_jsonl_record(path: Path, payload: Mapping[str, Any]) -> None:
    append_jsonl_record(path, payload)


def run_frozen_agent_loop(
    *,
    workspace: Any,
    frozen_row: Any,
    task_description: str,
    controls: FrozenStateMachineControls,
    backend: ModelBackend,
    tokenizer: Any,
    budget_policy: TokenBudgetPolicy,
    tool_catalog: Mapping[str, ToolSpecification],
    mcp_discovery: Mapping[str, Any] | None = None,
    task_execution_plan: Sequence[Mapping[str, Any]] | None = None,
    reset_executor: ResetExecutor,
    retrieved_content: str | None = None,
    root: Path | None = None,
    clock: Callable[[], float] = monotonic,
    allow_grading: bool = False,
    grade_callable: Callable[[], Any] | None = None,
    tid_callable: Callable[[], Any] | None = None,
    materialize_callable: Callable[[], Any] | None = None,
    validate_callable: Callable[[], Any] | None = None,
    finalize_callable: Callable[[], Any] | None = None,
    lineage_callable: Callable[[], Any] | None = None,
) -> AgentLoopExecutionRecord:
    """Run the frozen multi-turn loop until evidence-ready termination."""

    from phase5_5.parser import extract_tool_call

    if getattr(reset_executor, "workspace", None) is not None and reset_executor.workspace != workspace:
        raise SchemaInvariantError("reset executor workspace does not match the attempt workspace")

    workspace.materialize()
    session = Phase5Session.initial()
    session_token = uuid.uuid4().hex[:8].upper()
    state_transitions: list[StateTransitionRecord] = []
    parser_events_path = workspace.workspace_root / "parser_events.jsonl"
    model_outputs_path = workspace.workspace_root / "model_outputs.jsonl"
    tool_transcript_path = workspace.workspace_root / "tool_transcript.jsonl"
    workspace.write_text_snapshot(tool_transcript_path.name, "")
    event_writer = AttemptEventLogWriter(workspace.metadata.event_log_path)
    history: list[ConversationTurn] = []
    tool_results: list[ConversationTurn] = []
    parsed_outputs: list[ParsedModelOutput] = []
    tool_records: list[ToolDispatchRecord] = []
    reset_notes: list[str] = []
    notes: list[str] = []
    turn_count = 0
    tool_call_count = 0
    identical_consecutive_calls = 0
    last_signature: tuple[str, str] | None = None
    identical_total_calls: dict[tuple[str, str], int] = {}
    whole_trial_started = clock()
    event_sequence = 0

    def emit_attempt_event(
        *,
        event_type: AttemptEventType,
        artifact_ref: str | None = None,
        artifact_sha256: str | None = None,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        nonlocal event_sequence
        event_sequence += 1
        event_writer.append(
            _build_event(
                workspace.metadata,
                event_sequence=event_sequence,
                event_type=event_type,
                artifact_ref=artifact_ref,
                artifact_sha256=artifact_sha256,
                details=details,
            )
        )

    _state_transition(state_transitions, parser_events_path, state_index=0, state_code="S0", description="LOAD_FROZEN_ROW")
    if frozen_row is None:
        raise MissingFrozenSettingError("frozen row is required")
    workspace.write_json_snapshot("frozen_row_snapshot.json", _frozen_row_snapshot(frozen_row))
    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=1,
        state_code="S1",
        description="VERIFY_ROW_AND_HASHES",
        details={"frozen_row_id": frozen_row.trial_id.value if hasattr(frozen_row, "trial_id") else None},
    )

    _state_transition(state_transitions, parser_events_path, state_index=2, state_code="S2", description="CREATE_ATTEMPT_WORKSPACE")
    workspace.metadata.write_manifest()
    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=3,
        state_code="S3",
        description="START_OR_VERIFY_MCP_PROCESS",
        details={"tool_names": sorted(tool_catalog)},
    )

    _state_transition(state_transitions, parser_events_path, state_index=4, state_code="S4", description="PRE_TRIAL_RESET")
    try:
        reset_result = reset_executor.execute(
            mock_sinks={},
            event_log=[],
            temp_paths=(),
            server_state={},
            conversation_state={},
        )
        reset_notes.extend(getattr(reset_result, "notes", ()))
    except ResetFailureError:
        raise
    except Exception as exc:
        raise ResetFailureError(f"reset executor failed: {exc}") from exc

    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=5,
        state_code="S5",
        description="VERIFY_RESET_AND_DISCOVERY_INVARIANTS",
        details={"reset_status": getattr(reset_result, "status", None)},
    )

    prompt_artifact = compile_frozen_prompt(
        task_description=task_description,
        retrieved_content=retrieved_content,
        history=history,
        tool_results=tool_results,
        root=root,
        tokenizer=tokenizer,
        budget_policy=budget_policy,
        mcp_discovery=mcp_discovery,
        task_execution_plan=task_execution_plan,
    )
    prompt_paths = prompt_artifact.write(workspace.workspace_root)
    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=6,
        state_code="S6",
        description="COMPILE_INITIAL_CONTEXT",
        details={"prompt_sha256": prompt_artifact.prompt_sha256},
    )

    if not prompt_artifact.prompt_budget_decision.allowed:
        classification = prompt_artifact.prompt_budget_decision.classification
        if classification is None:
            raise SchemaInvariantError("budget overflow classification is missing")
        raise SchemaInvariantError(f"initial prompt overflow: {classification.value}")

    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=7,
        state_code="S7",
        description="VERIFY_INITIAL_TOKEN_BUDGET",
        details=prompt_artifact.prompt_budget_decision.to_mapping(),
    )
    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=8,
        state_code="S8",
        description="WRITE_RAW_PROMPT_AND_PREPARED_EVENT",
        details={"compiled_prompt_path": prompt_paths[0].as_posix()},
    )
    emit_attempt_event(
        event_type=AttemptEventType.PREPARED,
        artifact_ref=prompt_paths[0].as_posix(),
        artifact_sha256=prompt_artifact.prompt_sha256,
        details={"state": "S8"},
    )

    termination_reason = ""
    termination_state = ""
    terminal_response: str | None = None
    evidence_ready = False
    grader_invoked = False

    while True:
        if turn_count >= controls.max_model_turns:
            termination_reason = "max model turns reached"
            termination_state = "S19"
            break

        if clock() - whole_trial_started > controls.whole_trial_timeout_seconds:
            termination_reason = "whole-trial timeout"
            termination_state = "S19"
            break

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=9,
            state_code="S9",
            description="WRITE_AND_FSYNC_DISPATCHED_EVENT",
            details={"turn_index": turn_count},
        )
        emit_attempt_event(
            event_type=AttemptEventType.DISPATCHED,
            artifact_ref=prompt_paths[0].as_posix(),
            artifact_sha256=prompt_artifact.prompt_sha256,
            details={"state": "S9", "turn_index": turn_count},
        )

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=10,
            state_code="S10",
            description="MODEL_INFERENCE_TURN",
            details={"turn_index": turn_count},
        )
        start = clock()
        try:
            raw_model_output = backend.generate(
                prompt_text=prompt_artifact.prompt_text,
                conversation_history=tuple(history),
                session=session,
                turn_index=turn_count,
                controls=controls,
            )
        except Exception as exc:
            raise RuntimeError(f"backend crash: {type(exc).__name__}: {exc}") from exc
        model_elapsed = clock() - start
        try:
            _check_timeout(model_elapsed, controls.per_model_turn_timeout_seconds, label="model turn")
        except TimeoutError:
            termination_reason = "model_generation_timeout"
            termination_state = "S10"
            break

        if clock() - whole_trial_started > controls.whole_trial_timeout_seconds:
            termination_reason = "whole-trial timeout"
            termination_state = "S11"
            break

        raw_output_text = raw_model_output if isinstance(raw_model_output, str) else json.dumps(
            raw_model_output, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=11,
            state_code="S11",
            description="CAPTURE_AND_FSYNC_RAW_OUTPUT",
            details={"turn_index": turn_count, "byte_length": len(raw_output_text.encode("utf-8"))},
        )
        output_record = {
            "raw_output": raw_output_text,
            "session_token": session_token,
            "turn_index": turn_count,
            "elapsed_seconds": model_elapsed,
        }
        generation_receipt = getattr(backend, "last_generation_receipt", None)
        if generation_receipt is not None:
            output_record["generation_receipt"] = dict(generation_receipt)
        append_jsonl_record(
            model_outputs_path,
            output_record,
        )
        emit_attempt_event(
            event_type=AttemptEventType.MODEL_OUTPUT_CAPTURED,
            artifact_ref=None,
            artifact_sha256=None,
            details={"state": "S11", "turn_index": turn_count},
        )

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=12,
            state_code="S12",
            description="PARSE_MODEL_OUTPUT",
            details={"turn_index": turn_count},
        )
        parser_result = extract_tool_call(
            raw_output_text,
            parser_version=controls.parser_version or "phase5.5-parser-v1",
            generation_evidence=generation_receipt,
            tool_schemas=tool_catalog,
            forbidden_tool_names=controls.forbidden_tool_names,
        )
        terminal_from_parser = parser_result.metadata.get("terminal_response")
        parser_is_terminal = not parser_result.valid and isinstance(terminal_from_parser, str)
        if parser_is_terminal:
            parsed_output = ParsedModelOutput(
                raw_text=raw_output_text,
                parser_version=controls.parser_version,
                terminal_response=terminal_from_parser,
                tool_calls=(),
                metadata={"phase5_5_parser_status": parser_result.status.value},
                payload={},
            )
        elif not parser_result.valid:
            exc = parser_result.diagnostic or parser_result.status.value
            termination_reason = (
                "semantic failure"
                if parser_result.status.value == "SCHEMA_INVALID_CALL"
                else controls.malformed_output_policy
            )
            termination_state = "S12"
            notes.append(f"{parser_result.status.value}: {exc}")
            append_jsonl_record(
                parser_events_path,
                {
                    "event_type": "PARSE_FAILURE",
                    "reason": parser_result.status.value,
                    "details": exc,
                    "turn_index": turn_count,
                    "candidate_count": parser_result.candidate_count,
                    "parser_version": parser_result.parser_version,
                    "native_format": parser_result.native_format,
                    "canonical_json_compliant": parser_result.canonical_json_compliant,
                },
            )
            break
        else:
            parsed_output = ParsedModelOutput(
                raw_text=raw_output_text,
                parser_version=controls.parser_version,
                terminal_response=None,
                tool_calls=parser_result.parsed_calls,
                metadata={
                    "phase5_5_parser_status": parser_result.status.value,
                    "canonical_json_compliant": parser_result.canonical_json_compliant,
                    "candidate_spans": [list(span) for span in parser_result.candidate_spans],
                },
                payload={},
            )
        parsed_outputs.append(parsed_output)
        history.append(
            ConversationTurn(
                turn_index=turn_count,
                role="assistant",
                content=parsed_output.raw_text,
                turn_kind="model_output",
                metadata={
                    "parser_version": controls.parser_version,
                    "phase5_5_parser_status": parser_result.status.value,
                },
            )
        )
        append_jsonl_record(
            parser_events_path,
            {
                "event_type": "PARSE_COMPLETED",
                "turn_index": turn_count,
                "parser_version": parser_result.parser_version,
                "status": parser_result.status.value,
                "native_format": parser_result.native_format,
                "canonical_json_compliant": parser_result.canonical_json_compliant,
                "parsed_output": json.loads(serialize_parsed_output(parsed_output)),
            },
        )
        emit_attempt_event(
            event_type=AttemptEventType.PARSE_COMPLETED,
            artifact_ref=None,
            artifact_sha256=None,
            details={"state": "S12", "turn_index": turn_count},
        )

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=13,
            state_code="S13",
            description="TERMINAL_RESPONSE_CHECK",
            details={"terminal_response": parsed_output.terminal_response},
        )
        if parsed_output.is_terminal:
            terminal_response = parsed_output.terminal_response
            termination_reason = controls.terminal_response_policy
            termination_state = "S13"
            turn_count += 1
            emit_attempt_event(
                event_type=AttemptEventType.TURN_COMPLETED,
                details={"turn_index": turn_count, "terminal": True},
            )
            break
        if parsed_output.terminal_response is not None and parsed_output.tool_calls:
            termination_reason = controls.malformed_output_policy
            termination_state = "S13"
            break

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=14,
            state_code="S14",
            description="TOOL_CALL_POLICY_CHECK",
            details={"tool_call_count": len(parsed_output.tool_calls)},
        )
        if parsed_output.tool_calls:
            if controls.multiple_tool_call_policy == "reject" and len(parsed_output.tool_calls) > 1:
                termination_reason = "semantic failure"
                termination_state = "S14"
                notes.append("multiple tool calls rejected by frozen policy")
                break
            tool_call_count += len(parsed_output.tool_calls)
            if tool_call_count > controls.max_total_tool_calls:
                termination_reason = "maximum tool-call count"
                termination_state = "S14"
                break
        if parsed_output.tool_calls:
            call_signature = tuple(
                (call.tool_name, json.dumps(call.arguments, sort_keys=True, separators=(",", ":")))
                for call in parsed_output.tool_calls
            )
            for signature in call_signature:
                identical_total_calls[signature] = identical_total_calls.get(signature, 0) + 1
                if identical_total_calls[signature] > controls.max_identical_total_tool_calls:
                    termination_reason = "repeated-call limit reached"
                    termination_state = "S14"
                    break
            if termination_reason:
                break
            if len(call_signature) == 1:
                signature = call_signature[0]
                identical_consecutive_calls = identical_consecutive_calls + 1 if last_signature == signature else 1
                last_signature = signature
                if identical_consecutive_calls > controls.max_identical_consecutive_tool_calls:
                    termination_reason = "repeated-call limit reached"
                    termination_state = "S14"
                    break
            else:
                identical_consecutive_calls = 0
                last_signature = None

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=15,
            state_code="S15",
            description="DISPATCH_TOOL_CALLS_SERIALIZED",
            details={"tool_calls": [item.to_mapping() for item in parsed_output.tool_calls]},
        )
        try:
            dispatch_policy = ToolDispatchPolicy(
                multiple_tool_call_policy=controls.multiple_tool_call_policy,
                tool_error_reinsertion_policy=controls.tool_error_reinsertion_policy,
                forbidden_tool_names=controls.forbidden_tool_names,
                max_total_tool_calls=controls.max_total_tool_calls,
                max_identical_consecutive_tool_calls=controls.max_identical_consecutive_tool_calls,
                max_identical_total_tool_calls=controls.max_identical_total_tool_calls,
            )
            tool_results_batch = dispatch_tool_calls(
                parsed_output.tool_calls,
                tool_catalog=tool_catalog,
                policy=dispatch_policy,
                tool_result_serialization_version=controls.tool_result_serialization_version,
                clock=clock,
            )
        except (ForbiddenToolCallError, UnknownToolCallError, MissingToolParameterError) as exc:
            termination_reason = "semantic failure"
            termination_state = "S15"
            notes.append(str(exc))
            break
        except ToolExecutionFailure as exc:
            termination_reason = "infrastructure failure"
            termination_state = "S15"
            notes.append(str(exc))
            break

        if any(record.elapsed_seconds > controls.per_tool_call_timeout_seconds for record in tool_results_batch):
            termination_reason = "tool_execution_timeout"
            termination_state = "S16"
            break

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=16,
            state_code="S16",
            description="CAPTURE_TOOL_EVENTS_AND_RESULTS",
            details={"tool_calls": len(tool_results_batch)},
        )
        for record in tool_results_batch:
            tool_records.append(record)
            append_jsonl_record(tool_transcript_path, record.to_mapping())
            emit_attempt_event(
                event_type=AttemptEventType.TOOL_EVENT,
                artifact_ref=None,
                artifact_sha256=None,
                details={"tool_name": record.exposed_tool_name, "logical_tool_name": record.logical_tool_name},
            )
            emit_attempt_event(
                event_type=AttemptEventType.TOOL_RESULT_CAPTURED,
                artifact_ref=None,
                artifact_sha256=None,
                details={"tool_name": record.exposed_tool_name, "logical_tool_name": record.logical_tool_name},
            )

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=17,
            state_code="S17",
            description="APPEND_FROZEN_TOOL_RESULT_SERIALIZATION",
            details={"tool_results": [item.to_mapping() for item in tool_results_batch]},
        )
        for record in tool_results_batch:
            tool_results.append(record.to_conversation_turn(tool_result_serialization_version=controls.tool_result_serialization_version))

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=18,
            state_code="S18",
            description="VERIFY_NEXT_TURN_TOKEN_BUDGET",
            details={"turn_index": turn_count},
        )
        try:
            next_prompt = compile_frozen_prompt(
                task_description=task_description,
                retrieved_content=retrieved_content,
                history=history,
                tool_results=tool_results,
                root=root,
                tokenizer=tokenizer,
                budget_policy=budget_policy,
                mcp_discovery=mcp_discovery,
                task_execution_plan=task_execution_plan,
            )
        except TokenBudgetExceededError:
            termination_reason = OverflowClassification.MODEL_CREATED_LOOP_OVERFLOW.value
            termination_state = "S18"
            notes.append("next turn would exceed the frozen token budget")
            break
        except InfrastructureOversizeError:
            termination_reason = OverflowClassification.INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT.value
            termination_state = "S18"
            notes.append("infrastructure generated an oversized tool result")
            break
        if not next_prompt.prompt_budget_decision.allowed:
            classification = next_prompt.prompt_budget_decision.classification or OverflowClassification.MODEL_CREATED_LOOP_OVERFLOW
            termination_reason = classification.value
            termination_state = "S18"
            notes.append("next turn would exceed the frozen token budget")
            break
        prompt_artifact = next_prompt

        if clock() - whole_trial_started > controls.whole_trial_timeout_seconds:
            termination_reason = "whole-trial timeout"
            termination_state = "S18"
            break

        _state_transition(
            state_transitions,
            parser_events_path,
            state_index=19,
            state_code="S19",
            description="LOOP_TO_S9_OR_TERMINATE",
            details={"next_turn": turn_count + 1},
        )
        turn_count += 1
        emit_attempt_event(
            event_type=AttemptEventType.TURN_COMPLETED,
            artifact_ref=None,
            artifact_sha256=None,
            details={"turn_index": turn_count},
        )
        continue

        # Unreachable by design. The loop exits on one of the frozen terminal conditions.

    emit_attempt_event(
        event_type=AttemptEventType.TERMINATED,
        details={"termination_reason": termination_reason, "termination_state": termination_state},
    )

    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=20,
        state_code="S20",
        description="POST_TRIAL_RESET",
        details={"termination_reason": termination_reason},
    )
    try:
        post_reset = reset_executor.execute(
            mock_sinks={},
            event_log=[],
            temp_paths=(),
            server_state={},
            conversation_state={},
        )
        reset_notes.extend(getattr(post_reset, "notes", ()))
    except Exception as exc:
        raise ResetFailureError(f"post-trial reset failed: {exc}") from exc

    _state_transition(
        state_transitions,
        parser_events_path,
        state_index=21,
        state_code="S21",
        description="RESET_INTEGRITY_CHECK",
        details={"reset_status": getattr(post_reset, "status", None)},
    )
    if getattr(post_reset, "status", None) not in {"PASS", "QUARANTINED"}:
        raise ResetFailureError(f"reset integrity check failed: {getattr(post_reset, 'status', None)!r}")
    emit_attempt_event(
        event_type=AttemptEventType.RESET_CHECKED,
        details={"status": getattr(post_reset, "status", None)},
    )

    evidence_ready = True
    if allow_grading:
        if not all((grade_callable, tid_callable, materialize_callable, validate_callable, finalize_callable, lineage_callable)):
            raise MissingFrozenSettingError("grading hooks are required when allow_grading is enabled")
        _state_transition(state_transitions, parser_events_path, state_index=22, state_code="S22", description="FROZEN_GRADING")
        grade_callable()
        emit_attempt_event(event_type=AttemptEventType.GRADED, details={"state": "S22"})
        _state_transition(state_transitions, parser_events_path, state_index=23, state_code="S23", description="FROZEN_TID_CALCULATION")
        tid_callable()
        _state_transition(state_transitions, parser_events_path, state_index=24, state_code="S24", description="MATERIALIZE_FROZEN_SCHEMA_ROW")
        materialize_callable()
        emit_attempt_event(event_type=AttemptEventType.TRIAL_ROW_MATERIALIZED, details={"state": "S24"})
        _state_transition(state_transitions, parser_events_path, state_index=25, state_code="S25", description="VALIDATE_SCHEMA_AND_INVARIANTS")
        validate_callable()
        _state_transition(state_transitions, parser_events_path, state_index=26, state_code="S26", description="FINALIZE_AND_FSYNC")
        finalize_callable()
        emit_attempt_event(event_type=AttemptEventType.FINALIZED, details={"state": "S26"})
        _state_transition(state_transitions, parser_events_path, state_index=27, state_code="S27", description="UPDATE_LINEAGE_AND_MANIFEST")
        lineage_callable()
        grader_invoked = True

    total_elapsed = clock() - whole_trial_started
    return AgentLoopExecutionRecord(
        attempt_id=workspace.metadata.attempt_id,
        frozen_row_id=workspace.metadata.frozen_row_id,
        target_trial_id=workspace.metadata.target_trial_id,
        run_id=workspace.metadata.run_id,
        batch_id=workspace.metadata.batch_id,
        session_token=session_token,
        status="PASS" if evidence_ready and termination_reason == controls.terminal_response_policy else "FAIL",
        termination_reason=termination_reason,
        termination_state=termination_state,
        evidence_ready=evidence_ready,
        grader_invoked=grader_invoked,
        elapsed_seconds=total_elapsed,
        model_turn_count=turn_count,
        tool_call_count=tool_call_count,
        parsed_outputs=tuple(parsed_outputs),
        tool_results=tuple(tool_records),
        state_transitions=tuple(state_transitions),
        prompt_artifact=prompt_artifact,
        reset_notes=tuple(reset_notes),
        terminal_response=terminal_response,
        notes=tuple(notes),
    )
