"""Phase 4.5 Kaggle smoke runner scaffold.

The module is intentionally executable later on Kaggle without becoming an
official Phase 5 evaluation harness. It records the repository state, loads the
Phase 4 freeze inputs, validates the schema mapping, prepares smoke matrices,
and writes non-official artifact stubs.
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


try:
    # Attempt to load Hugging Face token from Kaggle Secrets if in Kaggle
    from kaggle_secrets import UserSecretsClient
    user_secrets = UserSecretsClient()
    os.environ["HF_TOKEN"] = user_secrets.get_secret("HF_TOKEN")
except Exception:
    pass

try:
    ROOT = Path(__file__).resolve().parents[1]
except NameError:
    # We are executing inside a Jupyter/Kaggle notebook cell
    kaggle_path = Path("/kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation")
    if kaggle_path.exists():
        os.chdir(kaggle_path)
        ROOT = kaggle_path / "phase4_5"
    else:
        ROOT = Path.cwd() / "phase4_5"

REPO_ROOT = ROOT.parent
CONFIG_DIR = ROOT / "configs"
MATRIX_DIR = ROOT / "matrices"
VALIDATION_DIR = ROOT / "validation"
LOCAL_RESULTS_DIR = ROOT / "dryrun_results" / "local"
KAGGLE_SMOKE_RESULTS_DIR = ROOT / "dryrun_results" / "kaggle_smoke"
KAGGLE_MODEL_RESULTS_DIR = ROOT / "dryrun_results" / "kaggle_model_loader_smoke"
RUN_MANIFEST_DIR = ROOT / "run_manifests"


def read_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a mapping")
    return data


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def current_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def record_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "UNKNOWN_KAGGLE_COMMIT"


def verify_environment_lock() -> dict[str, str]:
    lock = read_yaml(CONFIG_DIR / "phase45_environment_lock.yaml")
    results = {"python_version": lock.get("python_version", "TO_VERIFY_ON_KAGGLE")}
    results["cuda_availability_expected"] = str(lock.get("cuda_availability_expected", "TO_VERIFY_ON_KAGGLE"))
    return results


def load_frozen_phase4_configs() -> dict[str, Any]:
    return {
        "model_set": read_yaml(REPO_ROOT / "phase4" / "configs" / "model_set_freeze.yaml"),
        "payload_reference_map": read_json(REPO_ROOT / "phase4" / "configs" / "payload_reference_map.json"),
        "phase5_schema": read_json(REPO_ROOT / "phase4" / "configs" / "phase5_schema_freeze.json"),
        "statistical_plan": read_yaml(REPO_ROOT / "phase4" / "configs" / "statistical_plan.yaml"),
        "defense_config": read_yaml(REPO_ROOT / "phase4" / "configs" / "defense_config_freeze.yaml"),
        "phase5_manifest": read_json(REPO_ROOT / "phase4" / "frozen_bundle" / "phase5_execution_manifest.json"),
        "lock_manifest": read_json(REPO_ROOT / "phase4" / "frozen_bundle" / "cryptographic_lock_manifest.json"),
        "trial_order_core": (REPO_ROOT / "phase4" / "frozen_bundle" / "trial_order_core.csv").read_text(encoding="utf-8"),
        "trial_order_defense": (REPO_ROOT / "phase4" / "frozen_bundle" / "trial_order_defense.csv").read_text(encoding="utf-8"),
    }


def load_schema_mapping() -> dict[str, Any]:
    return read_yaml(CONFIG_DIR / "phase45_schema_mapping.yaml")


def validate_schema_mapping(schema: dict[str, Any], mapping: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in schema if field not in mapping]
    extras = [field for field in mapping if field not in schema]
    return {"missing": missing, "extras": extras, "valid": not missing and not extras}


def build_or_load_kaggle_smoke_matrix() -> list[dict[str, str]]:
    path = MATRIX_DIR / "phase45_kaggle_smoke_matrix.csv"
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    subprocess.check_call([sys.executable, str(REPO_ROOT / "phase4_5" / "scripts" / "build_phase45_kaggle_matrix.py")], cwd=REPO_ROOT)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def build_or_load_local_matrix() -> list[dict[str, str]]:
    path = MATRIX_DIR / "phase45_local_dryrun_matrix.csv"
    if path.exists():
        with path.open("r", encoding="utf-8", newline="") as handle:
            return list(csv.DictReader(handle))
    subprocess.check_call([sys.executable, str(REPO_ROOT / "phase4_5" / "scripts" / "build_phase45_local_matrix.py")], cwd=REPO_ROOT)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_selected_model() -> dict[str, Any]:
    return read_yaml(CONFIG_DIR / "phase45_selected_model.yaml")


def perform_loader_smoke(frozen_models: dict[str, str]) -> list[dict[str, str]]:
    return [
        {
            "model_slot": slot,
            "exact_model_identifier": identifier,
            "status": "PENDING_KAGGLE_SMOKE",
            "notes": "Model loader smoke is deferred to Kaggle execution.",
        }
        for slot, identifier in frozen_models.items()
    ]


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_raw_jsonl_logs(local_rows: list[dict[str, str]]) -> Path:
    out_path = LOCAL_RESULTS_DIR / "trials.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload_map = read_json(REPO_ROOT / "phase4" / "configs" / "payload_reference_map.json")
    source_payload_hash = next(iter(payload_map.values()))
    with out_path.open("w", encoding="utf-8") as handle:
        for index, row in enumerate(local_rows, start=1):
            trial = {
                "phase": "phase5_adversarial_core",
                "official_trial": False,
                "trial_id": f"{row['row_id']}",
                "run_id": "phase4_5_kaggle_smoke_run",
                "branch": "phase5-model-1",
                "git_commit_hash": record_git_commit(),
                "timestamp_utc": current_utc(),
                "model_id": row["model_slot"],
                "exact_model_identifier": row["exact_model_identifier"],
                "model_digest": "TO_VERIFY_ON_KAGGLE",
                "quantization": "float16",
                "backend": "transformers",
                "backend_version": "transformers==5.0.0",
                "ollama_version": None,
                "density": row["density"],
                "metadata_surface_condition": row["metadata_surface_condition"],
                "attack_family": row["attack_family"],
                "defense_condition": "BASELINE",
                "payload_id": row["payload_id"],
                "phase1_payload_hash": source_payload_hash,
                "payload_hash": "TO_VERIFY_ON_KAGGLE",
                "adversarial_payload_present": True,
                "payload_condition": "PHASE1_HASH_AUTHORIZED",
            }
            record = {
                "phase": "phase4_5",
                "dry_run": True,
                "official_trial": False,
                "counts_for_phase5": False,
                "publication_evidence": False,
                "payload_reference_validated": True,
                "trial": trial,
                "row_index": index,
            }
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return out_path


def write_hardware_metrics() -> Path:
    out_path = LOCAL_RESULTS_DIR / "hardware_metrics.json"
    write_json(
        out_path,
        {
            "timestamp_utc": current_utc(),
            "cpu": "TO_VERIFY_ON_KAGGLE",
            "gpu": "TO_VERIFY_ON_KAGGLE",
            "ram": "TO_VERIFY_ON_KAGGLE",
            "cuda_available": "TO_VERIFY_ON_KAGGLE",
        },
    )
    return out_path


def write_reset_checks() -> Path:
    out_path = LOCAL_RESULTS_DIR / "reset_checks.json"
    write_json(
        out_path,
        {
            "timestamp_utc": current_utc(),
            "reset_visible_in_mcp": False,
            "dispatch_rejection_verified": False,
            "notes": "Reset checks are scaffold-only until Kaggle execution.",
        },
    )
    return out_path


def write_failures_and_invalid_trials() -> Path:
    out_path = LOCAL_RESULTS_DIR / "failures_and_invalid_trials.json"
    write_json(out_path, {"failures": [], "invalid_trials": []})
    return out_path


def write_rerun_links(local_rows: list[dict[str, str]]) -> Path:
    out_path = LOCAL_RESULTS_DIR / "rerun_links.json"
    links = {
        row["row_id"]: f"phase4_5/dryrun_results/local/reruns/{row['row_id']}.json"
        for row in local_rows
    }
    write_json(out_path, links)
    return out_path


def write_run_manifest(local_rows: list[dict[str, str]], kaggle_rows: list[dict[str, str]], loader_rows: list[dict[str, str]]) -> Path:
    out_path = RUN_MANIFEST_DIR / "phase45_run_manifest.json"
    write_json(
        out_path,
        {
            "phase": "phase4_5",
            "dry_run": True,
            "official_trial": False,
            "counts_for_phase5": False,
            "publication_evidence": False,
            "git_commit_hash": record_git_commit(),
            "timestamp_utc": current_utc(),
            "local_matrix_rows": len(local_rows),
            "kaggle_matrix_rows": len(kaggle_rows),
            "loader_rows": len(loader_rows),
            "no_phase5_claims": True,
        },
    )
    return out_path


def write_run_hashes(artifacts: list[Path]) -> Path:
    out_path = RUN_MANIFEST_DIR / "phase45_run_hashes.json"
    write_json(out_path, {str(path.relative_to(ROOT)): sha256_file(path) for path in artifacts})
    return out_path


def run_log_validation(log_path: Path) -> Path:
    report_path = VALIDATION_DIR / "phase45_log_schema_report.md"
    subprocess.check_call(
        [
            sys.executable,
            str(ROOT / "scripts" / "validate_phase45_logs.py"),
            "--input",
            str(log_path),
            "--report",
            str(report_path),
            "--allow-empty",
        ],
        cwd=REPO_ROOT,
    )
    return report_path


def run_statistics_smoke(kaggle_rows: list[dict[str, str]]) -> Path:
    out_path = VALIDATION_DIR / "phase45_statistics_smoke_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    densities = sorted({row["density"] for row in kaggle_rows})
    out_path.write_text(
        "\n".join(
            [
                "# Phase 4.5 Statistics Smoke Report",
                "",
                f"- Timestamp: `{current_utc()}`",
                f"- Row count: `{len(kaggle_rows)}`",
                f"- Densities: `{', '.join(densities)}`",
                "- No inferential statistics computed in the scaffold.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


def write_quota_feasibility_report(kaggle_rows: list[dict[str, str]]) -> Path:
    out_path = VALIDATION_DIR / "phase45_quota_feasibility_report.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(
            [
                "# Phase 4.5 Quota Feasibility Report",
                "",
                f"- Timestamp: `{current_utc()}`",
                f"- Planned Kaggle smoke rows: `{len(kaggle_rows)}`",
                "- No Phase 5 quota claim is made by this scaffold.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return out_path


@dataclass(frozen=True)
class KaggleSmokePlan:
    phase: str
    execution_surface: str
    official_trial: bool
    counts_for_phase5: bool
    selected_model_slot: str
    selected_model_identifier: str
    current_status: str


def build_smoke_plan() -> KaggleSmokePlan:
    selected = load_selected_model()
    return KaggleSmokePlan(
        phase="phase4_5",
        execution_surface="kaggle",
        official_trial=False,
        counts_for_phase5=False,
        selected_model_slot=selected["model_slot"],
        selected_model_identifier=selected["exact_model_identifier"],
        current_status="KAGGLE_SMOKE_PREPARED",
    )


def main() -> int:
    repo_commit = record_git_commit()
    env = verify_environment_lock()
    frozen = load_frozen_phase4_configs()
    schema = load_schema_mapping()
    mapping_validation = validate_schema_mapping(frozen["phase5_schema"], schema)
    local_rows = build_or_load_local_matrix()
    kaggle_rows = build_or_load_kaggle_smoke_matrix()
    loader_rows = perform_loader_smoke(frozen["model_set"])
    trial_log = write_raw_jsonl_logs(local_rows)
    hardware_report = write_hardware_metrics()
    reset_report = write_reset_checks()
    failure_report = write_failures_and_invalid_trials()
    rerun_links = write_rerun_links(local_rows)
    run_manifest = write_run_manifest(local_rows, kaggle_rows, loader_rows)
    run_hashes = write_run_hashes([trial_log, hardware_report, reset_report, failure_report, rerun_links, run_manifest])
    log_validation = run_log_validation(trial_log)
    stats_report = run_statistics_smoke(kaggle_rows)
    quota_report = write_quota_feasibility_report(kaggle_rows)

    summary = {
        "repo_commit": repo_commit,
        "environment_lock": env,
        "schema_mapping": mapping_validation,
        "smoke_plan": asdict(build_smoke_plan()),
        "artifacts": [
            str(path.relative_to(ROOT))
            for path in [trial_log, hardware_report, reset_report, failure_report, rerun_links, run_manifest, run_hashes, log_validation, stats_report, quota_report]
        ],
        "no_phase5_claims": True,
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if mapping_validation["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
