import json
import os
import re

OUTPUT_DIR = "d:/research-work/ResearchWork-on-Mcp-Privilege-Aggregation/phase5/kaggle"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def markdown_cell(text):
    return {"cell_type": "markdown", "metadata": {}, "source": [text]}

def code_cell(source_code):
    # Split by actual newline and append newline to each line except maybe the last
    lines = [line + "\n" for line in source_code.split("\n")]
    if lines and lines[-1] == "\n":
        lines.pop()
    return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": lines}

cells = []

# --- 1. Configuration ---
cells.append(markdown_cell("### 1. Configuration & Constants"))
config_code = """import os
import re

CANDIDATE_SHA = os.environ.get("PHASE5_CANDIDATE_SHA", "").strip()

if not re.fullmatch(r"[0-9a-f]{40}", CANDIDATE_SHA):
    raise RuntimeError(
        "Set PHASE5_CANDIDATE_SHA to the exact P18-approved 40-character commit SHA."
    )

os.environ["REPO_URL"] = "https://github.com/rana-m-ahmed/ResearchWork-on-Mcp-Privilege-Aggregation.git"
os.environ["REPO_DIR"] = "/kaggle/working/research_repo"
os.environ["OUTPUT_DIR"] = "/kaggle/working/phase5_nonofficial_validation"

# For convenience in python cells
OUTPUT_DIR = os.environ["OUTPUT_DIR"]

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/gate0", exist_ok=True)
os.makedirs(f"{OUTPUT_DIR}/logs", exist_ok=True)
"""
cells.append(code_cell(config_code))

# --- 2. Env Bootstrap ---
cells.append(markdown_cell("### 2. Environment Bootstrap & Proof"))
env_bash = """%%bash
pwd
uname -a
nvidia-smi
nvidia-smi --query-gpu=name,memory.total,memory.free,driver_version --format=csv
python --version
git --version
df -h
"""
cells.append(code_cell(env_bash))

env_py = """import torch
print("PyTorch:", torch.__version__)
print("CUDA:", torch.version.cuda)
print("GPU Available:", torch.cuda.is_available())
for i in range(torch.cuda.device_count()):
    print(i, torch.cuda.get_device_name(i))

import psutil
print(f"Available CPU RAM: {psutil.virtual_memory().available / (1024**3):.2f} GB")
"""
cells.append(code_cell(env_py))

# --- 3. Exact Source Checkout ---
cells.append(markdown_cell("### 3. Exact Source Checkout"))
checkout_bash = """%%bash
rm -rf "$REPO_DIR"
git clone "$REPO_URL" "$REPO_DIR"
cd "$REPO_DIR"
git fetch --all --tags
git checkout --detach "$PHASE5_CANDIDATE_SHA"

HEAD_SHA=$(git rev-parse HEAD)
if [ "$HEAD_SHA" != "$PHASE5_CANDIDATE_SHA" ]; then
    echo "ERROR: HEAD is $HEAD_SHA, expected $PHASE5_CANDIDATE_SHA"
    exit 1
fi
echo "Exact source checkout successful."
"""
cells.append(code_cell(checkout_bash))

# --- 4. Dependencies ---
cells.append(markdown_cell("### 4. Dependency Verification"))
deps_bash = """%%bash
cd "$REPO_DIR"
pip install pytest
pip install -e .
pip freeze > "$OUTPUT_DIR/installed_dependencies.txt"
"""
cells.append(code_cell(deps_bash))

# --- 5. Repository Command Invocation: Gate 0 ---
cells.append(markdown_cell("### 5. Gate 0 Authorization"))
gate0_bash = """%%bash
cd "$REPO_DIR"
python -m phase5 gate0 --strict --root . > "$OUTPUT_DIR/gate0/gate0_output.txt" 2>&1
EXIT_CODE=$?
cat "$OUTPUT_DIR/gate0/gate0_output.txt"
if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Gate 0 Failed"
    exit $EXIT_CODE
fi
"""
cells.append(code_cell(gate0_bash))

# --- 6. Framework Validation (Pytest) ---
cells.append(markdown_cell("### 6. FastMCP, Reset, Token Budget, Interruption Validations"))
pytest_bash = """%%bash
cd "$REPO_DIR"
pytest phase5/tests/ -v > "$OUTPUT_DIR/logs/pytest_validation_suite.txt" 2>&1
EXIT_CODE=$?
cat "$OUTPUT_DIR/logs/pytest_validation_suite.txt"
if [ $EXIT_CODE -ne 0 ]; then
    echo "ERROR: Pytest validation framework failed. Hard invariants broken."
    exit $EXIT_CODE
fi
"""
cells.append(code_cell(pytest_bash))

# --- 7. Model Loading & Synthetic Canopy (Thin Client) ---
cells.append(markdown_cell("### 7. Real Sequential Loader & Matrix Validation"))
smoke_bash = """%%bash
cd "$REPO_DIR"
python phase5/scripts/run_kaggle_smoke.py --output-dir "$OUTPUT_DIR"
"""
cells.append(code_cell(smoke_bash))

