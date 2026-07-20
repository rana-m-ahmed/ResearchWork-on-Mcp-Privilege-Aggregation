"""Build the versioned Phase 5.5 Kaggle execution notebook."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "phase5_5" / "kaggle" / "phase5_5_runner.ipynb"


def markdown(source: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


def code(stage: str, source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"phase5_5_stage": stage},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


CELLS = [
    markdown(
        "# Phase 5.5 Kaggle Runner\n\n"
        "This notebook runs one frozen model slot per Kaggle GPU session. It verifies the repository, "
        "hardware, dependencies, parser fixtures, provenance gates, and evidence boundary before any "
        "official dispatch. The current repository remains authorization-locked until its policy says "
        "official dispatch is enabled.\n"
    ),
    code(
        "configuration",
        '''from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tarfile

REPOSITORY_URL = os.environ.get(
    "PHASE5_REPOSITORY_URL",
    "https://github.com/rana-m-ahmed/ResearchWork-on-Mcp-Privilege-Aggregation.git",
)
MODEL_SLOT = os.environ.get("PHASE5_MODEL_SLOT", "M1").upper()
EXECUTE_OFFICIAL = os.environ.get("PHASE5_EXECUTE_OFFICIAL", "0") == "1"
DATASET_VERSION = "P5-DV-1.1.0-TREATMENT-V3"
EXPECTED_BRANCH_HEADS = {
    "M1": "ee7ce192",
    "M2": "59418737",
    "M3": "7b72659a",
    "M4": "818a94ac",
}
BRANCHES = {slot: f"phase5_5-model-{slot.removeprefix('M')}" for slot in ("M1", "M2", "M3", "M4")}
MODEL_IDS = {
    "M1": "Qwen/Qwen2.5-7B-Instruct",
    "M2": "deepseek-ai/DeepSeek-R1-Distill-Llama-8B",
    "M3": "mistralai/Mistral-7B-Instruct-v0.3",
    "M4": "microsoft/Phi-3.5-mini-instruct",
}
if MODEL_SLOT not in BRANCHES:
    raise ValueError(f"MODEL_SLOT must be one of {tuple(BRANCHES)}, got {MODEL_SLOT!r}")

REPO_ROOT = Path("/kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation")
OUTPUT_ROOT = Path("/kaggle/working/phase5_5_outputs")
UTC_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
RUN_TOKEN = secrets.token_hex(4).upper()
RUN_ID = f"P5RUN-{DATASET_VERSION}-{MODEL_SLOT}-{UTC_DATE}-{RUN_TOKEN}"
BRANCH = BRANCHES[MODEL_SLOT]
OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
print(json.dumps({"model_slot": MODEL_SLOT, "branch": BRANCH, "run_id": RUN_ID, "official_requested": EXECUTE_OFFICIAL}, indent=2))
''',
    ),
    code(
        "clone_and_fetch_refs",
        '''if REPO_ROOT.exists():
    raise RuntimeError(f"Refusing to reuse existing repository path: {REPO_ROOT}")
subprocess.run(["git", "clone", "--no-single-branch", REPOSITORY_URL, str(REPO_ROOT)], check=True)
for branch_name in BRANCHES.values():
    subprocess.run(
        ["git", "-C", str(REPO_ROOT), "fetch", "origin", f"refs/heads/{branch_name}:refs/heads/{branch_name}"],
        check=True,
    )
subprocess.run(["git", "-C", str(REPO_ROOT), "checkout", "--detach", BRANCH], check=True)
''',
    ),
    code(
        "source_and_branch_provenance",
        '''def git(*arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO_ROOT), *arguments], text=True).strip()

actual_branch_head = git("rev-parse", "HEAD")
expected_prefix = EXPECTED_BRANCH_HEADS[MODEL_SLOT]
if expected_prefix and not actual_branch_head.startswith(expected_prefix):
    print(f"BRANCH_HEAD_CHANGED_AFTER_BUILD: expected_prefix={expected_prefix}; actual={actual_branch_head}")
freeze = json.loads((REPO_ROOT / "phase5_5/manifests/phase5_5_source_freeze_v3.json").read_text(encoding="utf-8-sig"))
if freeze.get("artifact") != "phase5_5_source_freeze_v3" or freeze.get("dataset_version") != DATASET_VERSION:
    raise RuntimeError("v3 source freeze does not match the treatment dataset")
if subprocess.run(
    ["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", freeze["source_commit"], actual_branch_head],
    check=False,
).returncode != 0:
    raise RuntimeError("v3 source freeze is not an ancestor of the selected branch head")
branch_config = json.loads((REPO_ROOT / "phase5_5/branch_config.json").read_text(encoding="utf-8-sig"))
if branch_config["model_slot"] != MODEL_SLOT or branch_config["exact_model_identifier"] != MODEL_IDS[MODEL_SLOT]:
    raise RuntimeError("selected branch does not match its approved model slot")
print(json.dumps({"branch_head": actual_branch_head, "source_commit": freeze["source_commit"], "model_id": MODEL_IDS[MODEL_SLOT]}, indent=2))
''',
    ),
    code(
        "hardware_and_dependencies",
        '''def run_checked(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\\n{completed.stderr}")
    return completed.stdout

nvidia = run_checked(["nvidia-smi"])
print(nvidia)
subprocess.run([sys.executable, "-m", "pip", "install", "--requirement", str(REPO_ROOT / "phase4_5/kaggle/requirements.lock.txt")], check=True)
hardware = run_checked([
    sys.executable,
    "-c",
    "import torch; assert torch.cuda.is_available(); print({'torch': torch.__version__, 'cuda': torch.version.cuda, 'devices': torch.cuda.device_count()})",
])
print(hardware)
''',
    ),
    code(
        "fixtures_and_gate0",
        '''test_environment = os.environ.copy()
test_environment["PYTHONDONTWRITEBYTECODE"] = "1"
pytest_command = [
    sys.executable,
    "-m",
    "pytest",
    "-q",
    "phase5/tests",
    "phase5_5/tests",
    "-p",
    "no:cacheprovider",
    "--basetemp",
    str(OUTPUT_ROOT / "pytest-temp"),
]
subprocess.run(pytest_command, cwd=REPO_ROOT, env=test_environment, check=True)
gate_report = OUTPUT_ROOT / "gate0_authorization_report"
subprocess.run(
    [sys.executable, "-m", "phase5", "gate0", "--strict", "--root", str(REPO_ROOT), "--report-dir", str(gate_report)],
    cwd=REPO_ROOT,
    check=True,
)
canary_path = OUTPUT_ROOT / "qualification_canary.json"
subprocess.run(
    [
        sys.executable,
        "phase5_5/scripts/run_qualification_canary.py",
        "--root",
        str(REPO_ROOT),
        "--output",
        str(canary_path),
    ],
    cwd=REPO_ROOT,
    check=True,
)
canary = json.loads(canary_path.read_text(encoding="utf-8"))
if canary.get("pass") is not True or len(canary.get("records", [])) != 4:
    raise RuntimeError("live qualification canary failed")
''',
    ),
    code(
        "official_preflight",
        '''preflight_path = OUTPUT_ROOT / "official_preflight.json"
preflight_run = subprocess.run(
    [sys.executable, "phase5_5/scripts/official_preflight.py", "--root", str(REPO_ROOT), "--output", str(preflight_path)],
    cwd=REPO_ROOT,
    check=False,
    capture_output=True,
    text=True,
)
preflight = json.loads(preflight_path.read_text(encoding="utf-8"))
non_authorization_failures = [failure for failure in preflight["failures"] if failure != "official-dispatch-disabled"]
if non_authorization_failures:
    raise RuntimeError(f"official preflight failed for infrastructure/provenance reasons: {non_authorization_failures}")
if not preflight["checks"]["cuda_available"]:
    raise RuntimeError("Kaggle CUDA check failed")
if "official-dispatch-disabled" in preflight["failures"]:
    print("READY_FOR_AUTHORIZATION: repository policy still forbids official dispatch")
    if EXECUTE_OFFICIAL:
        raise RuntimeError("PHASE5_EXECUTE_OFFICIAL=1 but repository authorization is still disabled")
else:
    print("OFFICIAL_PREFLIGHT_PASS")
''',
    ),
    code(
        "official_campaign",
        '''if not EXECUTE_OFFICIAL:
    print("No official rows dispatched. Set PHASE5_EXECUTE_OFFICIAL=1 only after the versioned authorization amendment passes preflight.")
elif preflight["failures"]:
    raise RuntimeError(f"official execution blocked by preflight failures: {preflight['failures']}")
else:
    campaign_report = OUTPUT_ROOT / f"{MODEL_SLOT}_campaign.json"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "phase5",
            "run-campaign",
            "--official",
            "--model-slot",
            MODEL_SLOT,
            "--dataset-version",
            DATASET_VERSION,
            "--run-id",
            RUN_ID,
            "--seal-epoch",
            "1",
            "--until-safety-horizon",
            "--batch-manifest",
            "phase5/manifests/batch_partition_manifest_v3_treatment.json",
            "--run-plan",
            "phase5/validation/kaggle_run_plan_v3_treatment.json",
            "--output",
            str(campaign_report),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    print(f"OFFICIAL_CAMPAIGN_COMPLETE: {campaign_report}")
''',
    ),
    code(
        "evidence_package",
        '''def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

if EXECUTE_OFFICIAL and not preflight["failures"]:
    evidence_root = REPO_ROOT / "phase5_5/evidence"
    if not evidence_root.is_dir():
        raise RuntimeError("official campaign did not produce phase5_5/evidence")
    evidence_files = sorted(path for path in evidence_root.rglob("*") if path.is_file())
    evidence_manifest = {
        "artifact": "phase5_5_kaggle_evidence_package",
        "model_slot": MODEL_SLOT,
        "branch": BRANCH,
        "branch_head": actual_branch_head,
        "run_id": RUN_ID,
        "dataset_version": DATASET_VERSION,
        "source_commit": freeze["source_commit"],
        "files": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in evidence_files],
    }
    manifest_path = OUTPUT_ROOT / f"{MODEL_SLOT}_evidence_manifest.json"
    manifest_path.write_text(json.dumps(evidence_manifest, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    archive_path = OUTPUT_ROOT / f"{MODEL_SLOT}_evidence.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(evidence_root, arcname="phase5_5/evidence")
        archive.add(manifest_path, arcname=f"phase5_5/{manifest_path.name}")
    print(json.dumps({"manifest": str(manifest_path), "archive": str(archive_path), "archive_sha256": sha256(archive_path)}, indent=2))
else:
    print("No official evidence package created.")
''',
    ),
]


NOTEBOOK = {
    "cells": CELLS,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}


def main() -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(NOTEBOOK, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
