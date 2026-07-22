from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from phase5.domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from phase5.runtime import (
    ConversationTurn,
    OverflowClassification,
    TokenBudgetPolicy,
    TokenBudgetExceededError,
    TokenizerIdentityMismatchError,
    build_exact_tokenizer,
    classify_overflow,
    compile_frozen_prompt,
    enforce_token_budget,
    load_frozen_prompt_bundle,
    load_frozen_tokenizer_identity,
    render_history,
    serialize_turn,
)
from phase5.runtime.prompt_compiler import POST_TOOL_RESPONSE_CONTRACT
from phase5.runtime.token_budget import InfrastructureOversizeError


FIXTURE_ROOT = Path("phase5/tests/fixtures/p08")


class FakeTokenizer:
    def __init__(self, name_or_path: str) -> None:
        self.name_or_path = name_or_path
        self.init_kwargs = {"name_or_path": name_or_path}

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        return list(text.encode("utf-8"))


def _fake_tokenizer(name_or_path: str = "microsoft/Phi-3.5-mini-instruct") -> FakeTokenizer:
    return FakeTokenizer(name_or_path)


def test_frozen_prompt_bundle_matches_hash_manifest() -> None:
    bundle = load_frozen_prompt_bundle()
    bundle_metadata = bundle.to_mapping()

    assert bundle.system_prompt.relative_path.as_posix() == "prompts/phase3_system_prompt.txt"
    assert bundle.tool_call_contract.relative_path.as_posix() == "prompts/phase3_tool_call_contract.txt"
    assert bundle.user_task_template.relative_path.as_posix() == "prompts/phase3_user_task_template.txt"
    assert bundle.tool_result_template.relative_path.as_posix() == "prompts/phase3_tool_result_template.txt"
    assert bundle_metadata["manifest_path"] == "prompts/phase3_prompt_manifest.json"
    assert bundle_metadata["hash_manifest_path"] == "prompts/prompt_hash_manifest.json"
    assert not Path(bundle_metadata["manifest_path"]).is_absolute()
    assert not Path(bundle_metadata["hash_manifest_path"]).is_absolute()
    assert "helpful and capable" in bundle.system_prompt.text


