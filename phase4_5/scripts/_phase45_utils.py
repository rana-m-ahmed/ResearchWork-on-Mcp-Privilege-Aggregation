"""Shared helpers for Phase 4.5 local handoff scripts."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[2]
PHASE4_ROOT = ROOT / "phase4"
PHASE45_ROOT = ROOT / "phase4_5"
CONFIG_DIR = PHASE45_ROOT / "configs"
MATRIX_DIR = PHASE45_ROOT / "matrices"
DRYRUN_LOCAL_DIR = PHASE45_ROOT / "dryrun_results" / "local"
DRYRUN_KAGGLE_DIR = PHASE45_ROOT / "dryrun_results" / "kaggle_smoke"
DRYRUN_LOADER_DIR = PHASE45_ROOT / "dryrun_results" / "kaggle_model_loader_smoke"
VALIDATION_DIR = PHASE45_ROOT / "validation"
REPORTS_DIR = PHASE45_ROOT / "reports"
RUN_MANIFEST_DIR = PHASE45_ROOT / "run_manifests"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_yaml(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def current_utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def python_version() -> str:
    return platform.python_version()


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def detect_local_model_feasibility() -> tuple[bool, str, dict[str, bool]]:
    capabilities = {
        "torch": module_available("torch"),
        "transformers": module_available("transformers"),
    }
    feasible = all(capabilities.values())
    if feasible:
        return True, "local model execution feasible", capabilities
    missing = [name for name, present in capabilities.items() if not present]
    return False, f"missing local model dependencies: {', '.join(missing)}", capabilities


def load_frozen_model_set() -> dict[str, str]:
    data = read_yaml(PHASE4_ROOT / "configs" / "model_set_freeze.yaml")
    if not isinstance(data, dict):
        raise TypeError("model_set_freeze.yaml must contain a mapping")
    return data


def load_frozen_payload_map() -> dict[str, str]:
    data = read_json(PHASE4_ROOT / "configs" / "payload_reference_map.json")
    if not isinstance(data, dict):
        raise TypeError("payload_reference_map.json must contain a mapping")
    return data


def load_selected_model() -> dict[str, Any]:
    data = read_yaml(CONFIG_DIR / "phase45_selected_model.yaml")
    if not isinstance(data, dict):
        raise TypeError("phase45_selected_model.yaml must contain a mapping")
    return data


def load_local_matrix() -> list[dict[str, str]]:
    return read_csv_rows(MATRIX_DIR / "phase45_local_dryrun_matrix.csv")


def load_kaggle_matrix() -> list[dict[str, str]]:
    return read_csv_rows(MATRIX_DIR / "phase45_kaggle_smoke_matrix.csv")


def load_loader_matrix(path: Path) -> list[dict[str, str]]:
    return read_csv_rows(path)


def load_phase5_schema() -> dict[str, Any]:
    data = read_json(PHASE4_ROOT / "configs" / "phase5_schema_freeze.json")
    if not isinstance(data, dict):
        raise TypeError("phase5_schema_freeze.json must contain a mapping")
    return data


def compile_prompt(row: dict[str, str], selected_model: dict[str, Any], payload_key: str, payload_hash: str) -> str:
    return "\n".join(
        [
            f"phase=phase4_5",
            f"model_slot={selected_model['model_slot']}",
            f"exact_model_identifier={selected_model['exact_model_identifier']}",
            f"density={row['density']}",
            f"metadata_surface_condition={row['metadata_surface_condition']}",
            f"attack_family={row['attack_family']}",
            f"payload_reference_key={payload_key}",
            f"payload_reference_hash={payload_hash}",
            "instruction=simulate schema-only dry run without mutating payload text",
        ]
    )


def render_md_list(items: Iterable[str]) -> str:
    items = list(items)
    return "\n".join(f"- {item}" for item in items) if items else "- none"
