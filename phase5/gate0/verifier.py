"""Strict, fail-closed Gate 0 verification for Phase 5 dispatch."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Callable, Iterable, Mapping

try:  # pragma: no cover - optional dependency is validated in tests
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from ..domain.config import load_upstream_artifact_registry
from ..domain.errors import Phase5Error
from ..guards import repo_root


_PHASE4_GO_LABEL = "Phase 4 GO report"
_PHASE45_GO_LABEL = "Phase 4.5 GO report"
_MODEL_LABELS = ("Model freeze set", "Model freeze M1", "Model freeze M2", "Model freeze M3", "Model freeze M4")
_QUEUE_LABELS = ("Trial order core", "Trial order defense", "Trial order utility", "Phase 5 execution manifest")
_EVIDENCE_LABELS = (
    "Phase 4 global freeze",
    "Defense freeze",
    "Statistical plan",
    "Phase 5 schema freeze",
    "Payload reference map",
    "Cryptographic lock manifest",
    "Master hash ledger",
    "Phase 4.5 GO report",
    "Schema mapping",
    "Log schema",
    "Reset",
    "Kaggle runtime setup",
    "Checkpoint/resume config",
    "Checkpoint/resume report",
    "Timing evidence, local run manifest",
    "Timing evidence, Kaggle smoke hardware metrics",
    "Timing evidence, Kaggle model-loader hardware metrics",
    "Phase 2.5 tokenizer validation report",
    "Logical-ID grader",
    "Model backend abstraction",
    "Tool call parser",
    "Tool definition read_internal_notes",
    "Tool definition write_outbox",
    "Tool definition get_local_weather",
    "Tool definition query_local_inventory",
    "Tool definition log_event",
)
_MODEL_EXPECTATIONS = {
    "M1": {
        "exact_model_identifier": "Qwen/Qwen2.5-7B-Instruct",
        "runtime_backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "tokenizer_identity": "Qwen/Qwen2.5-7B-Instruct",
        "quantization": "float16",
        "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
    },
    "M2": {
        "exact_model_identifier": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "runtime_backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "tokenizer_identity": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
        "quantization": "float16",
        "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
    },
    "M3": {
        "exact_model_identifier": "mistralai/Mistral-7B-Instruct-v0.3",
        "runtime_backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "tokenizer_identity": "mistralai/Mistral-7B-Instruct-v0.3",
        "quantization": "float16",
        "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
    },
    "M4": {
        "exact_model_identifier": "microsoft/Phi-3.5-mini-instruct",
        "runtime_backend": "transformers",
        "backend_version": "transformers==5.0.0",
        "tokenizer_identity": "microsoft/Phi-3.5-mini-instruct",
        "quantization": "float16",
        "model_digest": "UNAVAILABLE_NOT_RECORDED_IN_PHASE3",
    },
}
_EXPECTED_QUEUE_HEADER = (
    "trial_id",
    "model_id",
    "density",
    "metadata_surface_condition",
    "attack_family",
    "defense_condition",
    "payload_id",
    "phase1_payload_hash",
    "task_id",
    "task_hash",
    "payload_condition",
    "status",
)
_GATE0_REPORT_MD = "gate0_authorization_report.md"
_GATE0_REPORT_JSON = "gate0_authorization_report.json"
_PHASE3_SOURCE_MANIFEST = Path("reproducibility/phase3_hash_manifest.json")
_PHASE45_ENV_LOCK = Path("phase4_5/configs/phase45_environment_lock.yaml")
_PHASE45_RUNTIME_SETUP = Path("phase4_5/kaggle/kaggle_runtime_setup.md")
_PHASE45_LOCAL_RUN_MANIFEST = Path("phase4_5/dryrun_results/local/run_manifest.json")
_PHASE45_KAGGLE_TRIALS = Path("phase4_5/dryrun_results/kaggle_smoke/trials.jsonl")
_PHASE45_KAGGLE_SMOKE_METRICS = Path("phase4_5/dryrun_results/kaggle_smoke/hardware_metrics.jsonl")
_PHASE45_MODEL_LOADER_METRICS = Path(
    "phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_hardware_metrics.jsonl"
)


@dataclass(frozen=True, slots=True)
class Gate0Check:
    name: str
    status: str
    details: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Gate0Report:
    task_id: str
    status: str
    strict: bool
    generated_utc: str
    repository_root: str
    summary: str
    findings: tuple[str, ...]
    checks: tuple[Gate0Check, ...]
    verified_artifacts: tuple[tuple[str, str, str], ...]
    consumed_frozen_inputs: tuple[tuple[str, str], ...]
    verdicts: tuple[tuple[str, str], ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "status": self.status,
            "strict": self.strict,
            "generated_utc": self.generated_utc,
            "repository_root": self.repository_root,
            "summary": self.summary,
            "findings": list(self.findings),
            "checks": [
                {"name": check.name, "status": check.status, "details": list(check.details)}
                for check in self.checks
            ],
            "verified_artifacts": [
                {"label": label, "path": path, "sha256": sha256}
                for label, path, sha256 in self.verified_artifacts
            ],
            "consumed_frozen_inputs": [
                {"label": label, "sha256": sha256} for label, sha256 in self.consumed_frozen_inputs
            ],
            "verdicts": [{"label": label, "value": value} for label, value in self.verdicts],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# Gate 0 Authorization Report",
            "",
            "## Verdict",
            "",
            f"- Status: `{self.status}`",
            f"- Task: `{self.task_id}`",
            f"- Strict: `{str(self.strict).lower()}`",
            f"- Generated UTC: `{self.generated_utc}`",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Checks",
        ]
        for check in self.checks:
            lines.append(f"- {check.name}: {check.status}")
            for detail in check.details:
                lines.append(f"  - {detail}")
        lines.extend(
            [
                "",
                "## Findings",
            ]
        )
        if self.findings:
            lines.extend(f"- {item}" for item in self.findings)
        else:
            lines.append("- none")
        lines.extend(
            [
                "",
                "## Verified Artifacts",
            ]
        )
        for label, path, sha256 in self.verified_artifacts:
            lines.append(f"- {label}: `{path}` `{sha256}`")
        lines.extend(
            [
                "",
                "## Frozen Inputs",
            ]
        )
        for label, sha256 in self.consumed_frozen_inputs:
            lines.append(f"- {label}: `{sha256}`")
        lines.extend(
            [
                "",
                "## Verdicts",
            ]
        )
        for label, value in self.verdicts:
            lines.append(f"- {label}: `{value}`")
        lines.extend(["", "## Output Files", "", f"- `{_GATE0_REPORT_MD}`", f"- `{_GATE0_REPORT_JSON}`"])
        return "\n".join(lines) + "\n"

    def write(self, report_dir: Path) -> None:
        report_dir.mkdir(parents=True, exist_ok=True)
        (report_dir / _GATE0_REPORT_MD).write_text(self.to_markdown(), encoding="utf-8")
        (report_dir / _GATE0_REPORT_JSON).write_text(self.to_json(), encoding="utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_json(path: Path) -> Mapping[str, object]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise Phase5Error(f"{path.as_posix()} must contain a JSON object")
    return data


def _load_yaml(path: Path) -> Mapping[str, object] | list[object]:
    if yaml is None:
        raise Phase5Error("pyyaml is required for Gate 0 verification")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, (dict, list)):
        raise Phase5Error(f"{path.as_posix()} must contain a YAML mapping or sequence")
    return data


def _record_artifact(label: str, entry) -> tuple[str, str, str]:
    return label, entry.actual_paths[0].as_posix(), entry.sha256[0]


def _check_result(name: str, ok: bool, *details: str) -> Gate0Check:
    return Gate0Check(name=name, status="PASS" if ok else "FAIL", details=tuple(details))


def _findings_for_check(check: Gate0Check) -> list[str]:
    if check.status == "PASS":
        return []
    return [f"{check.name}: {detail}" for detail in check.details] or [f"{check.name}: failed"]


def _parse_phase4_go_report(path: Path) -> Gate0Check:
    text = _load_text(path)
    status_match = re.search(r"(?im)^Status:\s*(PASS|FAIL|CONDITIONAL_PASS|READY_FOR_PHASE5)\s*$", text)
    evidence_match = re.search(r"(?is)```json\s*(\{.*?\})\s*```", text)
    if status_match is None:
        return _check_result("phase4-go-verdict", False, f"missing status line in {path.as_posix()}")
    if evidence_match is None:
        return _check_result("phase4-go-verdict", False, f"missing evidence block in {path.as_posix()}")
    evidence = json.loads(evidence_match.group(1))
    if not isinstance(evidence, dict):
        return _check_result("phase4-go-verdict", False, f"invalid evidence block in {path.as_posix()}")
    ready = evidence.get("ready_for_phase5")
    missing_dependencies = evidence.get("missing_dependencies")
    ok = status_match.group(1) == "PASS" and ready is True and missing_dependencies == []
    details = [
        f"status={status_match.group(1)}",
        f"ready_for_phase5={ready!r}",
        f"missing_dependencies={missing_dependencies!r}",
    ]
    return _check_result("phase4-go-verdict", ok, *details)


def _parse_phase45_go_report(path: Path) -> Gate0Check:
    text = _load_text(path)
    verdict_match = re.search(r"(?im)^-\s*Final verdict:\s*`?([A-Z0-9_ ]+)`?\s*$", text)
    corrected = "GO TO PHASE 5 REBINDING" in text
    required_phrases = (
        {
            "Schema mapping: `PASS`",
            "Payload loading and hashes: `PASS`",
            "Prompt compilation: `PASS`",
            "Token budgets: `PASS`",
            "Grader: `PASS`",
            "TID: `PASS`",
            "Reset/isolation: `PASS`",
            "Write-ahead logging: `PASS`",
            "Checkpoint/resume: `PASS`",
            "Utility smoke: `PASS`",
            "Outcome taxonomy: `PASS`",
            "Model/tokenizer/backend identity: `PASS`",
            "Timing and run-plan inputs: `PASS`",
            "Forbidden claims checks: `PASS`",
        }
        if corrected
        else {
            "Preflight: `PASS`",
            "Schema mapping: `PASS`",
            "Statistics smoke: `PASS`",
            "Forbidden claims lint: `PASS`",
            "Kaggle authentic quota feasibility: `CALCULATED`",
        }
    )
    if verdict_match is None:
        return _check_result("phase45-go-verdict", False, f"missing final verdict in {path.as_posix()}")
    missing = sorted(phrase for phrase in required_phrases if phrase not in text)
    ok = verdict_match.group(1) in {"READY_FOR_EXTERNAL_AUDIT", "GO TO PHASE 5 REBINDING"} and not missing
    details = [f"final_verdict={verdict_match.group(1)}"]
    if missing:
        details.extend(f"missing:{item}" for item in missing)
    return _check_result("phase45-go-verdict", ok, *details)


def _verify_registry(root: Path) -> tuple[object, dict[str, object], list[Gate0Check], list[str]]:
    registry = load_upstream_artifact_registry(root / "phase5" / "configs" / "upstream_artifact_registry.json")
    registry_doc = _load_json(registry.source_path)
    checks = [
        _check_result(
            "registry-status",
            registry.registry_id == "P00" and registry.status == "COMPLETE",
            f"registry_id={registry.registry_id}",
            f"status={registry.status}",
        )
    ]
    findings = _findings_for_check(checks[0])
    go_verdicts = registry_doc.get("go_verdicts")
    if not isinstance(go_verdicts, dict):
        checks.append(_check_result("registry-go-verdicts", False, "missing go_verdicts"))
        findings.extend(_findings_for_check(checks[-1]))
    else:
        phase4 = go_verdicts.get("phase4", {})
        phase45 = go_verdicts.get("phase4_5", {})
        checks.append(
            _check_result(
                "registry-go-verdicts",
                isinstance(phase4, dict)
                and isinstance(phase45, dict)
                and phase4.get("status") == "PASS"
                and phase45.get("status") in {"READY_FOR_EXTERNAL_AUDIT", "GO TO PHASE 5 REBINDING"},
                f"phase4={phase4.get('status')!r}",
                f"phase4_5={phase45.get('status')!r}",
            )
        )
        findings.extend(_findings_for_check(checks[-1]))
    return registry, registry_doc, checks, findings


def _verify_required_labels(registry, labels: Iterable[str]) -> tuple[list[tuple[str, str, str]], list[Gate0Check], list[str]]:
    artifacts: list[tuple[str, str, str]] = []
    checks: list[Gate0Check] = []
    findings: list[str] = []
    for label in labels:
        try:
            entry = registry.require(label)
        except Phase5Error as exc:
            check = _check_result(f"registry-label:{label}", False, str(exc))
            checks.append(check)
            findings.extend(_findings_for_check(check))
            continue
        artifacts.append(_record_artifact(label, entry))
        check = _check_result(f"registry-label:{label}", True, entry.actual_paths[0].as_posix(), entry.sha256[0])
        checks.append(check)
    return artifacts, checks, findings


def _verify_queue_file(
    path: Path,
    expected_sha256: str | None = None,
    expected_row_count: int | None = None,
) -> tuple[Gate0Check, dict[str, object]]:
    actual_sha256 = _sha256_file(path)
    if expected_sha256 is not None and actual_sha256.lower() != expected_sha256.lower():
        return _check_result(
            "queue-hash",
            False,
            f"{path.as_posix()}: expected {expected_sha256}",
            f"got {actual_sha256}",
        ), {}

    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return _check_result("queue-shape", False, f"{path.as_posix()} is empty"), {}
    header = tuple(rows[0])
    if header != _EXPECTED_QUEUE_HEADER:
        return _check_result(
            "queue-header",
            False,
            f"{path.as_posix()}: expected header={_EXPECTED_QUEUE_HEADER!r}",
            f"got header={header!r}",
        ), {}

    data_rows = rows[1:]
    non_empty_cells = sum(1 for row in data_rows for cell in row if cell != "")
    row_count = len(data_rows)
    unique_rows = len({tuple(row) for row in data_rows})
    unique_trial_ids = len({row[0] for row in data_rows}) if data_rows else 0
    unique_payload_ids = len({row[6] for row in data_rows if row[6]}) if data_rows else 0
    counts_by_model = Counter(row[1] for row in data_rows)
    counts_by_density = Counter(row[2] for row in data_rows)
    counts_by_defense = Counter(row[5] for row in data_rows)
    status_values = {row[11] for row in data_rows}
    ok = all(len(row) == len(_EXPECTED_QUEUE_HEADER) for row in data_rows) and status_values == {"PENDING"}
    if expected_row_count is not None:
        ok = ok and row_count == expected_row_count and unique_rows == row_count
    details = [
        f"rows={row_count}",
        f"cells={non_empty_cells}",
        f"unique_rows={unique_rows}",
        f"unique_trial_ids={unique_trial_ids}",
        f"unique_payload_ids={unique_payload_ids}",
        f"models={dict(sorted(counts_by_model.items()))}",
        f"densities={dict(sorted(counts_by_density.items()))}",
        f"defense={dict(sorted(counts_by_defense.items()))}",
        f"statuses={sorted(status_values)}",
        f"sha256={actual_sha256}",
    ]
    return _check_result("queue-file", ok, *details), {
        "row_count": row_count,
        "non_empty_cells": non_empty_cells,
        "unique_rows": unique_rows,
        "unique_trial_ids": unique_trial_ids,
        "unique_payload_ids": unique_payload_ids,
        "counts_by_model": dict(sorted(counts_by_model.items())),
        "counts_by_density": dict(sorted(counts_by_density.items())),
        "counts_by_defense": dict(sorted(counts_by_defense.items())),
        "statuses": sorted(status_values),
        "sha256": actual_sha256,
    }


def _verify_zero_row_queue(path: Path, expected_sha256: str | None = None) -> Gate0Check:
    actual_sha256 = _sha256_file(path)
    if expected_sha256 is not None and actual_sha256.lower() != expected_sha256.lower():
        return _check_result(
            "queue-hash",
            False,
            f"{path.as_posix()}: expected {expected_sha256}",
            f"got {actual_sha256}",
        )
    rows = list(csv.reader(path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        return _check_result("queue-header", False, f"{path.as_posix()} is missing a header")
    header = tuple(rows[0])
    ok = len(rows[1:]) == 0 and len(header) >= 2
    return _check_result(
        "queue-empty-file",
        ok,
        f"rows={len(rows) - 1}",
        f"header={header!r}",
        f"sha256={actual_sha256}",
    )


def _verify_model_frozen_files(root: Path, registry_doc: Mapping[str, object]) -> tuple[list[Gate0Check], list[str], tuple[tuple[str, str], ...]]:
    checks: list[Gate0Check] = []
    findings: list[str] = []
    consumed: list[tuple[str, str]] = []
    phase3_manifest = _load_json(root / _PHASE3_SOURCE_MANIFEST)
    phase3_source_hash = phase3_manifest.get("global_source")
    if not isinstance(phase3_source_hash, str) or not re.fullmatch(r"[a-f0-9]{64}", phase3_source_hash):
        check = _check_result("phase3-source-hash", False, "missing or invalid global_source")
        checks.append(check)
        findings.extend(_findings_for_check(check))
        phase3_source_hash = None
    else:
        checks.append(_check_result("phase3-source-hash", True, phase3_source_hash))
        consumed.append(("Phase 3 common-source hash", phase3_source_hash))

    model_set = _load_yaml(root / "phase4" / "configs" / "model_set_freeze.yaml")
    if not isinstance(model_set, dict):
        check = _check_result("model-set", False, "model_set_freeze.yaml must contain a mapping")
        checks.append(check)
        findings.extend(_findings_for_check(check))
        return checks, findings, tuple(consumed)

    expected_mapping = {slot: spec["exact_model_identifier"] for slot, spec in _MODEL_EXPECTATIONS.items()}
    check = _check_result(
        "model-set",
        dict(model_set) == expected_mapping,
        f"expected={expected_mapping}",
        f"got={dict(model_set)}",
    )
    checks.append(check)
    findings.extend(_findings_for_check(check))

    for slot, expectations in _MODEL_EXPECTATIONS.items():
        path = root / "phase4" / "configs" / f"model_{slot[1]}_freeze.yaml"
        model_doc = _load_yaml(path)
        if not isinstance(model_doc, dict):
            check = _check_result(f"model-freeze:{slot}", False, f"{path.as_posix()} must be a mapping")
            checks.append(check)
            findings.extend(_findings_for_check(check))
            continue
        consumed.append((f"{slot} freeze", _sha256_file(path)))
        required = {
            "model_slot": slot,
            "exact_model_identifier": expectations["exact_model_identifier"],
            "runtime_backend": expectations["runtime_backend"],
            "backend_version": expectations["backend_version"],
            "tokenizer_identity": expectations["tokenizer_identity"],
            "quantization": expectations["quantization"],
            "model_digest": expectations["model_digest"],
        }
        if phase3_source_hash is not None:
            required["phase3_source_freeze_hash"] = phase3_source_hash
        mismatches = []
        for key, expected_value in required.items():
            actual_value = model_doc.get(key)
            if actual_value != expected_value:
                mismatches.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
        check = _check_result(f"model-freeze:{slot}", not mismatches, *mismatches or (path.as_posix(),))
        checks.append(check)
        findings.extend(_findings_for_check(check))

    return checks, findings, tuple(consumed)


def _verify_runtime_contract(root: Path) -> tuple[list[Gate0Check], list[str], tuple[tuple[str, str], ...], str]:
    checks: list[Gate0Check] = []
    findings: list[str] = []
    consumed: list[tuple[str, str]] = []
    env_lock = _load_yaml(root / _PHASE45_ENV_LOCK)
    if not isinstance(env_lock, dict):
        check = _check_result("runtime-env-lock", False, "environment lock must be a mapping")
        checks.append(check)
        findings.extend(_findings_for_check(check))
        return checks, findings, tuple(consumed), ""

    required_truths = {
        "source_of_truth": "github",
        "local_validation_enabled": True,
        "kaggle_execution_enabled": True,
        "return_outputs_to_github": True,
        "non_official_boundary": True,
        "no_model_weights": True,
        "no_caches": True,
        "no_env_files": True,
        "no_credentials": True,
        "no_absolute_paths": True,
    }
    mismatches = []
    for key, expected_value in required_truths.items():
        actual_value = env_lock.get(key)
        if actual_value != expected_value:
            mismatches.append(f"{key}: expected {expected_value!r}, got {actual_value!r}")
    check = _check_result("runtime-env-lock", not mismatches, *mismatches or ("environment lock verified",))
    checks.append(check)
    findings.extend(_findings_for_check(check))

    runtime_setup = _load_text(root / _PHASE45_RUNTIME_SETUP)
    if "nested docker" in runtime_setup.lower():
        check = _check_result("runtime-setup", False, "nested Docker is forbidden")
    else:
        check = _check_result(
            "runtime-setup",
            "smoke preparation only" in runtime_setup.lower() and "no official trial rows" in runtime_setup.lower(),
            "smoke-only runtime confirmed" if "smoke preparation only" in runtime_setup.lower() else "missing smoke-only boundary",
        )
    checks.append(check)
    findings.extend(_findings_for_check(check))

    local_run = _load_json(root / _PHASE45_LOCAL_RUN_MANIFEST)
    git_commit_hash = local_run.get("git_commit_hash")
    if not isinstance(git_commit_hash, str) or not re.fullmatch(r"[a-f0-9]{40}", git_commit_hash):
        check = _check_result("runtime-source-commit", False, "missing or invalid git_commit_hash")
    else:
        check = _check_result("runtime-source-commit", True, git_commit_hash)
        consumed.append(("Phase 4.5 source commit", git_commit_hash))
    checks.append(check)
    findings.extend(_findings_for_check(check))

    if isinstance(git_commit_hash, str) and re.fullmatch(r"[a-f0-9]{40}", git_commit_hash):
        smoke_trials = _load_text(root / _PHASE45_KAGGLE_TRIALS).splitlines()
        first_trial = json.loads(smoke_trials[0]) if smoke_trials else {}
        if not isinstance(first_trial, dict):
            check = _check_result("runtime-kaggle-trials", False, "missing first trial entry")
        else:
            check = _check_result(
                "runtime-kaggle-trials",
                first_trial.get("dry_run") is True
                and first_trial.get("counts_for_phase5") is False
                and isinstance(first_trial.get("trial"), dict)
                and first_trial.get("trial", {}).get("backend") == "transformers"
                and isinstance(first_trial.get("trial", {}).get("git_commit_hash"), str)
                and re.fullmatch(r"[a-f0-9]{40}", first_trial.get("trial", {}).get("git_commit_hash", "")) is not None,
                f"trial_commit={first_trial.get('trial', {}).get('git_commit_hash')!r}",
                f"run_manifest_commit={git_commit_hash}",
            )
        checks.append(check)
        findings.extend(_findings_for_check(check))

    metrics_count = sum(1 for line in _load_text(root / _PHASE45_KAGGLE_SMOKE_METRICS).splitlines() if line.strip())
    loader_count = sum(1 for line in _load_text(root / _PHASE45_MODEL_LOADER_METRICS).splitlines() if line.strip())
    check = _check_result(
        "runtime-metrics-count",
        metrics_count == 8 and loader_count == 4,
        f"kaggle_smoke_rows={metrics_count}",
        f"model_loader_rows={loader_count}",
    )
    checks.append(check)
    findings.extend(_findings_for_check(check))

    consumed.append(("Phase 4.5 runtime setup", _sha256_file(root / _PHASE45_RUNTIME_SETUP)))
    consumed.append(("Phase 4.5 environment lock", _sha256_file(root / _PHASE45_ENV_LOCK)))
    return checks, findings, tuple(consumed), git_commit_hash if isinstance(git_commit_hash, str) else ""


def _verify_queue_statistics(
    root: Path,
    registry,
    registry_doc: Mapping[str, object],
) -> tuple[list[Gate0Check], list[str], tuple[tuple[str, str], ...]]:
    checks: list[Gate0Check] = []
    findings: list[str] = []
    consumed: list[tuple[str, str]] = []
    queue_stats = registry_doc.get("queue_statistics")
    if not isinstance(queue_stats, dict):
        check = _check_result("queue-statistics", False, "missing queue_statistics")
        checks.append(check)
        findings.extend(_findings_for_check(check))
        return checks, findings, tuple(consumed)

    core_path = root / registry.require("Trial order core").actual_paths[0]
    defense_path = root / registry.require("Trial order defense").actual_paths[0]
    utility_path = root / registry.require("Trial order utility").actual_paths[0]
    manifest_path = root / registry.require("Phase 5 execution manifest").actual_paths[0]
    expected_core_rows = queue_stats.get("trial_order_core_rows")

    core_check, core_metrics = _verify_queue_file(
        core_path,
        registry.require("Trial order core").sha256[0],
        expected_row_count=expected_core_rows if isinstance(expected_core_rows, int) else None,
    )
    checks.append(core_check)
    findings.extend(_findings_for_check(core_check))
    consumed.append(("Trial order core", core_metrics.get("sha256", "")))

    expected_defense_rows = queue_stats.get("trial_order_defense_rows")
    defense_check, defense_metrics = _verify_queue_file(
        defense_path,
        registry.require("Trial order defense").sha256[0],
        expected_row_count=expected_defense_rows if isinstance(expected_defense_rows, int) else None,
    )

    expected_utility_rows = queue_stats.get("trial_order_utility_rows")
    utility_check, utility_metrics = _verify_queue_file(
        utility_path,
        registry.require("Trial order utility").sha256[0],
        expected_row_count=expected_utility_rows if isinstance(expected_utility_rows, int) else None,
    )
    checks.extend([defense_check, utility_check])
    findings.extend(_findings_for_check(defense_check))
    findings.extend(_findings_for_check(utility_check))

    manifest = _load_json(manifest_path)
    manifest_hashes = manifest.get("hashes", {})
    manifest_metrics = manifest.get("metrics", {})
    if not isinstance(manifest_hashes, dict) or not isinstance(manifest_metrics, dict):
        check = _check_result("execution-manifest", False, "manifest missing hashes or metrics")
    else:
        check = _check_result(
            "execution-manifest",
            manifest_hashes.get("trial_order_core_sha256") == registry.require("Trial order core").sha256[0]
            and manifest_hashes.get("trial_order_defense_sha256") == registry.require("Trial order defense").sha256[0]
            and manifest_hashes.get("trial_order_utility_sha256") == registry.require("Trial order utility").sha256[0]
            and manifest_hashes.get("phase4_corrected_lock_hash") == registry.require("Cryptographic lock manifest").sha256[0]
            and manifest_metrics.get("expected_trial_count") == queue_stats.get("phase5_manifest_expected_trial_count")
            and manifest_metrics.get("expected_payload_count") == queue_stats.get("phase5_manifest_expected_payload_count"),
            f"trial_order_core_sha256={manifest_hashes.get('trial_order_core_sha256')!r}",
            f"trial_order_defense_sha256={manifest_hashes.get('trial_order_defense_sha256')!r}",
            f"trial_order_utility_sha256={manifest_hashes.get('trial_order_utility_sha256')!r}",
            f"phase4_corrected_lock_hash={manifest_hashes.get('phase4_corrected_lock_hash')!r}",
            f"expected_trial_count={manifest_metrics.get('expected_trial_count')!r}",
            f"expected_payload_count={manifest_metrics.get('expected_payload_count')!r}",
        )
    checks.append(check)
    findings.extend(_findings_for_check(check))

    total_rows = sum(
        int(metrics.get("row_count", 0)) for metrics in (core_metrics, defense_metrics, utility_metrics)
    )
    per_model_total: Counter[str] = Counter()
    for metrics in (core_metrics, defense_metrics, utility_metrics):
        counts = metrics.get("counts_by_model", {})
        if isinstance(counts, dict):
            per_model_total.update({str(key): int(value) for key, value in counts.items()})
    total_check = _check_result(
        "corrected-v2-totals",
        total_rows == queue_stats.get("total_rows")
        and dict(sorted(per_model_total.items())) == queue_stats.get("per_model_total"),
        f"total_rows={total_rows}",
        f"per_model_total={dict(sorted(per_model_total.items()))}",
    )
    checks.append(total_check)
    findings.extend(_findings_for_check(total_check))

    expected_unique_trials = queue_stats.get("trial_order_core_unique_trial_ids")
    expected_non_empty = queue_stats.get("trial_order_core_non_empty_cells")
    expected_duplicates = queue_stats.get("trial_order_core_duplicates")
    expected_by_model = queue_stats.get("trial_order_core_by_model")
    expected_by_density = queue_stats.get("trial_order_core_by_density")
    expected_by_defense = queue_stats.get("trial_order_core_by_defense_condition")
    expected_payload_ids = queue_stats.get("unique_payload_ids_used_in_core")
    expected_manifest_trials = queue_stats.get("phase5_manifest_expected_trial_count")
    expected_manifest_payloads = queue_stats.get("phase5_manifest_expected_payload_count")

    core_rows = list(csv.reader(core_path.read_text(encoding="utf-8").splitlines()))[1:]
    computed = {
        "rows": len(core_rows),
        "unique_trial_ids": len({row[0] for row in core_rows}),
        "non_empty_cells": sum(1 for row in core_rows for cell in row if cell != ""),
        "duplicates": sorted(trial_id for trial_id, count in Counter(row[0] for row in core_rows).items() if count > 1),
        "by_model": dict(sorted(Counter(row[1] for row in core_rows).items())),
        "by_density": dict(sorted(Counter(row[2] for row in core_rows).items())),
        "by_defense": dict(sorted(Counter(row[5] for row in core_rows).items())),
        "unique_payload_ids": len({row[6] for row in core_rows if row[6]}),
    }
    ok = (
        computed["rows"] == expected_core_rows
        and computed["unique_trial_ids"] == expected_unique_trials
        and computed["non_empty_cells"] == expected_non_empty
        and computed["duplicates"] == list(expected_duplicates or [])
        and computed["by_model"] == dict(sorted((expected_by_model or {}).items()))
        and computed["by_density"] == dict(sorted((expected_by_density or {}).items()))
        and computed["by_defense"] == dict(sorted((expected_by_defense or {}).items()))
        and computed["unique_payload_ids"] == expected_payload_ids
        and expected_manifest_trials == manifest_metrics.get("expected_trial_count")
        and expected_manifest_payloads == manifest_metrics.get("expected_payload_count")
    )
    check = _check_result(
        "queue-statistics",
        ok,
        f"computed={computed}",
        f"expected_rows={expected_core_rows!r}",
        f"expected_unique_trials={expected_unique_trials!r}",
        f"expected_non_empty_cells={expected_non_empty!r}",
    )
    checks.append(check)
    findings.extend(_findings_for_check(check))

    consumed.append(("Trial order core", registry.require("Trial order core").sha256[0]))
    consumed.append(("Trial order defense", registry.require("Trial order defense").sha256[0]))
    consumed.append(("Trial order utility", registry.require("Trial order utility").sha256[0]))
    consumed.append(("Phase 5 execution manifest", registry.require("Phase 5 execution manifest").sha256[0]))
    return checks, findings, tuple(consumed)


def _verify_required_artifact_presence(registry) -> tuple[list[Gate0Check], list[str], tuple[tuple[str, str, str], ...]]:
    artifacts: list[tuple[str, str, str]] = []
    checks: list[Gate0Check] = []
    findings: list[str] = []
    for label in (*_PHASE4_REQUIRED_LABELS, *_EVIDENCE_LABELS, *_QUEUE_LABELS, *_MODEL_LABELS):
        try:
            entry = registry.require(label)
        except Phase5Error as exc:
            check = _check_result(f"required-label:{label}", False, str(exc))
            checks.append(check)
            findings.extend(_findings_for_check(check))
            continue
        artifacts.append(_record_artifact(label, entry))
        checks.append(_check_result(f"required-label:{label}", True, entry.actual_paths[0].as_posix(), entry.sha256[0]))
    return checks, findings, tuple(artifacts)


_PHASE4_REQUIRED_LABELS = (
    _PHASE4_GO_LABEL,
    "Phase 4 global freeze",
    "Model freeze set",
    "Model freeze M1",
    "Model freeze M2",
    "Model freeze M3",
    "Model freeze M4",
    "Defense freeze",
    "Statistical plan",
    "Phase 5 schema freeze",
    "Payload reference map",
    "Cryptographic lock manifest",
    "Master hash ledger",
)


def _verify_checkout(strict: bool, root: Path, source_clean: bool | None) -> Gate0Check:
    if not strict:
        return _check_result("checkout-clean", True, "strict mode disabled")
    if source_clean is None:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=root,
                capture_output=True,
                text=True,
                check=False,
            )
        except Exception as exc:  # pragma: no cover - defensive
            return _check_result("checkout-clean", False, f"unable to determine git status: {exc}")
        source_clean = result.returncode == 0 and not result.stdout.strip()
    return _check_result(
        "checkout-clean",
        bool(source_clean),
        "working tree clean" if source_clean else "working tree is dirty",
    )


def _merge_findings(*groups: Iterable[str]) -> tuple[str, ...]:
    findings: list[str] = []
    for group in groups:
        findings.extend(group)
    return tuple(findings)


def run_gate0(
    *,
    strict: bool,
    report_dir: Path | None = None,
    root: Path | None = None,
    source_clean: bool | None = None,
) -> Gate0Report:
    repository_root = (root or repo_root()).resolve()
    generated_utc = datetime.now(tz=timezone.utc).isoformat().replace("+00:00", "Z")

    registry = None
    registry_doc: dict[str, object] = {}
    checks: list[Gate0Check] = []
    findings: list[str] = []
    verified_artifacts: list[tuple[str, str, str]] = []
    consumed_frozen_inputs: list[tuple[str, str]] = []
    verdicts: list[tuple[str, str]] = []

    try:
        registry, registry_doc, registry_checks, registry_findings = _verify_registry(repository_root)
        checks.extend(registry_checks)
        findings.extend(registry_findings)
    except Phase5Error as exc:
        checks.append(_check_result("registry-load", False, str(exc)))
        findings.append(f"registry-load: {exc}")
        summary = "Gate 0 failed before registry initialization."
        report = Gate0Report(
            task_id="P03",
            status="FAIL",
            strict=strict,
            generated_utc=generated_utc,
            repository_root=repository_root.as_posix(),
            summary=summary,
            findings=tuple(findings),
            checks=tuple(checks),
            verified_artifacts=tuple(verified_artifacts),
            consumed_frozen_inputs=tuple(consumed_frozen_inputs),
            verdicts=tuple(verdicts),
        )
        if report_dir is not None:
            report.write(report_dir)
        return report

    phase4_path = repository_root / registry.require(_PHASE4_GO_LABEL).actual_paths[0]
    phase45_path = repository_root / registry.require(_PHASE45_GO_LABEL).actual_paths[0]
    phase4_check = _parse_phase4_go_report(phase4_path)
    phase45_check = _parse_phase45_go_report(phase45_path)
    checks.extend([phase4_check, phase45_check])
    findings.extend(_merge_findings(_findings_for_check(phase4_check), _findings_for_check(phase45_check)))
    verdicts.extend(
        [
            ("phase4", "PASS" if phase4_check.status == "PASS" else "FAIL"),
            ("phase4_5", "GO TO PHASE 5 REBINDING" if phase45_check.status == "PASS" else "FAIL"),
        ]
    )

    artifact_checks, artifact_findings, artifacts = _verify_required_artifact_presence(registry)
    checks.extend(artifact_checks)
    findings.extend(artifact_findings)
    verified_artifacts.extend(artifacts)

    queue_checks, queue_findings, queue_consumed = _verify_queue_statistics(repository_root, registry, registry_doc)
    checks.extend(queue_checks)
    findings.extend(queue_findings)
    consumed_frozen_inputs.extend(queue_consumed)

    model_checks, model_findings, model_consumed = _verify_model_frozen_files(repository_root, registry_doc)
    checks.extend(model_checks)
    findings.extend(model_findings)
    consumed_frozen_inputs.extend(model_consumed)

    runtime_checks, runtime_findings, runtime_consumed, runtime_commit = _verify_runtime_contract(repository_root)
    checks.extend(runtime_checks)
    findings.extend(runtime_findings)
    consumed_frozen_inputs.extend(runtime_consumed)

    checkout_check = _verify_checkout(strict, repository_root, source_clean)
    checks.append(checkout_check)
    findings.extend(_findings_for_check(checkout_check))

    if runtime_commit:
        verdicts.append(("phase4_5_source_commit", runtime_commit))

    status = "PASS" if not findings and all(check.status == "PASS" for check in checks) else "FAIL"
    summary = (
        "Gate 0 passed with strict, hash-bound verification of the registry, frozen artifacts, queue files, "
        "model/runtime evidence, and checkout cleanliness."
        if status == "PASS"
        else "Gate 0 failed because one or more frozen artifacts, verdicts, runtime controls, or checkout checks did not match."
    )
    report = Gate0Report(
        task_id="P03",
        status=status,
        strict=strict,
        generated_utc=generated_utc,
        repository_root=repository_root.as_posix(),
        summary=summary,
        findings=tuple(findings),
        checks=tuple(checks),
        verified_artifacts=tuple(verified_artifacts),
        consumed_frozen_inputs=tuple(consumed_frozen_inputs),
        verdicts=tuple(verdicts),
    )
    if report_dir is not None:
        report.write(report_dir)
    return report
