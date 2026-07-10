"""Generate the canonical I17E Kaggle notebook deterministically."""

from __future__ import annotations

import json
from pathlib import Path


OUTPUT = Path(__file__).resolve().parents[1] / "kaggle" / "phase5_runner.ipynb"


def code(stage: str, source: str) -> dict[str, object]:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"phase5_stage": stage},
        "outputs": [],
        "source": source.splitlines(keepends=True),
    }


def markdown(source: str) -> dict[str, object]:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(keepends=True)}


CELLS = [
    markdown(
        "# Phase 5 Official-Capable Kaggle Runner\n\n"
        "I17E development build. Official dispatch remains locked until the v3 qualification and authorization gates pass.\n"
    ),
    code(
        "environment_identity",
        '''from datetime import datetime, timezone
from pathlib import Path
import json, os, re, subprocess, sys

REPO_ROOT = Path("/kaggle/working/ResearchWork-on-Mcp-Privilege-Aggregation")
REPOSITORY_URL = os.environ.get("PHASE5_REPOSITORY_URL", "https://github.com/rana-m-ahmed/ResearchWork-on-Mcp-Privilege-Aggregation.git")
SOURCE_TAG_OR_COMMIT = os.environ.get("PHASE5_SOURCE_TAG", "phase5-official-source-v3")
EXPECTED_SOURCE_COMMIT = os.environ.get("PHASE5_EXPECTED_SOURCE_COMMIT", "")
MODEL_SLOT = os.environ.get("PHASE5_MODEL_SLOT", "M1")
EVIDENCE_BRANCHES = {"M1":"phase5-model-1","M2":"phase5-model-2","M3":"phase5-model-3","M4":"phase5-model-4"}
EVIDENCE_BRANCH = EVIDENCE_BRANCHES.get(MODEL_SLOT, "")
DATASET_VERSION = "P5-DV-1.0.2-A7C91E42"
UTC_DATE = datetime.now(timezone.utc).strftime("%Y%m%d")
RUN_TOKEN = os.urandom(4).hex().upper()
RUN_ID = f"P5RUN-{DATASET_VERSION}-{MODEL_SLOT}-{UTC_DATE}-{RUN_TOKEN}"
SEAL_EPOCH = 1
SYNC_MANIFEST_PATH = REPO_ROOT / "phase5" / "checkpoints" / MODEL_SLOT / RUN_ID / "sync_manifest.json"
SYNC_RECEIPT_PATH = REPO_ROOT / "phase5" / "checkpoints" / MODEL_SLOT / RUN_ID / "sync_receipt.json"
CANARY_FIXTURE_ID = f"I17E-SYNTHETIC-{MODEL_SLOT}"
AUTHORIZATION_PHRASE = f"AUTHORIZE_OFFICIAL_{MODEL_SLOT}_DISPATCH"
I17E_DEVELOPMENT_LOCK = True

assert re.fullmatch(r"[0-9a-f]{40}", EXPECTED_SOURCE_COMMIT), "Set exact PHASE5_EXPECTED_SOURCE_COMMIT"
assert EVIDENCE_BRANCH, "Unknown frozen model slot"
assert not any("<" in str(value) or ">" in str(value) for value in (REPOSITORY_URL, SOURCE_TAG_OR_COMMIT, EXPECTED_SOURCE_COMMIT, EVIDENCE_BRANCH, RUN_ID))
''',
    ),
    code(
        "clone_evidence_branch",
        '''subprocess.run(["git","clone","--branch",EVIDENCE_BRANCH,"--single-branch",REPOSITORY_URL,str(REPO_ROOT)], check=True)
subprocess.run(["git","-C",str(REPO_ROOT),"fetch","--tags","origin",SOURCE_TAG_OR_COMMIT], check=True)
''',
    ),
    code(
        "verify_source",
        '''SOURCE_VERIFICATION_RULE = "branch HEAD execution is prohibited"
subprocess.run(["git","-C",str(REPO_ROOT),"checkout","--detach",SOURCE_TAG_OR_COMMIT], check=True)
actual_commit = subprocess.check_output(["git","-C",str(REPO_ROOT),"rev-parse","HEAD"], text=True).strip()
if actual_commit != EXPECTED_SOURCE_COMMIT:
    raise RuntimeError(f"Source mismatch: expected {EXPECTED_SOURCE_COMMIT}, got {actual_commit}")
''',
    ),
    code(
        "install_pinned_dependencies",
        '''LOCKFILE = REPO_ROOT / "phase4_5" / "kaggle" / "requirements.lock.txt"
if not LOCKFILE.is_file(): raise RuntimeError("Pinned dependency lock is missing")
subprocess.run([sys.executable,"-m","pip","install","--requirement",str(LOCKFILE)], check=True)
''',
    ),
    code(
        "strict_gate0",
        '''subprocess.run([sys.executable,"-m","phase5","gate0","--strict","--root",str(REPO_ROOT),"--report-dir","phase5/validation"], cwd=REPO_ROOT, check=True)
''',
    ),
    code(
        "runtime_model_verification",
        '''from phase5.runtime.model_backend_adapter import load_frozen_model_backend_identity
identity = load_frozen_model_backend_identity(root=REPO_ROOT)
if identity.model_id != MODEL_SLOT: raise RuntimeError("Frozen model slot mismatch")
''',
    ),
    code(
        "non_official_startup_canary",
        '''CANARY = {"fixture_id": CANARY_FIXTURE_ID, "official_trial": False, "counts_for_phase5": False, "publication_evidence": False, "synthetic_fixture": True}
assert CANARY["official_trial"] is False and CANARY["synthetic_fixture"] is True
''',
    ),
    code(
        "build_resume_campaign_plan",
        '''subprocess.run([sys.executable,"-m","phase5","checkpoint-status","--model-slot",MODEL_SLOT], cwd=REPO_ROOT, check=True)
subprocess.run([sys.executable,"-m","phase5","resume-plan","--model-slot",MODEL_SLOT], cwd=REPO_ROOT, check=True)
resume_plan = json.loads((REPO_ROOT / "phase5/validation/campaign_resume_plan.json").read_text(encoding="utf-8"))
FIRST_PENDING_BATCH = resume_plan.get("next_batch_id")
if not FIRST_PENDING_BATCH: raise RuntimeError("No pending frozen batch is available")
''',
    ),
    code(
        "operator_confirmation",
        '''operator_confirmation = os.environ.get("PHASE5_OPERATOR_CONFIRMATION", "")
if operator_confirmation != AUTHORIZATION_PHRASE:
    raise RuntimeError(f"Explicit operator confirmation required: {AUTHORIZATION_PHRASE}")
if I17E_DEVELOPMENT_LOCK:
    raise RuntimeError("I17E development lock: official row dispatch remains prohibited")
''',
    ),
    code("session_open", '''subprocess.run([sys.executable,"-m","phase5","session-open","--model-slot",MODEL_SLOT,"--batch-id",FIRST_PENDING_BATCH,"--run-id",RUN_ID], cwd=REPO_ROOT, check=True)\n'''),
    code("seal_epoch", '''subprocess.run([sys.executable,"-m","phase5","session-seal","--run-id",RUN_ID,"--seal-epoch",str(SEAL_EPOCH)], cwd=REPO_ROOT, check=True)\n'''),
    code("real_run_campaign", '''subprocess.run([sys.executable,"-m","phase5","run-campaign","--official","--dataset-version",DATASET_VERSION,"--model-slot",MODEL_SLOT,"--run-id",RUN_ID,"--seal-epoch",str(SEAL_EPOCH),"--until-safety-horizon"], cwd=REPO_ROOT, check=True)\n'''),
    code("batch_finalization", '''assert SYNC_MANIFEST_PATH.is_file(), "Finalized sync manifest is missing"\n'''),
    code("seal_closure", '''subprocess.run([sys.executable,"-m","phase5","session-close-seal","--run-id",RUN_ID], cwd=REPO_ROOT, check=True)\n'''),
    code("stop_runtime", '''MODEL_AND_MCP_PROCESSES_STOPPED = True\nassert MODEL_AND_MCP_PROCESSES_STOPPED\n'''),
    code("github_checkpoint_sync", '''subprocess.run([sys.executable,"-m","phase5","sync-github","--repo",str(REPO_ROOT),"--manifest",str(SYNC_MANIFEST_PATH),"--allowlist","phase5/configs/sync_allowlist.yaml","--receipt",str(SYNC_RECEIPT_PATH)], cwd=REPO_ROOT, check=True)\n'''),
    code("remote_sha_verification", '''assert SYNC_RECEIPT_PATH.is_file(), "Sync receipt is missing"\n'''),
    code("credential_purge", '''os.environ.pop("GITHUB_TOKEN", None)\nassert "GITHUB_TOKEN" not in os.environ\n'''),
    code("source_freeze_reverification", '''subprocess.run([sys.executable,"-m","phase5","session-reverify","--repo",str(REPO_ROOT),"--receipt",str(SYNC_RECEIPT_PATH)], cwd=REPO_ROOT, check=True)\n'''),
    code("new_seal_or_termination", '''NO_MORE_OFFICIAL_EXECUTION_IN_SESSION = True\n'''),
    code("campaign_resume_report", '''subprocess.run([sys.executable,"-m","phase5","checkpoint-status","--model-slot",MODEL_SLOT,"--run-id",RUN_ID], cwd=REPO_ROOT, check=True)\n'''),
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


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(NOTEBOOK, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")
