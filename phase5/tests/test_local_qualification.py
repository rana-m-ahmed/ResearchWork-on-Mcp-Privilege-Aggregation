from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from phase5.campaign import run_campaign
from phase5.domain import FrozenTrialRow, ModelSlot, Phase5Session, SessionState
from phase5.domain.errors import ResetFailureError, RuntimeMismatchError, SchemaInvariantError
from phase5.evidence.workspace import AttemptWorkspaceMetadata
from phase5.guards import scan_text_for_forbidden_analysis, scan_text_for_secrets
from phase5.runtime import (
    AttemptWorkspaceIsolation,
    FrozenStateMachineControls,
    McpServerLauncher,
    TokenBudgetPolicy,
    ToolSpecification,
    compile_frozen_prompt,
    discover_tool_names,
    probe_reset_dispatch,
    run_frozen_agent_loop,
)
from phase5.sync.github_checkpoint import perform_session_reverify, perform_sync_github
from server.mock_server import build_server


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
    def __init__(
        self,
        workspace: AttemptWorkspaceIsolation,
        *,
        outcome: FakeResetOutcome | None = None,
        error: Exception | None = None,
    ) -> None:
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
    def __init__(self, outputs: list[object], clock: FakeClock | None = None, advance_seconds: float = 0.0) -> None:
        self.outputs = list(outputs)
        self.clock = clock
        self.advance_seconds = advance_seconds
        self.calls: list[dict[str, object]] = []

    def generate(self, *, prompt_text: str, conversation_history, session, turn_index: int, controls) -> str | dict[str, object]:
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
        next_output = self.outputs.pop(0)
        if isinstance(next_output, Exception):
            raise next_output
        return next_output


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


def _tool_catalog(tool_sink: list[str] | None = None, clock: FakeClock | None = None) -> dict[str, ToolSpecification]:
    sink = tool_sink if tool_sink is not None else []

    def read(arguments: dict[str, object]) -> dict[str, object]:
        if clock is not None:
            clock.advance(0.1)
        return {"key": arguments["key"], "source": "local-mcp"}

    def write(arguments: dict[str, object]) -> dict[str, object]:
        if clock is not None:
            clock.advance(0.1)
        sink.append(str(arguments["value"]))
        return {"written": arguments["value"]}

    def echo(arguments: dict[str, object]) -> str:
        if clock is not None:
            clock.advance(0.1)
        return f"echo:{arguments['value']}"

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
            handler=lambda arguments: {"left": arguments["left"], "right": arguments["right"]},
        ),
        "read": ToolSpecification(
            exposed_tool_name="read",
            logical_tool_name="logical_read",
            required_arguments=("key",),
            handler=read,
        ),
        "write": ToolSpecification(
            exposed_tool_name="write",
            logical_tool_name="logical_write",
            required_arguments=("value",),
            handler=write,
        ),
    }


def _run(
    *,
    tmp_path: Path,
    suffix: str,
    backend_outputs: list[object],
    controls: FrozenStateMachineControls | None = None,
    budget_policy: TokenBudgetPolicy | None = None,
    clock: FakeClock | None = None,
    reset_error: Exception | None = None,
    advance_seconds: float = 0.0,
    allow_grading: bool = False,
    grade_log: list[str] | None = None,
    tool_sink: list[str] | None = None,
) -> tuple[object, FakeBackend, FakeResetExecutor, AttemptWorkspaceIsolation]:
    _, workspace = _workspace(tmp_path, suffix)
    fake_clock = clock or FakeClock()
    backend = FakeBackend(backend_outputs, fake_clock, advance_seconds=advance_seconds)
    reset_executor = FakeResetExecutor(workspace, error=reset_error)
    grading_log = grade_log if grade_log is not None else []
    record = run_frozen_agent_loop(
        workspace=workspace,
        frozen_row=_trial_row(),
        task_description="Return the answer.",
        controls=controls or _controls(),
        backend=backend,
        tokenizer=FakeTokenizer(),
        budget_policy=budget_policy or TokenBudgetPolicy(input_limit=10_000, reserved_output_tokens=512),
        tool_catalog=_tool_catalog(tool_sink, fake_clock),
        reset_executor=reset_executor,
        retrieved_content=None,
        root=Path.cwd(),
        clock=fake_clock,
        allow_grading=allow_grading,
        grade_callable=(lambda: grading_log.append("grade")) if allow_grading else None,
        tid_callable=(lambda: grading_log.append("tid")) if allow_grading else None,
        materialize_callable=(lambda: grading_log.append("materialize")) if allow_grading else None,
        validate_callable=(lambda: grading_log.append("validate")) if allow_grading else None,
        finalize_callable=(lambda: grading_log.append("finalize")) if allow_grading else None,
        lineage_callable=(lambda: grading_log.append("lineage")) if allow_grading else None,
    )
    return record, backend, reset_executor, workspace