# --- 8. Evidence Packaging ---
cells.append(markdown_cell("### 8. Evidence Packaging (ZIP backup)"))
pkg_py = """import os
import shutil
import hashlib
import json

OUTPUT_DIR = "/kaggle/working/phase5_nonofficial_validation"
manifest = {}
for root, dirs, files in os.walk(OUTPUT_DIR):
    for f in files:
        if f.endswith(".zip") or f == "artifact_hash_manifest.json":
            continue
        fp = os.path.join(root, f)
        rel_path = os.path.relpath(fp, OUTPUT_DIR)
        
        hash_sha256 = hashlib.sha256()
        with open(fp, "rb") as bf:
            for chunk in iter(lambda: bf.read(4096), b""):
                hash_sha256.update(chunk)
        manifest[rel_path] = hash_sha256.hexdigest()

with open(os.path.join(OUTPUT_DIR, "artifact_hash_manifest.json"), "w") as f:
    json.dump(manifest, f, indent=2)

shutil.make_archive("/kaggle/working/phase5_nonofficial_validation_bundle", 'zip', OUTPUT_DIR)
"""
cells.append(code_cell(pkg_py))

# --- 9. Controlled Synchronization ---
cells.append(markdown_cell("### 9. Controlled Synchronization Barrier (GitHub Non-Official Evidence Push)"))
sync_py = """# Retrieve token securely via python, avoiding shell history if possible,
# but we need it for git push. We inject it into a temporary git config and purge immediately.
import os
import subprocess
try:
    from kaggle_secrets import UserSecretsClient
    github_token = UserSecretsClient().get_secret("GITHUB_TOKEN")
    if not github_token:
        raise ValueError("GITHUB_TOKEN is empty")
        
    REPO_DIR = "/kaggle/working/research_repo"
    OUTPUT_DIR = "/kaggle/working/phase5_nonofficial_validation"
    BRANCH = "phase5-kaggle-nonofficial-evidence"
    
    # Configure git securely
    subprocess.run(["git", "config", "--global", "user.email", "kaggle-validation@example.com"])
    subprocess.run(["git", "config", "--global", "user.name", "Kaggle Validator"])
    
    # We copy evidence to a dedicated repo copy for pushing to avoid muddying the checked out commit
    EVIDENCE_REPO = "/kaggle/working/evidence_repo"
    subprocess.run(["rm", "-rf", EVIDENCE_REPO])
    subprocess.run(["git", "clone", f"https://x-access-token:{github_token}@github.com/rana-m-ahmed/ResearchWork-on-Mcp-Privilege-Aggregation.git", EVIDENCE_REPO])
    
    # Checkout or create branch
    res = subprocess.run(["git", "-C", EVIDENCE_REPO, "checkout", BRANCH])
    if res.returncode != 0:
        subprocess.run(["git", "-C", EVIDENCE_REPO, "checkout", "-b", BRANCH])
        
    # Copy evidence
    subprocess.run(f"cp -r {OUTPUT_DIR}/* {EVIDENCE_REPO}/", shell=True)
    
    # Commit and push
    subprocess.run(["git", "-C", EVIDENCE_REPO, "add", "."])
    subprocess.run(["git", "-C", EVIDENCE_REPO, "commit", "-m", "Non-official kaggle validation evidence sync"])
    push_res = subprocess.run(["git", "-C", EVIDENCE_REPO, "push", "origin", BRANCH])
    
    if push_res.returncode == 0:
        print("[PASS] Controlled synchronization barrier passed. Evidence pushed.")
    else:
        print("[FAIL] Failed to push to remote.")
    
    # Purge token
    subprocess.run(["rm", "-rf", EVIDENCE_REPO])
    github_token = None

except ImportError:
    print("Not running on Kaggle. Synchronization skipped.")
except Exception as e:
    print(f"Synchronization failed: {e}")
"""
cells.append(code_cell(sync_py))

# --- 10. Verdict ---
cells.append(markdown_cell("### 10. Verdict Display"))
verdict_py = """import os
import json

OUTPUT_DIR = "/kaggle/working/phase5_nonofficial_validation"

passed_all = True
failures = []

try:
    with open(os.path.join(OUTPUT_DIR, "model_loading_results.json"), "r") as f:
        model_res = json.load(f)
    for m in ["M1", "M2", "M3", "M4"]:
        if model_res.get(m, {}).get("status") != "PASS":
            passed_all = False
            failures.append(f"Model {m} failed loading.")
            
    with open(os.path.join(OUTPUT_DIR, "synthetic_canary_results.json"), "r") as f:
        canary_res = json.load(f)
    if not all(v == "PASS" for v in canary_res.values()):
        passed_all = False
        failures.append("Synthetic canary smoke test failed.")
except FileNotFoundError:
    passed_all = False
    failures.append("Smoke test evidence missing.")

if passed_all:
    print("KAGGLE IMPLEMENTATION VERDICT:")
    print("GO FOR FINAL READINESS AUDIT")
else:
    print("KAGGLE IMPLEMENTATION VERDICT:")
    print("TARGETED REPAIR REQUIRED")
    for failure in failures:
        print(" -", failure)
    import sys
    sys.exit(1)
"""
cells.append(code_cell(verdict_py))

notebook = {
    "cells": cells,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3"
        },
        "language_info": {
            "codemirror_mode": {"name": "ipython", "version": 3},
            "file_extension": ".py",
            "mimetype": "text/x-python",
            "name": "python",
            "nbconvert_exporter": "python",
            "pygments_lexer": "ipython3",
            "version": "3.10.12"
        }
    },
    "nbformat": 4,
    "nbformat_minor": 4
}

with open(os.path.join(OUTPUT_DIR, "phase5_kaggle_nonofficial_validation.ipynb"), "w") as f:
    json.dump(notebook, f, indent=2)

print("Notebook created in phase5/kaggle/")
