"""Stable Phase 5 CLI skeleton."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .gate0 import run_gate0
from .kaggle import plan_kaggle_runs
from .domain.errors import ExitCode, NotImplementedCommandError, Phase5Error
from .domain.session import Phase5Session
from .sync.github_checkpoint import perform_session_reverify, perform_sync_github


PLANNED_COMMANDS = (
    "gate0",
    "plan-kaggle-runs",
    "run-batch",
    "validate-batch",
    "validate-phase",
    "session-seal",
    "session-reverify",
    "sync-github",
    "generate-qa-sample",
    "build-phase6-handoff",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="phase5",
        description="Phase 5 scaffold CLI. Gate 0 and Kaggle run planning are implemented; other commands remain not implemented.",
    )
    parser.add_argument("--version", action="version", version=f"phase5 {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    gate0 = subparsers.add_parser(
        "gate0",
        help="Run the strict Phase 5 entry gate.",
        description="Run strict Gate 0 authorization and frozen-artifact verification.",
    )
    gate0.add_argument("--strict", action="store_true", help="Require a clean checkout.")
    gate0.add_argument("--root", required=False)
    gate0.add_argument("--report-dir", required=False)
    gate0.set_defaults(command="gate0")

    def add_planned_command(name: str, help_text: str) -> argparse.ArgumentParser:
        command_parser = subparsers.add_parser(
            name,
            help=help_text,
            description=f"{name} is part of the planned Phase 5 command surface and returns NOT_IMPLEMENTED.",
        )
        command_parser.set_defaults(command=name)
        return command_parser

    plan = add_planned_command("plan-kaggle-runs", "Plan Kaggle sessions from frozen timing evidence.")
    plan.add_argument("--timing-report", required=False)
    plan.add_argument("--safe-session-hours", required=False, type=float)
    plan.add_argument("--output", required=False)

    run_batch = add_planned_command("run-batch", "Execute a single frozen batch.")
    run_batch.add_argument("--batch-id", required=False)

    validate_batch = add_planned_command("validate-batch", "Validate a frozen batch contract.")
    validate_batch.add_argument("--batch-id", required=False)
    validate_batch.add_argument("--strict", action="store_true")

    validate_phase = add_planned_command("validate-phase", "Validate a Phase 5 contract slice.")
    validate_phase.add_argument("--strict", action="store_true")

    session_seal = add_planned_command("session-seal", "Open a new seal epoch.")
    session_seal.add_argument("--run-id", required=False)
    session_seal.add_argument("--seal-epoch", required=False, type=int)

    session_reverify = add_planned_command("session-reverify", "Reverify source/frozen hashes after sync.")
    session_reverify.add_argument("--repo", required=False, default=".")
    session_reverify.add_argument("--receipt", required=True)

    sync = add_planned_command("sync-github", "Synchronize finalized evidence after seal closure.")
    sync.add_argument("--repo", required=False, default=".")
    sync.add_argument("--manifest", required=True)
    sync.add_argument("--allowlist", required=False, default="phase5/configs/sync_allowlist.yaml")
    sync.add_argument("--receipt", required=True)
    sync.add_argument("--trial-process-running", action="store_true")

    qa = add_planned_command("generate-qa-sample", "Generate the frozen QA sample.")
    qa.add_argument("--output", required=False)

    handoff = add_planned_command("build-phase6-handoff", "Build the Phase 6 handoff manifest.")
    handoff.add_argument("--output", required=False)

    return parser


def _handle_not_implemented(command: str) -> int:
    raise NotImplementedCommandError(f"phase5 command {command!r} is not implemented yet")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    if argv is not None and len(argv) == 0:
        parser.print_help()
        return int(ExitCode.SUCCESS)

    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return int(ExitCode.SUCCESS)

    if args.command == "gate0":
        try:
            root = Path(args.root) if getattr(args, "root", None) else None
            report_dir = (
                Path(args.report_dir)
                if getattr(args, "report_dir", None)
                else (root or Path.cwd()) / "phase5" / "validation"
            )
            report = run_gate0(strict=bool(args.strict), report_dir=report_dir, root=root)
            if report.status != "PASS":
                print("GATE0_FAILURE:", file=sys.stderr)
                for finding in report.findings:
                    print(f"- {finding}", file=sys.stderr)
                return int(ExitCode.GATE0_FAILURE)
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"GATE0_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "plan-kaggle-runs":
        try:
            root = Path.cwd()
            timing_report = Path(args.timing_report) if getattr(args, "timing_report", None) else None
            safe_session_hours = getattr(args, "safe_session_hours", None)
            output = Path(args.output) if getattr(args, "output", None) else None
            plan_kaggle_runs(
                root=root,
                timing_report_path=timing_report,
                safe_session_hours=safe_session_hours,
                output_path=output,
            )
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"PLAN_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "sync-github":
        try:
            session, _receipt = perform_sync_github(
                session=Phase5Session.initial().seal().close_after_finalization(),
                repo=Path(args.repo),
                manifest_path=Path(args.manifest),
                allowlist_path=Path(args.allowlist),
                receipt_path=Path(args.receipt),
                trial_process_running=bool(args.trial_process_running),
            )
            if session.state.value != "UNSEALED_SYNCED":
                raise Phase5Error("sync-github did not transition to UNSEALED_SYNCED")
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"SYNC_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "session-reverify":
        try:
            session, _result = perform_session_reverify(
                session=Phase5Session.initial().seal().close_after_finalization().begin_sync().finish_sync(),
                repo=Path(args.repo),
                receipt_path=Path(args.receipt),
            )
            if session.state.value != "REVERIFIED_AFTER_SYNC":
                raise Phase5Error("session-reverify did not transition to REVERIFIED_AFTER_SYNC")
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"REVERIFY_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    try:
        return _handle_not_implemented(args.command)
    except Phase5Error as exc:
        print(f"NOT_IMPLEMENTED: {exc}", file=sys.stderr)
        return int(exc.exit_code)