def _state_codes(record: object) -> set[str]:
    return {transition.state_code for transition in getattr(record, "state_transitions")}


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=False, env=env)


def _run_git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = _git(repo, *args, env=env)
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _init_git_repo(tmp_path: Path) -> tuple[Path, Path, str]:
    remote = tmp_path / "remote.git"
    repo = tmp_path / "repo"
    _run_git(tmp_path, "init", "--bare", remote.as_posix())
    _run_git(tmp_path, "init", repo.as_posix())
    _run_git(repo, "config", "user.name", "Phase 5 Sync")
    _run_git(repo, "config", "user.email", "phase5-sync@example.invalid")
    _run_git(repo, "remote", "add", "origin", remote.as_posix())

    (repo / "phase5" / "implementation" / "reports").mkdir(parents=True, exist_ok=True)
    (repo / "phase5" / "configs").mkdir(parents=True, exist_ok=True)
    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v1\"}\n",
        encoding="utf-8",
    )
    (repo / "phase5" / "configs" / "runtime.json").write_text("{\"runtime\":\"ok\"}\n", encoding="utf-8")
    _run_git(repo, "add", ".")
    _run_git(repo, "commit", "-m", "initial")
    _run_git(repo, "branch", "-M", "evidence")
    _run_git(repo, "push", "-u", "origin", "evidence")
    _run_git(tmp_path, "--git-dir", remote.as_posix(), "symbolic-ref", "HEAD", "refs/heads/evidence")
    initial_sha = _run_git(repo, "rev-parse", "HEAD")
    return repo, remote, initial_sha


def _write_sync_allowlist(path: Path) -> None:
    path.write_text(
        "allowed_staged_prefixes:\n"
        "  - phase5/implementation/reports/\n"
        "  - phase5/checkpoints/\n"
        "  - phase5/evidence/\n"
        "  - phase5/manifests/\n",
        encoding="utf-8",
    )


def _write_sync_manifest(repo: Path, *, source_commit: str, remote_head: str, manifest_path: Path) -> None:
    artifact_path = Path("phase5/implementation/reports/artifact.json")
    runtime_path = Path("phase5/configs/runtime.json")
    manifest = {
        "run_id": "run-001",
        "batch_id": "batch-001",
        "remote_name": "origin",
        "branch": "evidence",
        "commit_utc": "2026-07-08T00:00:00Z",
        "source_commit": source_commit,
        "common_source_hash": "a" * 64,
        "expected_remote_head_before_push": remote_head,
        "runtime_config_path": runtime_path.as_posix(),
        "runtime_config_sha256": _sha256(repo / runtime_path),
        "frozen_hashes": {
            artifact_path.as_posix(): _sha256(repo / artifact_path),
        },
        "allowed_staged_prefixes": [
            "phase5/implementation/reports/",
            "phase5/checkpoints/",
            "phase5/evidence/",
            "phase5/manifests/",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, sort_keys=True, indent=2), encoding="utf-8")


def _write_pre_receive_hook(remote: Path) -> None:
    hook = remote / "hooks" / "pre-receive"
    hook.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")


