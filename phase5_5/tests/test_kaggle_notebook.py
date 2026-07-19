from __future__ import annotations

import json
from pathlib import Path


def test_kaggle_runner_notebook_is_valid_and_targets_phase5_5_refs() -> None:
    root = Path(__file__).resolve().parents[2]
    notebook_path = root / "phase5_5/kaggle/phase5_5_official_runner.ipynb"
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))

    assert notebook["nbformat"] == 4
    assert notebook["nbformat_minor"] >= 5
    assert notebook["cells"]
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    for index, cell in enumerate(notebook["cells"]):
        if cell.get("cell_type") == "code":
            compile("".join(cell["source"]), f"kaggle-cell-{index}", "exec")
    assert "phase5_5-model-" in source
    assert "phase5-model-" not in source
    assert 'MODEL_SLOT = "M4"' in source
    assert '"M4": "microsoft/Phi-3.5-mini-instruct"' in source
    assert 'os.environ["PHASE5_REQUIRE_CUDA_DEVICE_COUNT"] = "2"' in source
    assert "torch.cuda.device_count() >= {2 if MODEL_SLOT == 'M4' else 1}" in source
    assert "P5-DV-1.0.2-A7C91E42" in source
    assert "PHASE5_GITHUB_TOKEN" in source
    assert 'get_secret("GITHUB_TOKEN")' not in source
    assert "phase5_5/evidence" in source
    assert '"--basetemp"' in source
    assert 'str(OUTPUT_ROOT / "pytest-temp")' in source
    assert '"--output"' in source
    assert 'str(canary_path)' in source
    assert "MODEL_CACHE_PREP_START" in source
    assert "MODEL_CACHE_READY" in source
    assert "M4_OPTIMIZED_RUNTIME_READY" in source
    assert "GITHUB_PUBLICATION_AUTH_READY" in source
    assert '"--dry-run"' in source
    assert 'AUTHORIZATION: basic' in source
    checkpoint_path = root / "phase5_5/scripts/publish_checkpoint.py"
    if checkpoint_path.exists():
        assert 'AUTHORIZATION: basic' in checkpoint_path.read_text(encoding="utf-8")
    assert 'os.environ["HF_ENABLE_PARALLEL_LOADING"] = "true"' in source
    assert 'os.environ["HF_PARALLEL_LOADING_WORKERS"] = "4"' in source
    assert "load_frozen_model_backend_identity(root=REPO_ROOT, model_slot=MODEL_SLOT)" in source
    assert "OFFICIAL_CAMPAIGN_HEARTBEAT" in source
    assert "OFFICIAL_CAMPAIGN_START" in source
    assert "subprocess.Popen" in source
    assert '"--checkpoint-publish"' in source
    assert '"--checkpoint-interval-trials"' in source
    assert '"6"' in source
    assert "publish_checkpoint.py" in source or "checkpoint-publish" in source
    pretrial_path = root / "phase5_5/kaggle/phase5_5_pretrial_runner.ipynb"
    assert pretrial_path.is_file()
    pretrial_notebook = json.loads(pretrial_path.read_text(encoding="utf-8"))
    pretrial_source = "\n".join(
        "".join(cell.get("source", []))
        for cell in pretrial_notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    assert '"--pretrial"' in pretrial_source
    assert '"--max-batches"' in pretrial_source
    assert '"--pretrial-trials"' in pretrial_source
    assert '"--attempts-root"' in pretrial_source
    assert '"--evidence-root"' in pretrial_source
    assert "/kaggle/working/phase5_5_pretrial_evidence" in pretrial_source
    assert '"official_trial": False' in pretrial_source
    assert 'AUTHORIZATION: basic' in (root / "phase5_5/scripts/publish_checkpoint.py").read_text(encoding="utf-8")
    assert 'actual_branch_head = git("rev-parse", "HEAD")' in source
    assert 'shutil.which("nvidia-smi")' in source
    assert "NVIDIA_SMI_UNAVAILABLE: continuing with torch CUDA verification" in source
    campaign_source = source[source.index("campaign_error"):source.index("def sha256")]
    assert "subprocess.run(campaign_command" not in campaign_source

    backend_source = (root / "phase5/runtime/model_backend_adapter.py").read_text(encoding="utf-8")
    assert "MODEL_GPU_LOAD_START" in backend_source
    assert "MODEL_GPU_MODEL_READY" in backend_source
    assert "M4_GENERATION_METRICS" in backend_source
    assert "generated_tokens_per_second" in backend_source
