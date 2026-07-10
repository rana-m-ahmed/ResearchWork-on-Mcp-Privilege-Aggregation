"""Stable Phase 5 CLI skeleton."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from . import __version__
from .campaign import build_dashboard, build_resume_plan, run_campaign
from .gate0 import run_gate0
from .kaggle import plan_kaggle_runs
from .domain.errors import ExitCode, NotImplementedCommandError, Phase5Error
from .domain.enums import ModelSlot
from .domain.identifiers import BatchId
from .domain.session import Phase5Session
from .runtime.session import CampaignSession
from .sync.github_checkpoint import perform_session_reverify, perform_sync_github


PLANNED_COMMANDS = (
    "gate0",
    "plan-kaggle-runs",
    "checkpoint-status",
    "resume-plan",
    "run-campaign",
    "session-open",
    "session-close-seal",
    "session-seal",
    "session-reverify",
    "sync-github",
    "run-batch",
    "validate-batch",
    "validate-phase",
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

    status = add_planned_command("checkpoint-status", "Render the operational-only dashboard.")
    status.add_argument("--model-slot", required=True)
    status.add_argument("--run-id", required=False)
    status.add_argument("--batch-manifest", required=False, default="phase5/manifests/batch_partition_manifest_v2.json")
    status.add_argument("--run-plan", required=False, default="phase5/validation/kaggle_run_plan_v2.json")
    status.add_argument("--output", required=False)

    resume = add_planned_command("resume-plan", "Render the next contiguous campaign slice.")
    resume.add_argument("--model-slot", required=True)
    resume.add_argument("--run-id", required=False)
    resume.add_argument("--batch-manifest", required=False, default="phase5/manifests/batch_partition_manifest_v2.json")
    resume.add_argument("--run-plan", required=False, default="phase5/validation/kaggle_run_plan_v2.json")
    resume.add_argument("--output", required=False)

    run_campaign = add_planned_command("run-campaign", "Run the unified long-running campaign loop.")
    run_campaign.add_argument("--model-slot", required=True)
    run_campaign.add_argument("--run-id", required=False)
    run_campaign.add_argument("--utcdate", required=False)
    run_campaign.add_argument("--until-safety-horizon", action="store_true")
    run_campaign.add_argument("--batch-manifest", required=False, default="phase5/manifests/batch_partition_manifest_v2.json")
    run_campaign.add_argument("--run-plan", required=False, default="phase5/validation/kaggle_run_plan_v2.json")
    run_campaign.add_argument("--output", required=False)

    session_open = add_planned_command("session-open", "Open a new operational campaign session.")
    session_open.add_argument("--model-slot", required=True)
    session_open.add_argument("--batch-id", required=True)
    session_open.add_argument("--run-id", required=False)
    session_open.add_argument("--utcdate", required=False)
    session_open.add_argument("--output", required=False)

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
    session_seal.add_argument("--output", required=False)

    session_close = add_planned_command("session-close-seal", "Close the active seal after finalization.")
    session_close.add_argument("--run-id", required=False)
    session_close.add_argument("--output", required=False)

    session_reverify = add_planned_command("session-reverify", "Reverify source/frozen hashes after sync.")
    session_reverify.add_argument("--repo", required=False, default=".")
    session_reverify.add_argument("--receipt", required=True)
    session_reverify.add_argument("--output", required=False)

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


def _default_json_report_path(output: str | None, default_path: Path) -> tuple[Path, Path]:
    if output:
        output_path = Path(output)
        if output_path.suffix.lower() == ".md":
            return output_path.with_suffix(".json"), output_path
        if output_path.suffix.lower() == ".json":
            return output_path, output_path.with_suffix(".md")
        return output_path, output_path.with_suffix(".md")
    return default_path, default_path.with_suffix(".md")


def _write_json_md_report(report: object, output: str | None, default_path: Path) -> None:
    json_path, md_path = _default_json_report_path(output, default_path)
    to_mapping = getattr(report, "to_mapping", None)
    to_markdown = getattr(report, "to_markdown", None)
    if not callable(to_mapping) or not callable(to_markdown):
        raise Phase5Error("report object must provide to_mapping() and to_markdown()")
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(to_mapping(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(), encoding="utf-8")


def _session_state_payload(command: str, session: Phase5Session, *, run_id: str | None = None) -> dict[str, object]:
    payload: dict[str, object] = {
        "command": command,
        "phase5_session": {
            "seal_epoch": session.seal_epoch,
            "state": session.state.value,
            "sync_epoch": session.sync_epoch,
        },
    }
    if run_id is not None:
        payload["run_id"] = run_id
    return payload


def _session_state_markdown(payload: dict[str, object]) -> str:
    session = payload["phase5_session"]
    assert isinstance(session, dict)
    lines = [
        "# P14 Session Report",
        "",
        f"- Command: `{payload['command']}`",
    ]
    if "run_id" in payload:
        lines.append(f"- Run ID: `{payload['run_id']}`")
    lines.extend(
        [
            f"- Session state: `{session['state']}`",
            f"- Seal epoch: `{session['seal_epoch']}`",
            f"- Sync epoch: `{session['sync_epoch']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def _write_session_report(session: Phase5Session, command: str, output: str | None, default_path: Path, *, run_id: str | None = None) -> None:
    payload = _session_state_payload(command, session, run_id=run_id)
    json_path, md_path = _default_json_report_path(output, default_path)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_session_state_markdown(payload), encoding="utf-8")


def _parse_model_slot(value: str) -> ModelSlot:
    return ModelSlot.from_value(value)


def _parse_batch_id(value: str) -> BatchId:
    return BatchId.parse(value)


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

    if args.command == "checkpoint-status":
        try:
            report = build_dashboard(
                model_slot=_parse_model_slot(args.model_slot),
                run_id=getattr(args, "run_id", None),
                run_plan_path=Path(args.run_plan),
                batch_manifest_path=Path(args.batch_manifest),
            )
            _write_json_md_report(report, getattr(args, "output", None), Path("phase5/validation/checkpoint_status.json"))
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"STATUS_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "resume-plan":
        try:
            report = build_resume_plan(
                model_slot=_parse_model_slot(args.model_slot),
                run_id=getattr(args, "run_id", None),
                run_plan_path=Path(args.run_plan),
                batch_manifest_path=Path(args.batch_manifest),
            )
            _write_json_md_report(report, getattr(args, "output", None), Path("phase5/validation/campaign_resume_plan.json"))
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"RESUME_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "run-campaign":
        try:
            session, report = run_campaign(
                model_slot=_parse_model_slot(args.model_slot),
                run_id=getattr(args, "run_id", None),
                utcdate=getattr(args, "utcdate", None),
                until_safety_horizon=bool(args.until_safety_horizon),
                batch_manifest_path=Path(args.batch_manifest),
                run_plan_path=Path(args.run_plan),
                root=Path.cwd(),
                session=None,
            )
            _write_json_md_report(report, getattr(args, "output", None), Path("phase5/validation/campaign_run_report.json"))
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"CAMPAIGN_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "session-open":
        try:
            batch_id = _parse_batch_id(args.batch_id)
            session = CampaignSession.open(
                model_slot=_parse_model_slot(args.model_slot),
                batch_id=batch_id,
                run_id=getattr(args, "run_id", None),
                utcdate=getattr(args, "utcdate", None),
                time_to_safety_horizon_seconds=None,
            )
            _write_json_md_report(session, getattr(args, "output", None), Path("phase5/validation/session_open_report.json"))
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"SESSION_OPEN_FAILURE: {exc}", file=sys.stderr)
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
            _write_session_report(
                session,
                "session-reverify",
                getattr(args, "output", None),
                Path("phase5/validation/session_reverify_report.json"),
            )
            if session.state.value != "REVERIFIED_AFTER_SYNC":
                raise Phase5Error("session-reverify did not transition to REVERIFIED_AFTER_SYNC")
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"REVERIFY_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "session-seal":
        try:
            session = Phase5Session.initial().seal()
            if args.seal_epoch is not None and args.seal_epoch != session.seal_epoch:
                raise Phase5Error(
                    f"requested seal epoch {args.seal_epoch} does not match the frozen transition result {session.seal_epoch}"
                )
            _write_session_report(
                session,
                "session-seal",
                getattr(args, "output", None),
                Path("phase5/validation/session_seal_report.json"),
                run_id=getattr(args, "run_id", None),
            )
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"SEAL_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    if args.command == "session-close-seal":
        try:
            session = Phase5Session.initial().seal().close_after_finalization()
            _write_session_report(
                session,
                "session-close-seal",
                getattr(args, "output", None),
                Path("phase5/validation/session_close_seal_report.json"),
                run_id=getattr(args, "run_id", None),
            )
            return int(ExitCode.SUCCESS)
        except Phase5Error as exc:
            print(f"CLOSE_SEAL_FAILURE: {exc}", file=sys.stderr)
            return int(exc.exit_code)

    try:
        return _handle_not_implemented(args.command)
    except Phase5Error as exc:
        print(f"NOT_IMPLEMENTED: {exc}", file=sys.stderr)
        return int(exc.exit_code)