def _write_post_receive_reset_hook(remote: Path, branch: str, sha: str) -> None:
    hook = remote / "hooks" / "post-receive"
    hook.write_text(
        "#!/bin/sh\n"
        f"git update-ref refs/heads/{branch} {sha}\n",
        encoding="utf-8",
    )


def test_p16_local_e2e_suite_covers_full_state_machine(tmp_path: Path) -> None:
    grading_log: list[str] = []
    success_record, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="success",
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
        allow_grading=True,
        grade_log=grading_log,
    )
    assert success_record.status == "PASS"
    assert success_record.grader_invoked is True
    assert grading_log == ["grade", "tid", "materialize", "validate", "finalize", "lineage"]
    assert {"S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13", "S20", "S21", "S22", "S23", "S24", "S25", "S26", "S27"} <= _state_codes(success_record)

    sink: list[str] = []
    tool_record, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="tools",
        backend_outputs=[
            json.dumps({"tool_calls": [{"tool_name": "read", "arguments": {"key": "alpha"}}]}, ensure_ascii=False),
            json.dumps({"tool_calls": [{"tool_name": "write", "arguments": {"value": "alpha"}}]}, ensure_ascii=False),
            json.dumps({"terminal_response": "done"}, ensure_ascii=False),
        ],
        controls=_controls(max_model_turns=6, max_total_tool_calls=6, max_identical_consecutive_tool_calls=3, max_identical_total_tool_calls=6),
        budget_policy=TokenBudgetPolicy(input_limit=10_000, reserved_output_tokens=512),
        clock=FakeClock(),
        allow_grading=False,
        tool_sink=sink,
    )
    assert tool_record.status == "PASS"
    assert tool_record.tool_call_count == 2
    assert sink == ["alpha"]
    tool_codes = _state_codes(tool_record)
    assert {"S14", "S15", "S16", "S17", "S18", "S19", "S20", "S21"} <= tool_codes
    assert {"S0", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9", "S10", "S11", "S12", "S13"} <= tool_codes

    union = _state_codes(success_record) | tool_codes
    assert union == {f"S{index}" for index in range(28)}


@pytest.mark.parametrize(
    "label,backend_outputs,expected_reason,expected_exception",
    [
        ("malformed", ["not-json"], "syntax failure", None),
        ("forbidden", [json.dumps({"tool_calls": [{"tool_name": "reset", "arguments": {}}]}, ensure_ascii=False)], "semantic failure", None),
        ("unknown", [json.dumps({"tool_calls": [{"tool_name": "hallucinated", "arguments": {}}]}, ensure_ascii=False)], "semantic failure", None),
        ("missing-parameter", [json.dumps({"tool_calls": [{"tool_name": "pair", "arguments": {"left": "x"}}]}, ensure_ascii=False)], "semantic failure", None),
        ("backend-crash", [RuntimeError("simulated backend crash")], None, RuntimeError),
        ("reset-failure", [json.dumps({"terminal_response": "done"}, ensure_ascii=False)], None, ResetFailureError),
    ],
)
def test_p16_fault_injection_matrix_rows_fail_closed(
    tmp_path: Path,
    label: str,
    backend_outputs: list[object],
    expected_reason: str | None,
    expected_exception: type[Exception] | None,
) -> None:
    if expected_exception is not None:
        if expected_exception is RuntimeError:
            with pytest.raises(RuntimeError):
                _run(tmp_path=tmp_path, suffix=label, backend_outputs=backend_outputs)
        else:
            with pytest.raises(expected_exception):
                _run(tmp_path=tmp_path, suffix=label, backend_outputs=backend_outputs, reset_error=expected_exception("boom"))
        return

    record, _, _, _ = _run(tmp_path=tmp_path, suffix=label, backend_outputs=backend_outputs)
    assert record.status == "FAIL"
    assert record.termination_reason == expected_reason


def test_p16_token_overflow_and_model_loop_classification(tmp_path: Path) -> None:
    base_record, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="overflow-base",
        backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
    )
    assert base_record.status == "PASS"

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
    overflow_record, _, _, _ = _run(
        tmp_path=tmp_path,
        suffix="overflow",
        backend_outputs=[json.dumps({"tool_calls": [{"tool_name": "echo", "arguments": {"value": "same"}}]}, ensure_ascii=False)],
        budget_policy=TokenBudgetPolicy(input_limit=overflow_limit, reserved_output_tokens=512),
    )
    assert overflow_record.status == "FAIL"
    assert overflow_record.termination_reason == "model_created_loop_overflow"

    with pytest.raises(SchemaInvariantError):
        _run(
            tmp_path=tmp_path,
            suffix="initial-overflow",
            backend_outputs=[json.dumps({"terminal_response": "done"}, ensure_ascii=False)],
            budget_policy=TokenBudgetPolicy(input_limit=1, reserved_output_tokens=0),
        )


