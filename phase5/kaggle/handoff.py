"""Thin Kaggle handoff plans and public-CLI wrappers for Phase 5.

The notebook for P15 consumes the plan builders in this module. The execution
wrappers remain intentionally narrow and only dispatch through the public
``python -m phase5`` CLI surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import sys
from typing import Mapping, Sequence

from ..domain.errors import SchemaInvariantError


PUBLIC_CLI_PREFIX = (sys.executable, "-m", "phase5")
NOTEBOOK_STAGE_SEQUENCE = (
    "environment_identity",
    "clone_evidence_branch",
    "verify_source",
    "install_pinned_dependencies",
    "strict_gate0",
    "runtime_model_verification",
    "non_official_startup_canary",
    "build_resume_campaign_plan",
    "operator_confirmation",
    "session_open",
    "seal_epoch",
    "real_run_campaign",
    "batch_finalization",
    "seal_closure",
    "stop_runtime",
    "github_checkpoint_sync",
    "remote_sha_verification",
    "credential_purge",
    "source_freeze_reverification",
    "new_seal_or_termination",
    "campaign_resume_report",
)
EDITABLE_PARAMETER_KEYS = (
    "repository_branch",
    "source_tag_or_commit",
    "model_branch",
    "evidence_branch",
    "approved_operational_limits",
)
APPROVED_OPERATIONAL_LIMIT_KEYS = (
    "safe_session_hours",
    "checkpoint_barrier_interval_trials",
)
READ_SECRET_NAME = "GITHUB_READ_TOKEN_PHASE5"
WRITE_SECRET_NAME = "GITHUB_WRITE_TOKEN_PHASE5"
PUBLIC_TOKEN_ENV_NAME = "GITHUB_TOKEN"
DEFAULT_NOTEBOOK_REPO_ROOT = Path("/kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation")
DEFAULT_GATE0_REPORT_DIR = Path("phase5/validation")
DEFAULT_TIMING_REPORT = Path("phase4_5/validation/phase45_kaggle_quota_feasibility_report.md")
DEFAULT_RUN_PLAN = Path("phase5/validation/kaggle_run_plan_v2.json")
DEFAULT_BATCH_MANIFEST = Path("phase5/manifests/batch_partition_manifest_v2.json")
DEFAULT_CLI_OUTPUT = Path("phase5/validation/p15_handoff_report.json")
DEFAULT_SYNC_RECEIPT = Path("<SYNC_RECEIPT_PATH>")
DEFAULT_CANARY_BATCH_ID = "<CANARY_BATCH_ID>"
DEFAULT_RUN_ID = "<RUN_ID>"
DEFAULT_MODEL_SLOT = "<MODEL_SLOT>"
DEFAULT_REPO_URL = "<REPOSITORY_URL>"
DEFAULT_SOURCE_TAG_OR_COMMIT = "<SOURCE_TAG_OR_COMMIT>"
DEFAULT_EVIDENCE_BRANCH = "<EVIDENCE_BRANCH>"


@dataclass(frozen=True, slots=True)
class KaggleHandoffParameters:
    repository_branch: str
    source_tag_or_commit: str
    model_branch: str
    evidence_branch: str
    approved_operational_limits: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "approved_operational_limits": dict(self.approved_operational_limits),
            "evidence_branch": self.evidence_branch,
            "model_branch": self.model_branch,
            "repository_branch": self.repository_branch,
            "source_tag_or_commit": self.source_tag_or_commit,
        }


@dataclass(frozen=True, slots=True)
class HandoffCommand:
    stage: str
    argv: tuple[str, ...]
    description: str
    placeholder: bool = False

    def to_dict(self) -> dict[str, object]:
        return {
            "argv": list(self.argv),
            "description": self.description,
            "placeholder": self.placeholder,
            "stage": self.stage,
        }

    def to_markdown(self) -> str:
        command = " ".join(self.argv)
        suffix = " (placeholder)" if self.placeholder else ""
        return f"- `{self.stage}`: `{command}`{suffix} - {self.description}"


@dataclass(frozen=True, slots=True)
class HandoffPlan:
    title: str
    stage: str
    notes: tuple[str, ...]
    commands: tuple[HandoffCommand, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "commands": [command.to_dict() for command in self.commands],
            "notes": list(self.notes),
            "stage": self.stage,
            "title": self.title,
        }

    def to_markdown(self) -> str:
        lines = [f"### {self.title}", ""]
        lines.extend(f"- {note}" for note in self.notes or ("none",))
        if self.commands:
            lines.extend(["", "Commands:"])
            lines.extend(command.to_markdown() for command in self.commands)
        return "\n".join(lines) + "\n"


def _require_allowed_parameter_keys(parameters: KaggleHandoffParameters) -> None:
    keys = set(parameters.approved_operational_limits.keys())
    expected = set(APPROVED_OPERATIONAL_LIMIT_KEYS)
    if keys != expected:
        raise SchemaInvariantError(
            "approved_operational_limits must contain only "
            f"{sorted(expected)!r}, got {sorted(keys)!r}"
        )


def validate_handoff_parameters(parameters: KaggleHandoffParameters) -> KaggleHandoffParameters:
    _require_allowed_parameter_keys(parameters)
    if not parameters.repository_branch:
        raise SchemaInvariantError("repository_branch must be provided")
    if not parameters.source_tag_or_commit:
        raise SchemaInvariantError("source_tag_or_commit must be provided")
    if not parameters.model_branch:
        raise SchemaInvariantError("model_branch must be provided")
    if not parameters.evidence_branch:
        raise SchemaInvariantError("evidence_branch must be provided")
    return parameters


def _cli_argv(command: str, *args: str) -> tuple[str, ...]:
    return (*PUBLIC_CLI_PREFIX, command, *args)


def _command(stage: str, command: str, description: str, *args: str, placeholder: bool = False) -> HandoffCommand:
    return HandoffCommand(stage=stage, argv=_cli_argv(command, *args), description=description, placeholder=placeholder)


def build_bootstrap_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Preparation / Gate 0",
        stage="preparation_gate0",
        notes=(
            "Run Gate 0 first and stop on any refusal.",
            "Then regenerate the frozen Kaggle run plan from the tested public CLI.",
        ),
        commands=(
            _command(
                "preparation_gate0",
                "gate0",
                "Strict Phase 5 entry gate",
                "--strict",
                "--root",
                str(DEFAULT_NOTEBOOK_REPO_ROOT),
                "--report-dir",
                DEFAULT_GATE0_REPORT_DIR.as_posix(),
            ),
            _command(
                "preparation_gate0",
                "plan-kaggle-runs",
                "Regenerate the frozen Kaggle run plan",
                "--timing-report",
                DEFAULT_TIMING_REPORT.as_posix(),
                "--safe-session-hours",
                str(parameters.approved_operational_limits["safe_session_hours"]),
                "--output",
                DEFAULT_RUN_PLAN.as_posix(),
            ),
        ),
    )


def build_campaign_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Campaign Plan",
        stage="campaign_plan",
        notes=(
            "Exactly one model campaign is the target per Kaggle session.",
            "The actual campaign count comes from the frozen P05 run planning output.",
            "This notebook does not duplicate queue, parser, or scientific logic.",
        ),
        commands=(
            _command(
                "campaign_plan",
                "plan-kaggle-runs",
                "Public CLI planning command backed by frozen evidence",
                "--timing-report",
                DEFAULT_TIMING_REPORT.as_posix(),
                "--safe-session-hours",
                str(parameters.approved_operational_limits["safe_session_hours"]),
                "--output",
                DEFAULT_RUN_PLAN.as_posix(),
            ),
        ),
    )


def build_canary_placeholder(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Canary Command Placeholder",
        stage="canary_placeholder",
        notes=(
            "This is a placeholder only and is not executed by the handoff task.",
            "It exists so the notebook keeps the planned stage order without running Kaggle work.",
        ),
        commands=(
            _command(
                "canary_placeholder",
                "validate-batch",
                "Non-official canary placeholder",
                "--batch-id",
                DEFAULT_CANARY_BATCH_ID,
                "--strict",
                placeholder=True,
            ),
        ),
    )


def build_session_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Open and Seal",
        stage="open_seal",
        notes=(
            "Open a single Kaggle session for one model campaign.",
            "The session remains thin: it only prepares the public CLI commands.",
        ),
        commands=(
            _command(
                "open_seal",
                "session-seal",
                "Open the first seal epoch",
                "--run-id",
                DEFAULT_RUN_ID,
                "--seal-epoch",
                "1",
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
        ),
    )


def build_unified_campaign_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Unified Campaign",
        stage="unified_campaign",
        notes=(
            "The unified runner is the only place where the long campaign is controlled.",
            "Do not add output repair, nested retries, or scientific branching here.",
            "The model slot itself comes from frozen configuration, not the editable branch fields.",
        ),
        commands=(
            _command(
                "unified_campaign",
                "run-campaign",
                "Unified campaign controller",
                "--model-slot",
                DEFAULT_MODEL_SLOT,
                "--run-id",
                DEFAULT_RUN_ID,
                "--utcdate",
                "<YYYYMMDD>",
                "--until-safety-horizon",
                "--batch-manifest",
                DEFAULT_BATCH_MANIFEST.as_posix(),
                "--run-plan",
                DEFAULT_RUN_PLAN.as_posix(),
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
        ),
    )


def build_sync_barrier_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Optional Sync Barrier",
        stage="optional_sync_barriers",
        notes=(
            "If the predeclared threshold is reached, stop the active attempt and sync.",
            "After sync, the notebook must not continue until re-verification and reseal succeed.",
        ),
        commands=(
            _command(
                "optional_sync_barriers",
                "session-close-seal",
                "Close the active seal before sync",
                "--run-id",
                DEFAULT_RUN_ID,
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
            _command(
                "optional_sync_barriers",
                "sync-github",
                "Synchronize finalized allowlisted evidence",
                "--repo",
                str(DEFAULT_NOTEBOOK_REPO_ROOT),
                "--manifest",
                "<SYNC_MANIFEST_PATH>",
                "--allowlist",
                "phase5/configs/sync_allowlist.yaml",
                "--receipt",
                DEFAULT_SYNC_RECEIPT.as_posix(),
            ),
            _command(
                "optional_sync_barriers",
                "session-reverify",
                "Reverify frozen hashes after sync",
                "--repo",
                str(DEFAULT_NOTEBOOK_REPO_ROOT),
                "--receipt",
                DEFAULT_SYNC_RECEIPT.as_posix(),
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
            _command(
                "optional_sync_barriers",
                "session-seal",
                "Reseal after re-verification succeeds",
                "--run-id",
                DEFAULT_RUN_ID,
                "--seal-epoch",
                "2",
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
        ),
    )


def build_final_closure_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Final Closure / Sync",
        stage="final_closure_sync",
        notes=(
            "The notebook must stop after sync until CLI re-verification and reseal succeed.",
            "After reseal, the handoff is report-only.",
        ),
        commands=(
            _command(
                "final_closure_sync",
                "session-close-seal",
                "Close the final seal before sync",
                "--run-id",
                DEFAULT_RUN_ID,
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
            _command(
                "final_closure_sync",
                "sync-github",
                "Perform the final allowlisted synchronization",
                "--repo",
                str(DEFAULT_NOTEBOOK_REPO_ROOT),
                "--manifest",
                "<SYNC_MANIFEST_PATH>",
                "--allowlist",
                "phase5/configs/sync_allowlist.yaml",
                "--receipt",
                DEFAULT_SYNC_RECEIPT.as_posix(),
            ),
            _command(
                "final_closure_sync",
                "session-reverify",
                "Reverify the checkpoint before reseal",
                "--repo",
                str(DEFAULT_NOTEBOOK_REPO_ROOT),
                "--receipt",
                DEFAULT_SYNC_RECEIPT.as_posix(),
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
            _command(
                "final_closure_sync",
                "session-seal",
                "Reseal only after re-verification passes",
                "--run-id",
                DEFAULT_RUN_ID,
                "--seal-epoch",
                "2",
                "--output",
                DEFAULT_CLI_OUTPUT.as_posix(),
            ),
        ),
    )


def build_report_plan(parameters: KaggleHandoffParameters) -> HandoffPlan:
    validate_handoff_parameters(parameters)
    return HandoffPlan(
        title="Report",
        stage="report",
        notes=(
            "The notebook ends with a summary only.",
            "No Kaggle trial output is generated by this task.",
        ),
    )


def build_sync_environment(
    env: Mapping[str, str] | None = None,
    *,
    write_secret_name: str = WRITE_SECRET_NAME,
) -> dict[str, str]:
    source = dict(env or os.environ)
    if write_secret_name not in source:
        raise SchemaInvariantError(f"required Kaggle Secret missing: {write_secret_name}")
    source[PUBLIC_TOKEN_ENV_NAME] = source[write_secret_name]
    return source


def build_reverify_environment(
    env: Mapping[str, str] | None = None,
    *,
    write_secret_name: str = WRITE_SECRET_NAME,
) -> dict[str, str]:
    source = dict(env or os.environ)
    source.pop(PUBLIC_TOKEN_ENV_NAME, None)
    source.pop(write_secret_name, None)
    return source


def run_public_cli(
    command: str,
    *args: str,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        _cli_argv(command, *args),
        cwd=cwd,
        env=dict(env) if env is not None else None,
        capture_output=True,
        text=True,
        check=True,
    )


def run_bootstrap(
    parameters: KaggleHandoffParameters,
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]:
    plan = build_bootstrap_plan(parameters)
    return tuple(run_public_cli(command.argv[3], *command.argv[4:], cwd=cwd, env=env) for command in plan.commands)


def run_session(
    parameters: KaggleHandoffParameters,
    *,
    model_slot: str,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]:
    validate_handoff_parameters(parameters)
    seal = run_public_cli(
        "session-seal",
        "--run-id",
        DEFAULT_RUN_ID,
        "--seal-epoch",
        "1",
        "--output",
        DEFAULT_CLI_OUTPUT.as_posix(),
        cwd=cwd,
        env=env,
    )
    campaign = run_public_cli(
        "run-campaign",
        "--model-slot",
        model_slot,
        "--run-id",
        DEFAULT_RUN_ID,
        "--utcdate",
        "<YYYYMMDD>",
        "--until-safety-horizon",
        "--batch-manifest",
        DEFAULT_BATCH_MANIFEST.as_posix(),
        "--run-plan",
        DEFAULT_RUN_PLAN.as_posix(),
        "--output",
        DEFAULT_CLI_OUTPUT.as_posix(),
        cwd=cwd,
        env=env,
    )
    return seal, campaign


def run_sync_barrier(
    parameters: KaggleHandoffParameters,
    *,
    manifest_path: Path,
    receipt_path: Path,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]:
    validate_handoff_parameters(parameters)
    close = run_public_cli(
        "session-close-seal",
        "--run-id",
        DEFAULT_RUN_ID,
        "--output",
        DEFAULT_CLI_OUTPUT.as_posix(),
        cwd=cwd,
        env=env,
    )
    sync_env = build_sync_environment(env)
    sync = run_public_cli(
        "sync-github",
        "--repo",
        str(DEFAULT_NOTEBOOK_REPO_ROOT),
        "--manifest",
        str(manifest_path),
        "--allowlist",
        "phase5/configs/sync_allowlist.yaml",
        "--receipt",
        str(receipt_path),
        cwd=cwd,
        env=sync_env,
    )
    reverify_env = build_reverify_environment(sync_env)
    reverify = run_public_cli(
        "session-reverify",
        "--repo",
        str(DEFAULT_NOTEBOOK_REPO_ROOT),
        "--receipt",
        str(receipt_path),
        "--output",
        DEFAULT_CLI_OUTPUT.as_posix(),
        cwd=cwd,
        env=reverify_env,
    )
    reseal = run_public_cli(
        "session-seal",
        "--run-id",
        DEFAULT_RUN_ID,
        "--seal-epoch",
        "2",
        "--output",
        DEFAULT_CLI_OUTPUT.as_posix(),
        cwd=cwd,
        env=reverify_env,
    )
    return close, sync, reverify, reseal


def run_finalize(
    parameters: KaggleHandoffParameters,
    *,
    manifest_path: Path,
    receipt_path: Path,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], subprocess.CompletedProcess[str], subprocess.CompletedProcess[str]]:
    validate_handoff_parameters(parameters)
    return run_sync_barrier(
        parameters,
        manifest_path=manifest_path,
        receipt_path=receipt_path,
        cwd=cwd,
        env=env,
    )