def test_missing_prompt_asset_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    prompts = root / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    (prompts / "phase3_prompt_manifest.json").write_text(
        json.dumps(
            {
                "system_prompt": "prompts/phase3_system_prompt.txt",
                "tool_call_contract": "prompts/phase3_tool_call_contract.txt",
                "user_task_template": "prompts/phase3_user_task_template.txt",
                "tool_result_template": "prompts/phase3_tool_result_template.txt",
            }
        ),
        encoding="utf-8",
    )
    (prompts / "prompt_hash_manifest.json").write_text(
        json.dumps(
            {
                "phase3_system_prompt.txt": "0" * 64,
                "phase3_tool_call_contract.txt": "0" * 64,
                "phase3_user_task_template.txt": "0" * 64,
                "phase3_tool_result_template.txt": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase5.runtime.prompt_compiler.repo_root", lambda: root)

    with pytest.raises(MissingFrozenSettingError):
        load_frozen_prompt_bundle()


def test_hash_invalid_prompt_reference_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "repo"
    prompts = root / "prompts"
    prompts.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir()
    for name, content in {
        "phase3_system_prompt.txt": "system",
        "phase3_tool_call_contract.txt": "contract",
        "phase3_user_task_template.txt": "Task: {{task_description}}\nPlease execute the necessary tools to complete this task.",
        "phase3_tool_result_template.txt": "Tool Result [{{tool_name}}]:\n{{tool_output}}",
    }.items():
        (prompts / name).write_text(content, encoding="utf-8")
    (prompts / "phase3_prompt_manifest.json").write_text(
        json.dumps(
            {
                "system_prompt": "prompts/phase3_system_prompt.txt",
                "tool_call_contract": "prompts/phase3_tool_call_contract.txt",
                "user_task_template": "prompts/phase3_user_task_template.txt",
                "tool_result_template": "prompts/phase3_tool_result_template.txt",
            }
        ),
        encoding="utf-8",
    )
    (prompts / "prompt_hash_manifest.json").write_text(
        json.dumps(
            {
                "phase3_system_prompt.txt": "1" * 64,
                "phase3_tool_call_contract.txt": "0" * 64,
                "phase3_user_task_template.txt": "0" * 64,
                "phase3_tool_result_template.txt": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr("phase5.runtime.prompt_compiler.repo_root", lambda: root)

    with pytest.raises(FrozenArtifactHashError):
        load_frozen_prompt_bundle()


def test_manifest_metadata_hash_is_line_ending_stable(tmp_path: Path) -> None:
    def write_root(root: Path, manifest_newline: str) -> None:
        prompts = root / "prompts"
        prompts.mkdir(parents=True, exist_ok=True)
        (root / ".git").mkdir()
        assets = {
            "phase3_system_prompt.txt": "system\r\n",
            "phase3_tool_call_contract.txt": "contract\r\n",
            "phase3_user_task_template.txt": "Task: {{task_description}}\r\nPlease execute the necessary tools to complete this task.\r\n",
            "phase3_tool_result_template.txt": "Tool Result [{{tool_name}}]:\r\n{{tool_output}}\r\n",
        }
        for name, content in assets.items():
            (prompts / name).write_text(content, encoding="utf-8", newline="")

        manifest = {
            "system_prompt": "prompts/phase3_system_prompt.txt",
            "tool_call_contract": "prompts/phase3_tool_call_contract.txt",
            "user_task_template": "prompts/phase3_user_task_template.txt",
            "tool_result_template": "prompts/phase3_tool_result_template.txt",
        }
        manifest_text = json.dumps(manifest, indent=2)
        (prompts / "phase3_prompt_manifest.json").write_text(
            manifest_text.replace("\n", manifest_newline),
            encoding="utf-8",
            newline="",
        )
        (prompts / "prompt_hash_manifest.json").write_text(
            json.dumps(
                {
                    name: hashlib.sha256(content.encode("utf-8")).hexdigest()
                    for name, content in assets.items()
                }
            ),
            encoding="utf-8",
        )

    lf_root = tmp_path / "lf"
    crlf_root = tmp_path / "crlf"
    write_root(lf_root, "\n")
    write_root(crlf_root, "\r\n")

    lf_bundle = load_frozen_prompt_bundle(lf_root)
    crlf_bundle = load_frozen_prompt_bundle(crlf_root)

    assert lf_bundle.manifest_path.read_bytes() != crlf_bundle.manifest_path.read_bytes()
    assert lf_bundle.to_mapping()["manifest_sha256"] == crlf_bundle.to_mapping()["manifest_sha256"]


def test_null_payload_compile_matches_golden_fixture() -> None:
    artifact = compile_frozen_prompt(
        task_description="Check token budget handling",
        retrieved_content=None,
        history=(),
        tool_results=(),
        tokenizer=_fake_tokenizer(),
    )

    expected_prompt = (FIXTURE_ROOT / "compiled_prompt_null_payload.txt").read_bytes()
    expected_metadata = json.loads((FIXTURE_ROOT / "compiled_prompt_null_payload_metadata.json").read_text(encoding="utf-8"))
    expected_metadata["tokenizer_identity"] = load_frozen_tokenizer_identity()
    expected_turn_counts = json.loads((FIXTURE_ROOT / "token_counts_per_turn_null_payload.json").read_text(encoding="utf-8"))

    assert artifact.prompt_bytes == expected_prompt
    assert artifact.prompt_text == expected_prompt.decode("utf-8")
    assert artifact.metadata_mapping() == expected_metadata
    assert [item.to_mapping() for item in artifact.turn_token_counts] == expected_turn_counts
    assert artifact.prompt_sha256 == expected_metadata["prompt_sha256"]


def test_compile_preserves_whitespace_and_counts_tool_messages() -> None:
    history = (
        ConversationTurn(turn_index=0, role="user", content="keep  trailing  spaces  ", turn_kind="conversation"),
        ConversationTurn(
            turn_index=1,
            role="tool",
            content='{"ok":true}',
            turn_kind="tool_result",
            tool_name="read_file",
        ),
    )
    artifact = compile_frozen_prompt(
        task_description="Inspect the tool result",
        retrieved_content="payload line one\npayload line two",
        history=history,
        tool_results=(
            ConversationTurn(
                turn_index=2,
                role="tool",
                content="tool output block",
                turn_kind="tool_result",
                tool_name="log_event",
            ),
        ),
        tokenizer=_fake_tokenizer(),
    )

    assert "keep  trailing  spaces  " in artifact.prompt_text
    assert "Tool Result [read_file]:" in artifact.prompt_text
    assert "Tool Result [log_event]:" in artifact.prompt_text
    assert any(count.role == "tool" and count.source == "conversation_history" for count in artifact.turn_token_counts)
    assert any(count.role == "tool" and count.source == "tool_results" for count in artifact.turn_token_counts)
    assert serialize_turn(history[1]) == json.dumps(history[1].to_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    assert render_history(history, tool_result_template="Tool Result [{{tool_name}}]:\n{{tool_output}}") != ""


def test_post_tool_prompt_adds_terminal_response_contract_only_after_tool_results() -> None:
    initial = compile_frozen_prompt(
        task_description="Inspect the tool result",
        retrieved_content=None,
        history=(),
        tool_results=(),
        tokenizer=_fake_tokenizer(),
    )
    after_tool = compile_frozen_prompt(
        task_description="Inspect the tool result",
        retrieved_content=None,
        history=(),
        tool_results=(
            ConversationTurn(
                turn_index=1,
                role="tool",
                content="tool output block",
                turn_kind="tool_result",
                tool_name="read_file",
            ),
        ),
        tokenizer=_fake_tokenizer(),
    )

    assert "<|post_tool_response_contract|>" not in initial.prompt_text
    assert "<|post_tool_response_contract|>" in after_tool.prompt_text
    assert POST_TOOL_RESPONSE_CONTRACT in after_tool.prompt_text
    assert '{"terminal_response":"..."}' in after_tool.prompt_text


def test_compile_preserves_nested_json_in_task_substitution() -> None:
    nested_json = '{"tool":"read_internal_notes","arguments":{"note_id":"note-001"}}'
    artifact = compile_frozen_prompt(
        task_description=f"Call the tool using exactly {nested_json}.",
        retrieved_content=None,
        history=(),
        tool_results=(),
        tokenizer=_fake_tokenizer(),
    )

    assert nested_json in artifact.prompt_text


def test_compile_normalizes_prompt_bytes_to_lf() -> None:
    artifact = compile_frozen_prompt(
        task_description="line one\r\nline two\rline three",
        retrieved_content="retrieved\r\ncontent",
        history=(
            ConversationTurn(
                turn_index=0,
                role="user",
                content="history\r\ncontent",
                turn_kind="conversation",
            ),
        ),
        tool_results=(
            ConversationTurn(
                turn_index=1,
                role="tool",
                content="tool\rcontent",
                turn_kind="tool_result",
                tool_name="read_file",
            ),
        ),
        tokenizer=_fake_tokenizer(),
    )

    assert "\r" not in artifact.prompt_text
    assert b"\r" not in artifact.prompt_bytes
    assert "line one\nline two\nline three" in artifact.prompt_text
    assert "retrieved\ncontent" in artifact.prompt_text
    assert "history\ncontent" in artifact.prompt_text
    assert "tool\ncontent" in artifact.prompt_text


def test_null_payload_compile_path_writes_token_evidence(tmp_path: Path) -> None:
    artifact = compile_frozen_prompt(
        task_description=None,
        retrieved_content=None,
        history=(),
        tool_results=(),
        tokenizer=_fake_tokenizer(),
    )
    compiled_prompt_path, metadata_path, token_counts_path = artifact.write(tmp_path)

    assert compiled_prompt_path.is_file()
    assert metadata_path.is_file()
    assert token_counts_path.is_file()
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    token_counts = json.loads(token_counts_path.read_text(encoding="utf-8"))
    assert metadata["task_description_is_null"] is True
    assert metadata["retrieved_content_is_null"] is True
    assert token_counts == []


def test_tokenizer_identity_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("phase5.runtime.token_budget.load_frozen_tokenizer_identity", lambda root=None: "other/tokenizer")
    with pytest.raises(TokenizerIdentityMismatchError):
        build_exact_tokenizer(tokenizer_loader=lambda *args, **kwargs: _fake_tokenizer())


def test_loaded_tokenizer_identity_mismatch_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("phase5.runtime.token_budget.load_frozen_tokenizer_identity", lambda root=None: "Qwen/Qwen2.5-7B-Instruct")
    with pytest.raises(TokenizerIdentityMismatchError):
        build_exact_tokenizer(tokenizer_loader=lambda *args, **kwargs: _fake_tokenizer("wrong/tokenizer"))


def test_initial_overflow_expected_tool_result_overflow_and_model_loop_classification() -> None:
    policy = TokenBudgetPolicy(input_limit=5, reserved_output_tokens=512)

    assert classify_overflow(initial_prompt_overflow=True) is OverflowClassification.INITIAL_FROZEN_PROMPT_OVERFLOW
    assert classify_overflow(expected_valid_tool_result_overflow=True) is OverflowClassification.EXPECTED_VALID_TOOL_RESULT_OVERFLOW
    assert classify_overflow(model_created_loop_overflow=True) is OverflowClassification.MODEL_CREATED_LOOP_OVERFLOW
    assert classify_overflow(infrastructure_generated_oversized_result=True) is OverflowClassification.INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT

    with pytest.raises(SchemaInvariantError):
        classify_overflow(initial_prompt_overflow=True, model_created_loop_overflow=True)

    with pytest.raises(TokenBudgetExceededError):
        enforce_token_budget(
            input_tokens=6,
            policy=policy,
            classification=OverflowClassification.INITIAL_FROZEN_PROMPT_OVERFLOW,
        )

    with pytest.raises(TokenBudgetExceededError):
        enforce_token_budget(
            input_tokens=6,
            policy=policy,
            classification=OverflowClassification.EXPECTED_VALID_TOOL_RESULT_OVERFLOW,
        )

    with pytest.raises(TokenBudgetExceededError):
        enforce_token_budget(
            input_tokens=6,
            policy=policy,
            classification=OverflowClassification.MODEL_CREATED_LOOP_OVERFLOW,
        )

    with pytest.raises(InfrastructureOversizeError):
        enforce_token_budget(
            input_tokens=6,
            policy=policy,
            classification=OverflowClassification.INFRASTRUCTURE_GENERATED_OVERSIZED_RESULT,
        )


def test_budget_enforcement_allows_in_range_inputs() -> None:
    decision = enforce_token_budget(input_tokens=4, policy=TokenBudgetPolicy(input_limit=5, reserved_output_tokens=512))
    assert decision.allowed is True
    assert decision.classification is None
    assert decision.total_budget == 517


def test_history_and_tool_results_are_serialized_verbatim() -> None:
    turns = (
        ConversationTurn(turn_index=0, role="user", content="alpha  beta", turn_kind="conversation"),
        ConversationTurn(turn_index=1, role="tool", content="line1\nline2", turn_kind="tool_result", tool_name="read_file"),
    )
    rendered = render_history(turns, tool_result_template="Tool Result [{{tool_name}}]:\n{{tool_output}}")
    assert "alpha  beta" in rendered
    assert "line1\nline2" in rendered
    assert "Tool Result [read_file]:" in rendered


def test_frozen_tokenizer_identity_is_loaded_from_registry() -> None:
    assert load_frozen_tokenizer_identity() == "mistralai/Mistral-7B-Instruct-v0.3"


def test_backend_identity_failure_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "phase5.runtime.token_budget.load_frozen_model_backend_identity",
        lambda root=None: (_ for _ in ()).throw(MissingFrozenSettingError("missing frozen model")),
    )
    with pytest.raises(MissingFrozenSettingError):
        load_frozen_tokenizer_identity()
