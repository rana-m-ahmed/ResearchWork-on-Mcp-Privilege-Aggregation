"""Operational Kaggle run planning for Phase 5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import math
import statistics
from typing import Mapping, Sequence

try:  # pragma: no cover - optional dependency is validated in tests
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from ..guards import repo_root
from ..queues.batch_partitioner import (
    DEFAULT_BATCH_SIZE,
    BatchPartitionManifest,
    build_default_batch_partition_manifest,
)


MODEL_SLOTS = ("M1", "M2", "M3", "M4")
WORKLOAD_COUNTS = {
    "phase5_adversarial_core": 1350,
    "phase5_adversarial_defense": 600,
    "phase5_utility_preservation": 600,
}
DEFAULT_SAFE_SESSION_HOURS = 7.5
DEFAULT_TIMING_REPORT = Path("phase4_5/validation/phase45_kaggle_quota_feasibility_report.md")
DEFAULT_BATCH_MANIFEST = Path("phase5/manifests/batch_partition_manifest_v3.json")
DEFAULT_RUN_PLAN_JSON = Path("phase5/validation/kaggle_run_plan_v3.json")
DEFAULT_M4_RECONCILIATION = Path("phase5/validation/m4_loader_status_reconciliation.json")
DEFAULT_MODEL_LOADER_OUTPUTS = Path("phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_outputs.jsonl")
DEFAULT_MODEL_LOADER_TRIALS = Path("phase4_5/dryrun_results/kaggle_model_loader_smoke/model_loader_trials.jsonl")
DEFAULT_KAGGLE_SMOKE_METRICS = Path("phase4_5/dryrun_results/kaggle_smoke/hardware_metrics.jsonl")
DEFAULT_KAGGLE_SMOKE_INVALIDS = Path("phase4_5/dryrun_results/kaggle_smoke/invalid_trials.jsonl")
DEFAULT_KAGGLE_SMOKE_FAILURES = Path("phase4_5/dryrun_results/kaggle_smoke/failures.jsonl")
DEFAULT_CHECKPOINT_RESUME = Path("phase4_5/configs/phase45_checkpoint_resume.yaml")
FROZEN_TIMING_EVIDENCE_GENERATED_UTC = "2026-07-05T12:56:48.678168Z"
I17R_DATASET_VERSION = "P5-DV-1.0.2-A7C91E42"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_frozen_path(path: Path, *, repository_root: Path) -> str:
    """Hash frozen textual evidence independently of checkout newline style."""
    data = path.read_bytes()
    if path.suffix.lower() not in {".md", ".json", ".jsonl", ".yaml", ".yml", ".txt"}:
        return _sha256_bytes(data)
    canonical = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    return _sha256_bytes(canonical)


def _load_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        raise MissingFrozenSettingError(f"required frozen JSONL file is missing: {path.as_posix()}")
    rows: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise SchemaInvariantError(f"JSONL row must be a JSON object: {path.as_posix()}")
        rows.append(data)
    return rows


def _load_yaml(path: Path) -> Mapping[str, object]:
    if yaml is None:
        raise SchemaInvariantError("pyyaml is required to load the checkpoint/resume configuration")
    if not path.is_file():
        raise MissingFrozenSettingError(f"required frozen YAML file is missing: {path.as_posix()}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError(f"{path.as_posix()} must contain a YAML mapping")
    return data


def _write_if_unchanged(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        existing = path.read_text(encoding="utf-8-sig")
        if existing.lstrip("\ufeff") != content.lstrip("\ufeff"):
            raise FrozenArtifactHashError(f"immutable report refusal for {path.as_posix()}")
        return
    path.write_text(content, encoding="utf-8")


def _exclusive_p95(values: Sequence[float]) -> float:
    if not values:
        raise SchemaInvariantError("timing evidence must contain at least one sample")
    if len(values) == 1:
        return float(values[0])
    return float(statistics.quantiles(values, n=20, method="exclusive")[18])


def _rounded(value: float) -> float:
    return round(float(value), 2)


def _require_positive(value: float, label: str) -> float:
    if value <= 0:
        raise SchemaInvariantError(f"{label} must be positive")
    return value


def _parse_report_number(pattern: str, text: str) -> float:
    import re

    match = re.search(pattern, text)
    if match is None:
        raise SchemaInvariantError(f"timing report is missing required pattern: {pattern}")
    return float(match.group(1).replace(",", ""))


def _load_report_text(path: Path) -> str:
    if not path.is_file():
        raise MissingFrozenSettingError(f"timing report is missing: {path.as_posix()}")
    return path.read_text(encoding="utf-8")


@dataclass(frozen=True, slots=True)
class TimingEvidence:
    timing_report_path: Path
    timing_report_sha256: str
    evidence_generated_utc: str
    mean_trial_seconds: float
    p50_trial_seconds: float
    p95_trial_seconds: float
    trial_sample_count: int
    invalid_attempt_rate: float
    safe_session_hours: float
    checkpoint_frequency_trials: int
    model_load_seconds: tuple[tuple[str, float], ...]
    model_load_status: tuple[tuple[str, str], ...]
    evidence_inputs: tuple[tuple[str, str], ...]

    @property
    def model_load_map(self) -> dict[str, float]:
        return dict(self.model_load_seconds)

    @property
    def model_load_status_map(self) -> dict[str, str]:
        return dict(self.model_load_status)

    def to_dict(self) -> dict[str, object]:
        return {
            "checkpoint_frequency_trials": self.checkpoint_frequency_trials,
            "evidence_inputs": [{"label": label, "sha256": sha256} for label, sha256 in self.evidence_inputs],
            "evidence_generated_utc": self.evidence_generated_utc,
            "invalid_attempt_rate": self.invalid_attempt_rate,
            "mean_trial_seconds": self.mean_trial_seconds,
            "model_load_seconds": [
                {"model_slot": model_slot, "seconds": seconds} for model_slot, seconds in self.model_load_seconds
            ],
            "model_load_status": [
                {"model_slot": model_slot, "status": status} for model_slot, status in self.model_load_status
            ],
            "p50_trial_seconds": self.p50_trial_seconds,
            "p95_trial_seconds": self.p95_trial_seconds,
            "safe_session_hours": self.safe_session_hours,
            "timing_report_path": self.timing_report_path.as_posix(),
            "timing_report_sha256": self.timing_report_sha256,
            "trial_sample_count": self.trial_sample_count,
        }


@dataclass(frozen=True, slots=True)
class ModelRunPlan:
    model_slot: str
    accepted_targets: int
    workload_counts: tuple[tuple[str, int], ...]
    workload_batches: tuple[tuple[str, int], ...]
    total_batches: int
    batches_per_session: int
    projected_session_hours: float
    projected_sessions: int
    projected_gpu_hours: float
    invalid_attempt_rate: float
    p50_trial_seconds: float
    p95_trial_seconds: float
    load_overhead_seconds: float
    model_load_status: str
    note: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "accepted_targets": self.accepted_targets,
            "batches_per_session": self.batches_per_session,
            "invalid_attempt_rate": self.invalid_attempt_rate,
            "load_overhead_seconds": self.load_overhead_seconds,
            "model_load_status": self.model_load_status,
            "model_slot": self.model_slot,
            "note": self.note,
            "p50_trial_seconds": self.p50_trial_seconds,
            "p95_trial_seconds": self.p95_trial_seconds,
            "projected_gpu_hours": self.projected_gpu_hours,
            "projected_session_hours": self.projected_session_hours,
            "projected_sessions": self.projected_sessions,
            "total_batches": self.total_batches,
            "workload_batches": [
                {"batch_count": batch_count, "workload": workload} for workload, batch_count in self.workload_batches
            ],
            "workload_counts": [
                {"target_count": target_count, "workload": workload} for workload, target_count in self.workload_counts
            ],
        }


@dataclass(frozen=True, slots=True)
class KaggleRunPlan:
    task_id: str
    status: str
    generated_utc: str
    dataset_version: str
    safe_session_hours: float
    safe_session_seconds: float
    total_targets: int
    total_batches: int
    projected_total_sessions: int
    projected_total_gpu_hours: float
    checkpoint_barrier_interval_trials: int
    timing_evidence: TimingEvidence
    model_plans: tuple[ModelRunPlan, ...]
    sensitivity_scenarios: tuple[tuple[float, float, int, int], ...]
    batch_manifest_path: Path
    batch_manifest_sha256: str
    source_evidence: tuple[tuple[str, str], ...]
    findings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "batch_manifest_path": self.batch_manifest_path.as_posix(),
            "batch_manifest_sha256": self.batch_manifest_sha256,
            "checkpoint_barrier_interval_trials": self.checkpoint_barrier_interval_trials,
            "dataset_version": self.dataset_version,
            "findings": list(self.findings),
            "generated_utc": self.generated_utc,
            "model_plans": [plan.to_dict() for plan in self.model_plans],
            "projected_total_gpu_hours": self.projected_total_gpu_hours,
            "projected_total_sessions": self.projected_total_sessions,
            "safe_session_hours": self.safe_session_hours,
            "safe_session_seconds": self.safe_session_seconds,
            "sensitivity_scenarios": [
                {
                    "effective_seconds_per_trial": effective_seconds,
                    "approx_hours_per_model": approx_hours,
                    "sessions_per_model": sessions_per_model,
                    "total_sessions": total_sessions,
                }
                for effective_seconds, approx_hours, sessions_per_model, total_sessions in self.sensitivity_scenarios
            ],
            "source_evidence": [
                {"label": label, "sha256": sha256} for label, sha256 in self.source_evidence
            ],
            "status": self.status,
            "task_id": self.task_id,
            "timing_evidence": self.timing_evidence.to_dict(),
            "total_batches": self.total_batches,
            "total_targets": self.total_targets,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P05 Kaggle Run Plan",
            "",
            "## Verdict",
            "",
            f"- Task: `{self.task_id}`",
            f"- Status: `{self.status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            f"- Dataset version: `{self.dataset_version}`",
            f"- Safe session hours: `{self.safe_session_hours:.2f}`",
            f"- Safe session seconds: `{self.safe_session_seconds:.0f}`",
            f"- Total targets: `{self.total_targets}`",
            f"- Total batches: `{self.total_batches}`",
            f"- Projected total sessions: `{self.projected_total_sessions}`",
            f"- Projected total GPU hours: `{self.projected_total_gpu_hours:.2f}`",
            f"- Checkpoint barrier interval: `{self.checkpoint_barrier_interval_trials}` trials",
            "",
            "## Timing Evidence",
            f"- Timing report: `{self.timing_evidence.timing_report_path.as_posix()}`",
            f"- Mean trial seconds: `{self.timing_evidence.mean_trial_seconds:.2f}`",
            f"- P50 trial seconds: `{self.timing_evidence.p50_trial_seconds:.2f}`",
            f"- P95 trial seconds: `{self.timing_evidence.p95_trial_seconds:.2f}`",
            f"- Invalid attempt rate: `{self.timing_evidence.invalid_attempt_rate:.4f}`",
            "",
            "## Model Plans",
        ]
        for plan in self.model_plans:
            lines.extend(
                [
                    f"- `{plan.model_slot}`: targets={plan.accepted_targets}, batches={plan.total_batches}, "
                    f"sessions={plan.projected_sessions}, load={plan.load_overhead_seconds:.2f}s, "
                    f"status={plan.model_load_status}",
                ]
            )
            for workload, target_count in plan.workload_counts:
                lines.append(f"  - {workload}: `{target_count}`")
        lines.extend(["", "## Sensitivity Scenarios"])
        for effective_seconds, approx_hours, sessions_per_model, total_sessions in self.sensitivity_scenarios:
            lines.append(
                f"- `{effective_seconds:.0f}`s/trial -> `{approx_hours:.2f}` h/model, "
                f"`{sessions_per_model}` sessions/model, `{total_sessions}` total sessions"
            )
        lines.extend(["", "## Source Evidence"])
        for label, sha256 in self.source_evidence:
            lines.append(f"- {label}: `{sha256}`")
        lines.extend(["", "## Findings"])
        if self.findings:
            lines.extend(f"- {item}" for item in self.findings)
        else:
            lines.append("- none")
        lines.extend(["", "## Batch Manifest", f"- `{self.batch_manifest_path.as_posix()}`", f"- `{self.batch_manifest_sha256}`"])
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        _write_if_unchanged(json_path, self.to_json() + "\n")
        if markdown_path is not None:
            _write_if_unchanged(markdown_path, self.to_markdown())


def _parse_timing_report(path: Path) -> tuple[float, float, float]:
    text = _load_report_text(path)
    mean = _parse_report_number(r"Mean trial inference time:\s*`([0-9.]+)s`", text)
    p95 = _parse_report_number(r"P95 trial inference time:\s*`([0-9.]+)s`", text)
    core_trials = _parse_report_number(r"Estimated total core trials:\s*`([0-9,]+)`", text)
    if core_trials != 5400:
        raise SchemaInvariantError("timing report does not preserve the frozen core trial count")
    return mean, p95, core_trials


def _load_smoke_times(path: Path) -> list[float]:
    rows = _load_jsonl(path)
    values: list[float] = []
    for row in rows:
        value = row.get("inference_time_seconds")
        if not isinstance(value, (int, float)):
            raise SchemaInvariantError(f"missing inference_time_seconds in {path.as_posix()}")
        values.append(float(value))
    if not values:
        raise MissingFrozenSettingError(f"timing metrics are missing from {path.as_posix()}")
    return values


def _load_model_loader_outputs(path: Path) -> dict[str, float]:
    rows = _load_jsonl(path)
    values: dict[str, float] = {}
    for row in rows:
        model_slot = row.get("model_slot")
        load_time = row.get("load_time_seconds")
        if not isinstance(model_slot, str) or not model_slot:
            raise SchemaInvariantError(f"model_loader_outputs row missing model_slot: {path.as_posix()}")
        if not isinstance(load_time, (int, float)):
            raise SchemaInvariantError(f"model_loader_outputs row missing load_time_seconds: {path.as_posix()}")
        if model_slot in values:
            raise SchemaInvariantError(f"duplicate model loader output for {model_slot!r}")
        values[model_slot] = float(load_time)
    missing = [model for model in MODEL_SLOTS if model not in values]
    if missing:
        raise MissingFrozenSettingError(f"model loader outputs missing required models: {missing}")
    return values


def _load_model_loader_status(path: Path) -> dict[str, str]:
    rows = _load_jsonl(path)
    values: dict[str, str] = {}
    for row in rows:
        model_slot = row.get("model_slot")
        status = row.get("status")
        if not isinstance(model_slot, str) or not model_slot:
            raise SchemaInvariantError(f"model_loader_trials row missing model_slot: {path.as_posix()}")
        if not isinstance(status, str) or not status:
            raise SchemaInvariantError(f"model_loader_trials row missing status: {path.as_posix()}")
        if model_slot in values:
            raise SchemaInvariantError(f"duplicate model loader trial for {model_slot!r}")
        values[model_slot] = status
    missing = [model for model in MODEL_SLOTS if model not in values]
    if missing:
        raise MissingFrozenSettingError(f"model loader trials missing required models: {missing}")
    return values


def _apply_m4_reconciliation(repository_root: Path, load_status: dict[str, str]) -> tuple[dict[str, str], tuple[str, str] | None]:
    path = repository_root / DEFAULT_M4_RECONCILIATION
    if not path.is_file():
        return load_status, None
    data = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "model_slot": "M4",
        "model_id": "microsoft/Phi-3.5-mini-instruct",
        "prior_status": "LOAD_FAILURE",
        "final_non_official_kaggle_status": "PASS",
        "active_official_run_plan_status": "LOAD_SUCCESS",
        "official_trials_executed": 0,
    }
    for key, expected in required.items():
        if data.get(key) != expected:
            raise FrozenArtifactHashError(f"M4 reconciliation field mismatch for {key}: expected {expected!r}")
    if load_status.get("M4") != "LOAD_FAILURE":
        raise FrozenArtifactHashError("M4 reconciliation expected the historical loader status to be LOAD_FAILURE")
    reconciled = dict(load_status)
    reconciled["M4"] = "LOAD_SUCCESS"
    return reconciled, ("M4 loader status reconciliation", _sha256_frozen_path(path, repository_root=repository_root))


def _load_invalid_rate(invalids_path: Path, failures_path: Path, total_trials: int) -> float:
    invalid_count = len(_load_jsonl(invalids_path))
    failure_count = len(_load_jsonl(failures_path))
    if failure_count and invalid_count == 0:
        raise SchemaInvariantError("failure evidence exists without invalid trial records")
    if total_trials <= 0:
        raise SchemaInvariantError("timing sample count must be positive")
    total_attempts = total_trials + invalid_count + failure_count
    if total_attempts <= 0:
        raise SchemaInvariantError("invalid-attempt rate cannot be computed from empty evidence")
    return (invalid_count + failure_count) / float(total_attempts)


def _load_checkpoint_frequency(path: Path) -> int:
    data = _load_yaml(path)
    value = data.get("checkpoint_frequency_trials")
    if not isinstance(value, int) or value <= 0:
        raise SchemaInvariantError("checkpoint_frequency_trials must be a positive integer")
    return value


def load_timing_evidence(
    *,
    root: Path | None = None,
    timing_report_path: Path | None = None,
    safe_session_hours: float | None = None,
) -> TimingEvidence:
    repository_root = (root or repo_root()).resolve()
    timing_report = (timing_report_path or (repository_root / DEFAULT_TIMING_REPORT)).resolve()
    smoke_metrics = repository_root / DEFAULT_KAGGLE_SMOKE_METRICS
    invalid_trials = repository_root / DEFAULT_KAGGLE_SMOKE_INVALIDS
    failures = repository_root / DEFAULT_KAGGLE_SMOKE_FAILURES
    model_loader_outputs = repository_root / DEFAULT_MODEL_LOADER_OUTPUTS
    model_loader_trials = repository_root / DEFAULT_MODEL_LOADER_TRIALS
    checkpoint_resume = repository_root / DEFAULT_CHECKPOINT_RESUME

    report_mean, report_p95, _core_trials = _parse_timing_report(timing_report)
    smoke_values = _load_smoke_times(smoke_metrics)
    sample_count = len(smoke_values)
    computed_mean = statistics.mean(smoke_values)
    computed_p50 = statistics.median(smoke_values)
    computed_p95 = _exclusive_p95(smoke_values)
    _require_positive(float(computed_mean), "trial mean seconds")
    _require_positive(float(computed_p50), "trial p50 seconds")
    _require_positive(float(computed_p95), "trial p95 seconds")
    if round(computed_mean, 2) != round(report_mean, 2) or round(computed_p95, 2) != round(report_p95, 2):
        raise FrozenArtifactHashError(
            "timing report values do not reconcile with the smoke metrics evidence"
        )

    load_seconds = _load_model_loader_outputs(model_loader_outputs)
    load_status = _load_model_loader_status(model_loader_trials)
    load_status, reconciliation_evidence = _apply_m4_reconciliation(repository_root, load_status)
    invalid_rate = _load_invalid_rate(invalid_trials, failures, sample_count)
    if invalid_rate < 0 or invalid_rate >= 1:
        raise SchemaInvariantError("invalid-attempt rate must be in the range [0, 1)")
    checkpoint_frequency = _load_checkpoint_frequency(checkpoint_resume)
    safe_session_hours = safe_session_hours if safe_session_hours is not None else DEFAULT_SAFE_SESSION_HOURS
    _require_positive(float(safe_session_hours), "safe_session_hours")

    evidence_inputs = (
        ("Timing report", _sha256_frozen_path(timing_report, repository_root=repository_root)),
        ("Kaggle smoke metrics", _sha256_frozen_path(smoke_metrics, repository_root=repository_root)),
        ("Model-loader outputs", _sha256_frozen_path(model_loader_outputs, repository_root=repository_root)),
        ("Model-loader trials", _sha256_frozen_path(model_loader_trials, repository_root=repository_root)),
        ("Invalid trials", _sha256_frozen_path(invalid_trials, repository_root=repository_root)),
        ("Failures", _sha256_frozen_path(failures, repository_root=repository_root)),
        ("Checkpoint/resume config", _sha256_frozen_path(checkpoint_resume, repository_root=repository_root)),
    )
    if reconciliation_evidence is not None:
        evidence_inputs = (*evidence_inputs, reconciliation_evidence)
    return TimingEvidence(
        timing_report_path=timing_report,
        timing_report_sha256=_sha256_frozen_path(timing_report, repository_root=repository_root),
        evidence_generated_utc=FROZEN_TIMING_EVIDENCE_GENERATED_UTC,
        mean_trial_seconds=_rounded(computed_mean),
        p50_trial_seconds=_rounded(computed_p50),
        p95_trial_seconds=_rounded(computed_p95),
        trial_sample_count=sample_count,
        invalid_attempt_rate=_rounded(invalid_rate),
        safe_session_hours=float(safe_session_hours),
        checkpoint_frequency_trials=checkpoint_frequency,
        model_load_seconds=tuple(sorted(load_seconds.items())),
        model_load_status=tuple(sorted(load_status.items())),
        evidence_inputs=evidence_inputs,
    )


def _batch_duration_seconds(timing: TimingEvidence, batch_size: int) -> float:
    if batch_size <= 0:
        raise SchemaInvariantError("batch size must be positive")
    if timing.p95_trial_seconds <= 0:
        raise SchemaInvariantError("trial p95 seconds must be positive")
    if timing.invalid_attempt_rate < 0 or timing.invalid_attempt_rate >= 1:
        raise SchemaInvariantError("invalid-attempt rate must be in the range [0, 1)")
    effective_trial_seconds = timing.p95_trial_seconds / (1.0 - timing.invalid_attempt_rate)
    return batch_size * effective_trial_seconds


def _model_projected_seconds(timing: TimingEvidence, model_slot: str, batch_size: int = DEFAULT_BATCH_SIZE) -> float:
    if timing.p95_trial_seconds <= 0:
        raise SchemaInvariantError("trial p95 seconds must be positive")
    if timing.invalid_attempt_rate < 0 or timing.invalid_attempt_rate >= 1:
        raise SchemaInvariantError("invalid-attempt rate must be in the range [0, 1)")
    workload_total = sum(WORKLOAD_COUNTS.values())
    return workload_total * (timing.p95_trial_seconds / (1.0 - timing.invalid_attempt_rate)) + timing.model_load_map[model_slot]


def _batches_per_session(timing: TimingEvidence, model_slot: str, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    batch_duration = _batch_duration_seconds(timing, batch_size)
    safe_session_seconds = timing.safe_session_hours * 3600.0
    available_seconds = safe_session_seconds - timing.model_load_map[model_slot]
    if available_seconds <= 0:
        raise SchemaInvariantError("safe session window is smaller than the model load overhead")
    batches = math.floor(available_seconds / batch_duration)
    if batches <= 0:
        raise SchemaInvariantError("safe session window is too small to fit a single batch")
    return min(batches, sum(WORKLOAD_COUNTS[w] // batch_size for w in WORKLOAD_COUNTS))


def _sensitivity_scenarios(safe_session_hours: float) -> tuple[tuple[float, float, int, int], ...]:
    scenarios = []
    for effective_seconds in (5.0, 8.0, 10.0, 12.0, 20.0, 30.0, 60.0):
        approx_hours = (2550 * effective_seconds) / 3600.0
        sessions_per_model = math.ceil(approx_hours / safe_session_hours)
        total_sessions = sessions_per_model * len(MODEL_SLOTS)
        scenarios.append((effective_seconds, round(approx_hours, 2), sessions_per_model, total_sessions))
    return tuple(scenarios)


def _build_model_plans(timing: TimingEvidence) -> tuple[ModelRunPlan, ...]:
    plans: list[ModelRunPlan] = []
    workload_batches = tuple((workload, target_count // DEFAULT_BATCH_SIZE) for workload, target_count in WORKLOAD_COUNTS.items())
    workload_counts = tuple(WORKLOAD_COUNTS.items())
    total_batches = sum(batch_count for _, batch_count in workload_batches)
    for model_slot in MODEL_SLOTS:
        projected_seconds = _model_projected_seconds(timing, model_slot)
        projected_sessions = math.ceil(projected_seconds / (timing.safe_session_hours * 3600.0))
        projected_hours = projected_seconds / 3600.0
        plans.append(
            ModelRunPlan(
                model_slot=model_slot,
                accepted_targets=sum(WORKLOAD_COUNTS.values()),
                workload_counts=workload_counts,
                workload_batches=workload_batches,
                total_batches=total_batches,
                batches_per_session=_batches_per_session(timing, model_slot),
                projected_session_hours=round(projected_hours, 2),
                projected_sessions=projected_sessions,
                projected_gpu_hours=round(projected_hours, 2),
                invalid_attempt_rate=timing.invalid_attempt_rate,
                p50_trial_seconds=timing.p50_trial_seconds,
                p95_trial_seconds=timing.p95_trial_seconds,
                load_overhead_seconds=timing.model_load_map[model_slot],
                model_load_status=timing.model_load_status_map[model_slot],
                note="Operational estimate only; planning does not use outcome fields.",
            )
        )
    return tuple(plans)


def build_kaggle_run_plan(
    *,
    timing_evidence: TimingEvidence,
    batch_manifest: BatchPartitionManifest,
) -> KaggleRunPlan:
    projected_total_sessions = sum(plan.projected_sessions for plan in _build_model_plans(timing_evidence))
    projected_total_gpu_hours = round(
        sum(_model_projected_seconds(timing_evidence, model_slot) for model_slot in MODEL_SLOTS) / 3600.0,
        2,
    )
    findings: list[str] = []
    for model_slot, status in timing_evidence.model_load_status_map.items():
        if not status.startswith("LOAD_SUCCESS"):
            findings.append(f"{model_slot} loader smoke status={status}")
    return KaggleRunPlan(
        task_id="P05",
        status="PASS",
        generated_utc=timing_evidence.evidence_generated_utc,
        dataset_version=batch_manifest.dataset_version,
        safe_session_hours=timing_evidence.safe_session_hours,
        safe_session_seconds=timing_evidence.safe_session_hours * 3600.0,
        total_targets=batch_manifest.total_targets,
        total_batches=batch_manifest.total_batches,
        projected_total_sessions=projected_total_sessions,
        projected_total_gpu_hours=projected_total_gpu_hours,
        checkpoint_barrier_interval_trials=timing_evidence.checkpoint_frequency_trials,
        timing_evidence=timing_evidence,
        model_plans=_build_model_plans(timing_evidence),
        sensitivity_scenarios=_sensitivity_scenarios(timing_evidence.safe_session_hours),
        batch_manifest_path=DEFAULT_BATCH_MANIFEST,
        batch_manifest_sha256=batch_manifest.manifest_sha256,
        source_evidence=timing_evidence.evidence_inputs,
        findings=tuple(findings),
    )


def plan_kaggle_runs(
    *,
    root: Path | None = None,
    timing_report_path: Path | None = None,
    safe_session_hours: float | None = None,
    output_path: Path | None = None,
) -> KaggleRunPlan:
    repository_root = (root or repo_root()).resolve()
    timing_evidence = load_timing_evidence(
        root=repository_root,
        timing_report_path=timing_report_path,
        safe_session_hours=safe_session_hours,
    )
    batch_manifest = build_default_batch_partition_manifest(
        batch_size=DEFAULT_BATCH_SIZE,
        dataset_version=I17R_DATASET_VERSION,
        source_evidence=timing_evidence.evidence_inputs,
        generated_utc=timing_evidence.evidence_generated_utc,
    )
    batch_manifest_path = repository_root / DEFAULT_BATCH_MANIFEST
    batch_markdown_path = batch_manifest_path.with_suffix(".md")
    batch_manifest.write(batch_manifest_path, batch_markdown_path)

    plan = build_kaggle_run_plan(timing_evidence=timing_evidence, batch_manifest=batch_manifest)

    output_path = (output_path or (repository_root / DEFAULT_RUN_PLAN_JSON)).resolve()
    markdown_path = output_path.with_suffix(".md")
    plan.write(output_path, markdown_path)
    return plan
