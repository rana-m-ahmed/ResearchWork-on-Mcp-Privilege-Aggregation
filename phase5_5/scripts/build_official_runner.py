"""Build the fixed-slot official runner inside a model evidence branch."""

from __future__ import annotations

import json
from pathlib import Path


SLOT = "M2"
BASE_HEAD = "50a8cba90ca9c50e630b893854947968c21763ce"
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
print("OFFICIAL_AUTHORIZED_PREFLIGHT_PASS")
''')

    evidence = cell(notebook, "evidence_package")
    set_source(evidence, '''def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

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

from kaggle_secrets import UserSecretsClient
os.environ["PHASE5_GITHUB_TOKEN"] = UserSecretsClient().get_secret("PHASE5_GITHUB_TOKEN")
publication_receipt = OUTPUT_ROOT / f"{MODEL_SLOT}_publication_receipt.json"
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
print(json.dumps({"manifest": str(manifest_path), "archive": str(archive_path), "publication_receipt": str(publication_receipt)}, indent=2))
''')
    OUTPUT.write_text(json.dumps(notebook, indent=1, ensure_ascii=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