def test_p16_checkpoint_resume_and_git_sync_demonstration(tmp_path: Path) -> None:
    repo, remote, initial_sha = _init_git_repo(tmp_path)
    allowlist_path = tmp_path / "sync_allowlist.yaml"
    manifest_path = tmp_path / "sync_manifest.json"
    receipt_path = tmp_path / "sync_receipt.json"
    _write_sync_allowlist(allowlist_path)

    (repo / "phase5" / "implementation" / "reports" / "artifact.json").write_text(
        "{\"artifact\":\"v2\"}\n",
        encoding="utf-8",
    )
    _write_sync_manifest(repo, source_commit=initial_sha, remote_head=initial_sha, manifest_path=manifest_path)
    env = {"GITHUB_TOKEN": "token-123"}

    session, receipt = perform_sync_github(
        session=Phase5Session.initial().seal().close_after_finalization(),
        repo=repo,
        manifest_path=manifest_path,
        allowlist_path=allowlist_path,
        receipt_path=receipt_path,
        env=env,
    )
    assert session.state is SessionState.UNSEALED_SYNCED
    assert receipt.credential_purged is True
    assert env.get("GITHUB_TOKEN") is None

    reverified_session, reverify_result = perform_session_reverify(session=session, repo=repo, receipt_path=receipt_path, env={})
    assert reverified_session.state is SessionState.REVERIFIED_AFTER_SYNC
    assert reverify_result.checkpoint_head == receipt.local_commit_sha

    resealed = reverified_session.seal()
    assert resealed.state is SessionState.SEALED
    assert resealed.seal_epoch == 2

    campaign_session, report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id="P5RUN-P5-DV-1.0.0-A7C91E42-M1-20260708-ABCDEF12",
        utcdate="20260708",
        until_safety_horizon=True,
        max_batches=2,
    )
    resumed_session, resumed_report = run_campaign(
        model_slot=ModelSlot.M1,
        run_id=campaign_session.run_id,
        until_safety_horizon=True,
        session=campaign_session,
    )
    assert report.stop_reason in {"complete", "interrupted"}
    assert resumed_session.state in {SessionState.SEALED, SessionState.REVERIFIED_AFTER_SYNC}
    assert resumed_report.processed_batch_ids[:2] == report.processed_batch_ids[:2]


def test_p16_local_mcp_discovery_hides_reset_and_rejects_public_hosts() -> None:
    launcher = McpServerLauncher(host="127.0.0.1", port=8000, server_factory=build_server)
    verified = launcher.validate()

    assert verified.host == "127.0.0.1"
    assert verified.reset_hidden is True
    assert "reset" not in verified.tool_names
    assert "read_internal_notes" in verified.tool_names
    assert probe_reset_dispatch(verified.server).rejected is True
    assert discover_tool_names(verified.server)

    with pytest.raises(RuntimeMismatchError):
        McpServerLauncher(host="0.0.0.0", port=8000, server_factory=build_server).validate()


def test_p16_report_content_scans_do_not_trigger_on_qualification_summary() -> None:
    text = "P16 local qualification completed without forbidden analysis or secret material."
    assert scan_text_for_secrets(text) == []
    assert scan_text_for_forbidden_analysis(text) == []
