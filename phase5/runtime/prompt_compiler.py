"""Frozen prompt compilation helpers for Phase 5."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from ..evidence.io import atomic_write_text
from ..guards import repo_root
from .prompt_serialization import ConversationTurn, normalize_turns, render_history, render_turn_stream
from .token_budget import (
    TokenBudgetPolicy,
    TokenBudgetDecision,
    OverflowClassification,
    budget_decision_for_turn,
    build_exact_tokenizer,
    count_tokens,
    load_frozen_tokenizer_identity,
    summarize_text_token_count,
    summarize_turn_token_counts,
)


PROMPT_MANIFEST_PATH = Path("prompts/phase3_prompt_manifest.json")
PROMPT_HASH_MANIFEST_PATH = Path("prompts/prompt_hash_manifest.json")
EXPECTED_PROMPT_KEYS = (
    "system_prompt",
    "tool_call_contract",
    "user_task_template",
    "tool_result_template",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_canonical_json(mapping: Mapping[str, Any]) -> str:
    payload = json.dumps(mapping, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return _sha256_bytes(payload)


def _load_json(path: Path) -> Mapping[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError(f"{path.as_posix()} must contain a JSON object")
    return data


def _render_template(template: str, substitutions: Mapping[str, str]) -> str:
    rendered = template
    for placeholder, value in substitutions.items():
        token = f"{{{{{placeholder}}}}}"
        if token not in rendered:
            raise SchemaInvariantError(f"missing required placeholder {placeholder!r}")
        rendered = rendered.replace(token, value)
    if "{{" in rendered or "}}" in rendered:
        raise SchemaInvariantError("template contains unresolved placeholders")
    return rendered


def _normalize_line_endings(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


@dataclass(frozen=True, slots=True)
class FrozenPromptAsset:
    label: str
    relative_path: Path
    text: str
    sha256: str
    byte_length: int

    def to_mapping(self) -> dict[str, Any]:
        return {
            "byte_length": self.byte_length,
            "label": self.label,
            "relative_path": self.relative_path.as_posix(),
            "sha256": self.sha256,
        }


@dataclass(frozen=True, slots=True)
class FrozenPromptBundle:
    manifest_path: Path
    hash_manifest_path: Path
    manifest_sha256: str
    system_prompt: FrozenPromptAsset
    tool_call_contract: FrozenPromptAsset
    user_task_template: FrozenPromptAsset
    tool_result_template: FrozenPromptAsset

    @property
    def assets(self) -> tuple[FrozenPromptAsset, ...]:
        return (
            self.system_prompt,
            self.tool_call_contract,
            self.user_task_template,
            self.tool_result_template,
        )

    def to_mapping(self) -> dict[str, Any]:
        return {
            "assets": {asset.label: asset.to_mapping() for asset in self.assets},
            "hash_manifest_path": PROMPT_HASH_MANIFEST_PATH.as_posix(),
            "manifest_path": PROMPT_MANIFEST_PATH.as_posix(),
            "manifest_sha256": self.manifest_sha256,
        }


@dataclass(frozen=True, slots=True)
class CompiledPromptArtifact:
    prompt_text: str
    prompt_bytes: bytes
    bundle: FrozenPromptBundle
    task_description: str | None
    retrieved_content: str | None
    history: tuple[ConversationTurn, ...]
    tool_results: tuple[ConversationTurn, ...]
    prompt_token_count: int
    prompt_budget_decision: TokenBudgetDecision
    component_token_counts: tuple[Any, ...]
    turn_token_counts: tuple[Any, ...]
    tokenizer_identity: str

    @property
    def prompt_sha256(self) -> str:
        return _sha256_bytes(self.prompt_bytes)

    def metadata_mapping(self) -> dict[str, Any]:
        return {
            "bundle": self.bundle.to_mapping(),
            "component_token_counts": [item.to_mapping() for item in self.component_token_counts],
            "history_turn_count": len(self.history),
            "prompt_byte_length": len(self.prompt_bytes),
            "prompt_sha256": self.prompt_sha256,
            "prompt_token_count": self.prompt_token_count,
            "prompt_budget_decision": self.prompt_budget_decision.to_mapping(),
            "retrieved_content_is_null": self.retrieved_content is None,
            "task_description_is_null": self.task_description is None,
            "task_description": self.task_description,
            "tokenizer_identity": self.tokenizer_identity,
            "tool_result_count": len(self.tool_results),
            "turn_token_counts": [item.to_mapping() for item in self.turn_token_counts],
        }

    def write(self, destination_root: Path) -> tuple[Path, Path, Path]:
        compiled_prompt_path = destination_root / "compiled_prompt.txt"
        compiled_prompt_metadata_path = destination_root / "compiled_prompt_metadata.json"
        token_counts_path = destination_root / "token_counts_per_turn.json"
        atomic_write_text(compiled_prompt_path, self.prompt_text)
        atomic_write_text(
            compiled_prompt_metadata_path,
            json.dumps(self.metadata_mapping(), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        )
        atomic_write_text(
            token_counts_path,
            json.dumps([item.to_mapping() for item in self.turn_token_counts], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n",
        )
        return compiled_prompt_path, compiled_prompt_metadata_path, token_counts_path


def load_frozen_prompt_bundle(root: Path | None = None) -> FrozenPromptBundle:
    repository_root = (root or repo_root()).resolve()
    manifest_path = repository_root / PROMPT_MANIFEST_PATH
    hash_manifest_path = repository_root / PROMPT_HASH_MANIFEST_PATH
    if not manifest_path.is_file():
        raise MissingFrozenSettingError(f"frozen prompt manifest is missing: {manifest_path.as_posix()}")
    if not hash_manifest_path.is_file():
        raise MissingFrozenSettingError(f"prompt hash manifest is missing: {hash_manifest_path.as_posix()}")

    manifest = _load_json(manifest_path)
    hash_manifest = _load_json(hash_manifest_path)
    if set(manifest.keys()) != set(EXPECTED_PROMPT_KEYS):
        raise SchemaInvariantError(
            "frozen prompt manifest must expose exactly the expected prompt asset keys"
        )
    expected_hash_keys = {Path(manifest[label]).name for label in EXPECTED_PROMPT_KEYS}
    if set(hash_manifest.keys()) != expected_hash_keys:
        raise SchemaInvariantError("prompt hash manifest does not match the expected frozen prompt assets")

    assets: dict[str, FrozenPromptAsset] = {}
    for label in EXPECTED_PROMPT_KEYS:
        relative_path = Path(manifest[label])
        if relative_path.is_absolute():
            raise SchemaInvariantError(f"prompt asset path must be relative: {relative_path.as_posix()}")
        asset_path = repository_root / relative_path
        if not asset_path.is_file():
            raise MissingFrozenSettingError(f"frozen prompt asset is missing: {asset_path.as_posix()}")
        raw_bytes = asset_path.read_bytes()
        asset_text = raw_bytes.decode("utf-8")
        asset_sha256 = _sha256_bytes(raw_bytes)
        expected_sha256 = hash_manifest.get(relative_path.name)
        if expected_sha256 is None:
            raise MissingFrozenSettingError(f"prompt hash manifest is missing {relative_path.name!r}")
        if asset_sha256.lower() != str(expected_sha256).lower():
            raise FrozenArtifactHashError(
                f"prompt asset hash mismatch for {asset_path.as_posix()}: expected {expected_sha256}, got {asset_sha256}"
            )
        assets[label] = FrozenPromptAsset(
            label=label,
            relative_path=relative_path,
            text=asset_text,
            sha256=asset_sha256,
            byte_length=len(raw_bytes),
        )

    return FrozenPromptBundle(
        manifest_path=manifest_path,
        hash_manifest_path=hash_manifest_path,
        manifest_sha256=_sha256_canonical_json(manifest),
        system_prompt=assets["system_prompt"],
        tool_call_contract=assets["tool_call_contract"],
        user_task_template=assets["user_task_template"],
        tool_result_template=assets["tool_result_template"],
    )


def _render_compiled_sections(
    bundle: FrozenPromptBundle,
    *,
    task_description: str | None,
    retrieved_content: str | None,
    history: Sequence[ConversationTurn | Mapping[str, Any]] | None,
    tool_results: Sequence[ConversationTurn | Mapping[str, Any]] | None,
) -> tuple[str, tuple[ConversationTurn, ...], tuple[ConversationTurn, ...], str]:
    normalized_history = normalize_turns(history)
    normalized_tool_results = normalize_turns(tool_results)
    rendered_task = _render_template(
        bundle.user_task_template.text,
        {"task_description": "" if task_description is None else task_description},
    )
    rendered_history = render_history(normalized_history, tool_result_template=bundle.tool_result_template.text)
    rendered_tool_results = "\n\n".join(
        render_turn_stream(normalized_tool_results, tool_result_template=bundle.tool_result_template.text)
    )
    rendered_retrieved = "" if retrieved_content is None else retrieved_content
    prompt_text = "\n".join(
        [
            "<|system|>",
            bundle.system_prompt.text,
            "<|tools|>",
            bundle.tool_call_contract.text,
            "<|tool_result_template|>",
            bundle.tool_result_template.text,
            "<|retrieved_content|>",
            rendered_retrieved,
            "<|user|>",
            rendered_task,
            "<|history|>",
            rendered_history,
            "<|tool_results|>",
            rendered_tool_results,
            "<|assistant|>",
        ]
    )
    prompt_text = _normalize_line_endings(prompt_text)
    if not prompt_text.endswith("\n"):
        prompt_text += "\n"
    return prompt_text, normalized_history, normalized_tool_results, rendered_task


def compile_frozen_prompt(
    *,
    task_description: str | None,
    retrieved_content: str | None = None,
    history: Sequence[ConversationTurn | Mapping[str, Any]] | None = (),
    tool_results: Sequence[ConversationTurn | Mapping[str, Any]] | None = (),
    root: Path | None = None,
    tokenizer: Any | None = None,
    budget_policy: TokenBudgetPolicy | None = None,
) -> CompiledPromptArtifact:
    bundle = load_frozen_prompt_bundle(root)
    prompt_text, normalized_history, normalized_tool_results, rendered_task = _render_compiled_sections(
        bundle,
        task_description=task_description,
        retrieved_content=retrieved_content,
        history=history,
        tool_results=tool_results,
    )
    prompt_bytes = prompt_text.encode("utf-8")
    current_tokenizer = tokenizer or build_exact_tokenizer(root=root)
    policy = budget_policy or TokenBudgetPolicy()

    component_token_counts = (
        summarize_text_token_count(current_tokenizer, label="system_prompt", text=bundle.system_prompt.text, source="component"),
        summarize_text_token_count(
            current_tokenizer,
            label="tool_call_contract",
            text=bundle.tool_call_contract.text,
            source="component",
        ),
        summarize_text_token_count(
            current_tokenizer,
            label="tool_result_template",
            text=bundle.tool_result_template.text,
            source="component",
        ),
        summarize_text_token_count(
            current_tokenizer,
            label="retrieved_content",
            text="" if retrieved_content is None else retrieved_content,
            source="component",
        ),
        summarize_text_token_count(
            current_tokenizer,
            label="user_task",
            text=rendered_task,
            source="component",
        ),
        summarize_text_token_count(
            current_tokenizer,
            label="compiled_prompt",
            text=prompt_text,
            source="component",
        ),
    )

    history_turn_token_counts = summarize_turn_token_counts(
        current_tokenizer,
        normalized_history,
        tool_result_template=bundle.tool_result_template.text,
        source="conversation_history",
    )
    tool_result_token_counts = summarize_turn_token_counts(
        current_tokenizer,
        normalized_tool_results,
        tool_result_template=bundle.tool_result_template.text,
        source="tool_results",
    )
    turn_token_counts = history_turn_token_counts + tool_result_token_counts
    prompt_token_count = count_tokens(current_tokenizer, prompt_text)
    prompt_budget_decision = budget_decision_for_turn(
        input_tokens=prompt_token_count,
        policy=policy,
        classification=(
            None
            if prompt_token_count <= policy.input_limit
            else OverflowClassification.INITIAL_FROZEN_PROMPT_OVERFLOW
        ),
    )

    return CompiledPromptArtifact(
        prompt_text=prompt_text,
        prompt_bytes=prompt_bytes,
        bundle=bundle,
        task_description=task_description,
        retrieved_content=retrieved_content,
        history=normalized_history,
        tool_results=normalized_tool_results,
        prompt_token_count=prompt_token_count,
        prompt_budget_decision=prompt_budget_decision,
        component_token_counts=component_token_counts,
        turn_token_counts=turn_token_counts,
        tokenizer_identity=load_frozen_tokenizer_identity(root),
    )


def write_compiled_prompt_artifacts(
    destination_root: Path,
    *,
    task_description: str | None,
    retrieved_content: str | None = None,
    history: Sequence[ConversationTurn | Mapping[str, Any]] | None = (),
    tool_results: Sequence[ConversationTurn | Mapping[str, Any]] | None = (),
    root: Path | None = None,
    tokenizer: Any | None = None,
    budget_policy: TokenBudgetPolicy | None = None,
) -> CompiledPromptArtifact:
    artifact = compile_frozen_prompt(
        task_description=task_description,
        retrieved_content=retrieved_content,
        history=history,
        tool_results=tool_results,
        root=root,
        tokenizer=tokenizer,
        budget_policy=budget_policy,
    )
    artifact.write(destination_root)
    return artifact
