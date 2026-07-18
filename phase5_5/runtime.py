"""Phase 5.5 parser-to-dispatch evaluation boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from phase5.runtime.tool_dispatch import (
    ForbiddenToolCallError,
    MissingToolParameterError,
    ToolDispatchError,
    ToolDispatchPolicy,
    ToolDispatchRecord,
    ToolExecutionFailure,
    ToolSpecification,
    UnknownToolCallError,
    dispatch_tool_calls,
)

from .parser import ExtractionResult, GenerationEvidence, extract_tool_call


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Auditable outcome of one parser and dispatch boundary."""

    parser: ExtractionResult
    dispatch_records: tuple[ToolDispatchRecord, ...] = ()
    actual_logical_sequence: tuple[str, ...] = ()
    expected_logical_sequence: tuple[str, ...] = ()
    tool_selection_correct: bool = False
    argument_valid: bool = False
    model_competence_failure: bool = False
    infrastructure_failure: bool = False
    acceptance_status: str = "REJECTED"
    failure_reason: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @property
    def canonical_json_compliant(self) -> bool:
        return self.parser.canonical_json_compliant

    @property
    def privilege_aggregation_ready(self) -> bool:
        return bool(self.dispatch_records) and not self.infrastructure_failure

    def to_mapping(self) -> dict[str, Any]:
        return {
            "acceptance_status": self.acceptance_status,
            "actual_logical_sequence": list(self.actual_logical_sequence),
            "argument_valid": self.argument_valid,
            "canonical_json_compliant": self.canonical_json_compliant,
            "dispatch_records": [record.to_mapping() for record in self.dispatch_records],
            "expected_logical_sequence": list(self.expected_logical_sequence),
            "failure_reason": self.failure_reason,
            "infrastructure_failure": self.infrastructure_failure,
            "metadata": dict(self.metadata),
            "model_competence_failure": self.model_competence_failure,
            "parser": self.parser.to_mapping(),
            "privilege_aggregation_ready": self.privilege_aggregation_ready,
            "tool_selection_correct": self.tool_selection_correct,
        }


def evaluate_tool_output(
    raw_text: str,
    *,
    tool_catalog: Mapping[str, ToolSpecification],
    policy: ToolDispatchPolicy,
    expected_logical_sequence: Sequence[str] = (),
    parser_version: str = "phase5.5-parser-v1",
    generation_evidence: Mapping[str, Any] | GenerationEvidence | None = None,
    tool_result_serialization_version: str = "phase5.5-tool-result-v1",
) -> EvaluationResult:
    """Parse, validate, and dispatch one output without retries or repair."""

    parser = extract_tool_call(
        raw_text,
        parser_version=parser_version,
        generation_evidence=generation_evidence,
    )
    expected = tuple(expected_logical_sequence)
    if not parser.valid:
        return EvaluationResult(
            parser=parser,
            expected_logical_sequence=expected,
            model_competence_failure=True,
            acceptance_status="REJECTED",
            failure_reason=parser.diagnostic,
        )

    try:
        records = dispatch_tool_calls(
            (parser.parsed_call,),
            tool_catalog=tool_catalog,
            policy=policy,
            tool_result_serialization_version=tool_result_serialization_version,
        )
    except (ForbiddenToolCallError, MissingToolParameterError, UnknownToolCallError) as exc:
        return EvaluationResult(
            parser=parser,
            expected_logical_sequence=expected,
            model_competence_failure=True,
            acceptance_status="REJECTED",
            failure_reason=str(exc),
        )
    except (ToolExecutionFailure, ToolDispatchError) as exc:
        return EvaluationResult(
            parser=parser,
            expected_logical_sequence=expected,
            infrastructure_failure=True,
            acceptance_status="REJECTED",
            failure_reason=str(exc),
        )
    except Exception as exc:  # tool handlers are infrastructure boundaries
        return EvaluationResult(
            parser=parser,
            expected_logical_sequence=expected,
            infrastructure_failure=True,
            acceptance_status="REJECTED",
            failure_reason=f"tool handler failure: {exc}",
        )

    actual = tuple(record.logical_tool_name for record in records)
    selection_correct = not expected or actual == expected
    return EvaluationResult(
        parser=parser,
        dispatch_records=records,
        actual_logical_sequence=actual,
        expected_logical_sequence=expected,
        tool_selection_correct=selection_correct,
        argument_valid=True,
        acceptance_status="ACCEPTED" if selection_correct else "REJECTED",
        failure_reason=None if selection_correct else "logical tool sequence mismatch",
    )
