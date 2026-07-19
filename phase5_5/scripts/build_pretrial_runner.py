"""Build the bounded real-backend Phase 5.5 pretrial notebook."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "phase5_5/kaggle/phase5_5_runner.ipynb"
OUTPUT = ROOT / "phase5_5/kaggle/phase5_5_pretrial_runner.ipynb"


def find_cell(notebook: dict, stage: str) -> dict:
    return next(cell for cell in notebook["cells"] if cell.get("metadata", {}).get("phase5_5_stage") == stage)


def set_source(cell: dict, source: str) -> None:
    cell["source"] = source.splitlines(keepends=True)


def main() -> None:
    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
    config_path = ROOT / "phase5_5/branch_config.json"
    slot = json.loads(config_path.read_text(encoding="utf-8-sig"))["model_slot"]
    config = find_cell(notebook, "configuration")
    source = "".join(config["source"])
    source = source.replace(
        'MODEL_SLOT = os.environ.get("PHASE5_MODEL_SLOT", "M1").upper()',
        f'MODEL_SLOT = "{slot}"',
    )
    source = source.replace(
        'EXECUTE_OFFICIAL = os.environ.get("PHASE5_EXECUTE_OFFICIAL", "0") == "1"',
        "EXECUTE_OFFICIAL = False",
    )
    source = source.replace(
        'RUN_ID = f"P5RUN-{DATASET_VERSION}-{MODEL_SLOT}-{UTC_DATE}-{RUN_TOKEN}"',
        'RUN_ID = f"P5PRE-{DATASET_VERSION}-{MODEL_SLOT}-{UTC_DATE}-{RUN_TOKEN}"',
    )
    set_source(config, source)

    campaign = find_cell(notebook, "official_campaign")
    set_source(campaign, '''
from kaggle_secrets import UserSecretsClient
import selectors
import time

hf_token = (UserSecretsClient().get_secret("HF_TOKEN") or "").strip()
if not hf_token:
    raise RuntimeError("HF_TOKEN is required for the real-backend pretrial")
os.environ["HF_TOKEN"] = hf_token
pretrial_report = OUTPUT_ROOT / f"{MODEL_SLOT}_pretrial_report.json"
pretrial_command = [
    sys.executable,
    "-m",
    "phase5",
    "run-campaign",
    "--pretrial",
    "--model-slot",
    MODEL_SLOT,
    "--dataset-version",
    DATASET_VERSION,
    "--run-id",
    RUN_ID,
    "--seal-epoch",
    "1",
    "--until-safety-horizon",
    "--max-batches",
    "1",
    "--batch-manifest",
    "phase5/manifests/batch_partition_manifest_v3.json",
    "--run-plan",
    "phase5/validation/kaggle_run_plan_v3.json",
    "--output",
    str(pretrial_report),
]
print(f"PRETRIAL_START: slot={MODEL_SLOT}; one_frozen_batch=50_rows", flush=True)
started = time.monotonic()
process = subprocess.Popen(
    pretrial_command,
    cwd=REPO_ROOT,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)
assert process.stdout is not None
selector = selectors.DefaultSelector()
selector.register(process.stdout, selectors.EVENT_READ)
tail = []
while process.poll() is None:
    events = selector.select(timeout=30.0)
    if events:
        line = process.stdout.readline()
        if line:
            line = line.rstrip("\n")
            print(line, flush=True)
            tail.append(line)
            del tail[:-100:]
    else:
        elapsed = int(time.monotonic() - started)
        print(f"PRETRIAL_HEARTBEAT: elapsed_seconds={elapsed}", flush=True)
for line in process.stdout:
    line = line.rstrip("\n")
    print(line, flush=True)
    tail.append(line)
returncode = process.wait()
if returncode != 0:
    (OUTPUT_ROOT / f"{MODEL_SLOT}_pretrial_error.json").write_text(
        json.dumps({"returncode": returncode, "output_tail": tail}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    raise RuntimeError(f"real-backend pretrial failed with exit code {returncode}")
report = json.loads(pretrial_report.read_text(encoding="utf-8"))
if report.get("model_slot") != MODEL_SLOT or report.get("resume_required") is not False:
    raise RuntimeError("pretrial report does not reconcile to one completed slot run")
print(f"PRETRIAL_COMPLETE: {pretrial_report}", flush=True)
''')

    evidence = find_cell(notebook, "evidence_package")
    set_source(evidence, '''
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

evidence_root = REPO_ROOT / "phase5_5/evidence"
if not evidence_root.is_dir():
    raise RuntimeError("pretrial produced no evidence directory")
files = sorted(path for path in evidence_root.rglob("*") if path.is_file())
manifest = {
    "artifact": "phase5_5_real_backend_pretrial_v1",
    "model_slot": MODEL_SLOT,
    "run_id": RUN_ID,
    "dataset_version": DATASET_VERSION,
    "official_trial": False,
    "counts_for_phase5": False,
    "publication_evidence": False,
    "pretrial_batch_limit": 1,
    "files": [{"path": str(path.relative_to(REPO_ROOT)), "sha256": sha256(path)} for path in files],
}
manifest_path = OUTPUT_ROOT / f"{MODEL_SLOT}_pretrial_manifest.json"
manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
archive_path = OUTPUT_ROOT / f"{MODEL_SLOT}_pretrial_evidence.tar.gz"
with tarfile.open(archive_path, "w:gz") as archive:
    archive.add(evidence_root, arcname="phase5_5/evidence")
    archive.add(manifest_path, arcname=f"phase5_5/{manifest_path.name}")
print(json.dumps({"manifest": str(manifest_path), "archive": str(archive_path), "archive_sha256": sha256(archive_path)}, indent=2))
''')
    OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
