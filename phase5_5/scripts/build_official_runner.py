"""Build the fixed-slot official runner inside a model evidence branch."""

from __future__ import annotations

import json
from pathlib import Path


SLOT = "M4"
BASE_HEAD = "a6f7343ad15b719cc964c0c45f5e09ffff1bdde5"
OUTPUT = Path(__file__).resolve().parents[1] / "kaggle/phase5_5_official_runner.ipynb"
SOURCE = Path(__file__).resolve().parents[1] / "kaggle/phase5_5_runner.ipynb"


def cell(notebook: dict, stage: str) -> dict:
    return next(item for item in notebook["cells"] if item.get("metadata", {}).get("phase5_5_stage") == stage)


def set_source(item: dict, source: str) -> None:
    item["source"] = source.splitlines(keepends=True)


def main() -> None:
    notebook = json.loads(SOURCE.read_text(encoding="utf-8"))
    config = cell(notebook, "configuration")
    source = "".join(config["source"])
    source = source.replace('MODEL_SLOT = os.environ.get("PHASE5_MODEL_SLOT", "M1").upper()', f'MODEL_SLOT = "{SLOT}"')
    source = source.replace('EXECUTE_OFFICIAL = os.environ.get("PHASE5_EXECUTE_OFFICIAL", "0") == "1"', "EXECUTE_OFFICIAL = True")
    head_start = source.find("EXPECTED_BRANCH_HEADS = {")
    if head_start >= 0:
        head_end = source.find("BRANCHES =", head_start)
        if head_end < 0:
            raise RuntimeError("official runner configuration lost BRANCHES declaration")
        source = source[:head_start] + source[head_end:]
    set_source(config, source)

    provenance = cell(notebook, "source_and_branch_provenance")
    set_source(provenance, f'''def git(*arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO_ROOT), *arguments], text=True).strip()

actual_branch_head = git("rev-parse", "HEAD")
if subprocess.run(["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", "{BASE_HEAD}", actual_branch_head], check=False).returncode != 0:
    raise RuntimeError("official branch is not descended from the authorized base head")
freeze = json.loads((REPO_ROOT / "phase5_5/manifests/phase5_5_source_freeze.json").read_text(encoding="utf-8-sig"))
if freeze["source_commit"] != EXPECTED_SOURCE_COMMIT:
    raise RuntimeError(f"source-freeze commit mismatch: {{freeze['source_commit']}}")
branch_config = json.loads((REPO_ROOT / "phase5_5/branch_config.json").read_text(encoding="utf-8-sig"))
if branch_config["model_slot"] != MODEL_SLOT or branch_config["exact_model_identifier"] != MODEL_IDS[MODEL_SLOT]:
    raise RuntimeError("selected branch does not match its approved model slot")
print(json.dumps({{"branch_head": actual_branch_head, "source_commit": freeze["source_commit"], "model_id": MODEL_IDS[MODEL_SLOT]}}, indent=2))
''')

    preflight = cell(notebook, "official_preflight")
    set_source(preflight, '''authorized_preflight_path = OUTPUT_ROOT / "official_authorized_preflight.json"
subprocess.run(
    [
        sys.executable,
        "phase5_5/scripts/official_authorized_preflight.py",
        "--root",
        str(REPO_ROOT),
        "--model-slot",
        MODEL_SLOT,
        "--output",
        str(authorized_preflight_path),
    ],
    cwd=REPO_ROOT,
    check=True,
)
preflight = json.loads(authorized_preflight_path.read_text(encoding="utf-8"))
if preflight.get("pass") is not True:
    raise RuntimeError(f"authorized official preflight failed: {preflight.get('failures')}")
try:
    from kaggle_secrets import UserSecretsClient
    github_token = (UserSecretsClient().get_secret("PHASE5_GITHUB_TOKEN") or "").strip()
    hf_token = (UserSecretsClient().get_secret("HF_TOKEN") or "").strip()
except Exception as exc:
    raise RuntimeError("Kaggle secrets PHASE5_GITHUB_TOKEN and HF_TOKEN are required; refusing official dispatch") from exc
if not github_token:
    raise RuntimeError("Kaggle secret PHASE5_GITHUB_TOKEN is empty; refusing official dispatch")
if not hf_token:
    raise RuntimeError("Kaggle secret HF_TOKEN is empty; refusing official dispatch")
os.environ["PHASE5_GITHUB_TOKEN"] = github_token
os.environ["HF_TOKEN"] = hf_token
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
os.chdir(REPO_ROOT)
from huggingface_hub import snapshot_download
from phase5.runtime.model_backend_adapter import load_frozen_model_backend_identity

backend_identity = load_frozen_model_backend_identity(root=REPO_ROOT, model_slot=MODEL_SLOT)
if backend_identity.model_id != MODEL_SLOT:
    raise RuntimeError("frozen model slot does not match the selected official slot")
print(f"MODEL_CACHE_PREP_START: {backend_identity.exact_model_identifier}", flush=True)
cache_snapshot = snapshot_download(
    repo_id=backend_identity.exact_model_identifier,
    revision=backend_identity.huggingface_commit_sha,
    token=hf_token,
    cache_dir=os.environ["HF_HUB_CACHE"],
)
print(f"MODEL_CACHE_READY: {cache_snapshot}", flush=True)
if MODEL_SLOT == "M4":
    os.environ["PHASE5_M4_ENABLE_KV_CACHE"] = "1"
    m4_canary = OUTPUT_ROOT / "M4_runtime_canary.json"
    canary_command = [
        sys.executable,
        "phase5_5/scripts/run_m4_runtime_canary.py",
        "--root",
        str(REPO_ROOT),
        "--output",
        str(m4_canary),
    ]
    canary_process = subprocess.run(canary_command, cwd=REPO_ROOT, capture_output=True, text=True, check=False)
    if canary_process.returncode != 0:
        raise RuntimeError(f"M4 optimized runtime canary failed: {canary_process.stderr}")
    print(canary_process.stdout, flush=True)
    canary = json.loads(m4_canary.read_text(encoding="utf-8"))
    if canary.get("pass") is not True or canary.get("kv_cache_enabled") is not True:
        raise RuntimeError("M4 optimized runtime canary did not pass")
    print(f"M4_OPTIMIZED_RUNTIME_READY: {m4_canary}", flush=True)
print("OFFICIAL_AUTHORIZED_PREFLIGHT_PASS")
''')

    campaign = cell(notebook, "official_campaign")
    set_source(campaign, '''campaign_error: dict[str, object] | None = None
if not EXECUTE_OFFICIAL:
    print("No official rows dispatched.")
elif preflight.get("pass") is not True:
    raise RuntimeError(f"official execution blocked by preflight failures: {preflight.get('failures')}")
else:
    import selectors
    import time

    campaign_report = OUTPUT_ROOT / f"{MODEL_SLOT}_campaign.json"
    campaign_command = [
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
        "phase5/manifests/batch_partition_manifest_v3.json",
        "--run-plan",
        "phase5/validation/kaggle_run_plan_v3.json",
        "--checkpoint-publish",
        "--checkpoint-interval-trials",
        "6",
        "--checkpoint-output-dir",
        str(OUTPUT_ROOT / "checkpoints"),
        "--output",
        str(campaign_report),
    ]
    try:
        print("OFFICIAL_CAMPAIGN_START: model load and trial dispatch pending", flush=True)
        started = time.monotonic()
        process = subprocess.Popen(
            campaign_command,
            cwd=REPO_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        selector = selectors.DefaultSelector()
        assert process.stdout is not None
        selector.register(process.stdout, selectors.EVENT_READ)
        output_tail: list[str] = []
        last_heartbeat = started
        while True:
            events = selector.select(timeout=30.0)
            if events:
                line = process.stdout.readline()
                if line:
                    line = line.rstrip("\\n")
                    print(line, flush=True)
                    output_tail.append(line)
                    del output_tail[:-200:]
            elif process.poll() is None:
                elapsed = int(time.monotonic() - started)
                nvidia_smi = shutil.which("nvidia-smi")
                if nvidia_smi:
                    gpu = subprocess.run(
                        [nvidia_smi, "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
                        check=False,
                        capture_output=True,
                        text=True,
                    ).stdout.strip().replace("\\n", "; ")
                else:
                    gpu = "unavailable:nvidia-smi"
                print(f"OFFICIAL_CAMPAIGN_HEARTBEAT: elapsed_seconds={elapsed}; gpu={gpu or 'unavailable'}", flush=True)
                last_heartbeat = time.monotonic()
            if process.poll() is not None:
                for remaining in process.stdout:
                    line = remaining.rstrip("\\n")
                    print(line, flush=True)
                    output_tail.append(line)
                    del output_tail[:-200:]
                break
        returncode = process.wait()
        if returncode != 0:
            campaign_error = {
                "artifact": "phase5_5_official_campaign_failure",
                "returncode": returncode,
                "output_tail": output_tail,
            }
            (OUTPUT_ROOT / f"{MODEL_SLOT}_campaign_error.json").write_text(
                json.dumps(campaign_error, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
            )
            print(f"OFFICIAL_CAMPAIGN_FAILED; preserved evidence will still be published: {returncode}", flush=True)
        else:
            print(f"OFFICIAL_CAMPAIGN_COMPLETE: {campaign_report}", flush=True)
    except Exception as exc:
        campaign_error = {"artifact": "phase5_5_official_campaign_failure", "error": str(exc)}
        (OUTPUT_ROOT / f"{MODEL_SLOT}_campaign_error.json").write_text(
            json.dumps(campaign_error, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
        )
        print("OFFICIAL_CAMPAIGN_FAILED; preserved evidence will still be published")
''')

    hardware = cell(notebook, "hardware_and_dependencies")
    set_source(hardware, '''# Carry forward the Kaggle stability controls proven during the repaired Phase 5 runs.
os.environ["NCCL_P2P_DISABLE"] = "1"
os.environ["NCCL_IB_DISABLE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
os.environ["HF_ENABLE_PARALLEL_LOADING"] = "false"
os.environ["HF_PARALLEL_LOADING_WORKERS"] = "1"
os.environ["HF_HOME"] = "/kaggle/working/huggingface_cache"
os.environ["HF_HUB_CACHE"] = "/kaggle/working/huggingface_cache"
os.environ["TRANSFORMERS_CACHE"] = "/kaggle/working/huggingface_cache"
os.environ["PHASE5_MODEL_OFFLOAD_DIR"] = "/kaggle/working/phase5_5_model_offload"
if MODEL_SLOT == "M4":
    # The repaired Phi execution was validated on Kaggle's dual-T4 profile.
    os.environ["PHASE5_REQUIRE_CUDA_DEVICE_COUNT"] = "2"
    os.environ["HF_ENABLE_PARALLEL_LOADING"] = "true"
    os.environ["HF_PARALLEL_LOADING_WORKERS"] = "4"
Path(os.environ["HF_HOME"]).mkdir(parents=True, exist_ok=True)
Path(os.environ["PHASE5_MODEL_OFFLOAD_DIR"]).mkdir(parents=True, exist_ok=True)

def run_checked(command: list[str], *, cwd: Path | None = None) -> str:
    completed = subprocess.run(command, cwd=cwd, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        raise RuntimeError(f"command failed ({completed.returncode}): {' '.join(command)}\\n{completed.stderr}")
    return completed.stdout

nvidia_smi = shutil.which("nvidia-smi")
if nvidia_smi:
    print(run_checked([nvidia_smi]))
else:
    print("NVIDIA_SMI_UNAVAILABLE: continuing with torch CUDA verification")
subprocess.run([sys.executable, "-m", "pip", "install", "--requirement", str(REPO_ROOT / "phase4_5/kaggle/requirements.lock.txt")], check=True)
hardware = run_checked([
    sys.executable,
    "-c",
    f"import torch; assert torch.cuda.is_available(); assert torch.cuda.device_count() >= {2 if MODEL_SLOT == 'M4' else 1}; print({{'torch': torch.__version__, 'cuda': torch.version.cuda, 'devices': torch.cuda.device_count()}})",
])
print(hardware)
''')

    evidence = cell(notebook, "evidence_package")
    set_source(evidence, '''def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

actual_branch_head = git("rev-parse", "HEAD")
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
    archive.add(manifest_path, arcname=f"phase5_5/{{manifest_path.name}}")

if not os.environ.get("PHASE5_GITHUB_TOKEN"):
    raise RuntimeError("official publication credential was not retained from authorization preflight")
publication_receipt = OUTPUT_ROOT / f"{MODEL_SLOT}_publication_receipt.json"
try:
    subprocess.run(
        [
            sys.executable,
            "phase5_5/scripts/publish_official_evidence.py",
            "--root",
            str(REPO_ROOT),
            "--model-slot",
            MODEL_SLOT,
            "--run-id",
            RUN_ID,
            "--expected-parent",
            actual_branch_head,
            "--output",
            str(publication_receipt),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
finally:
    os.environ.pop("PHASE5_GITHUB_TOKEN", None)
    os.environ.pop("HF_TOKEN", None)
    try:
        del github_token
    except NameError:
        pass
    try:
        del hf_token
    except NameError:
        pass
print(json.dumps({"manifest": str(manifest_path), "archive": str(archive_path), "publication_receipt": str(publication_receipt)}, indent=2))
if campaign_error is not None:
    raise RuntimeError(f"official campaign failed after evidence publication: {campaign_error}")
''')
    OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
