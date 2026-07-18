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
    assert "OFFICIAL_CAMPAIGN_HEARTBEAT" in source
    assert "OFFICIAL_CAMPAIGN_START" in source
    assert "subprocess.Popen" in source
    campaign_source = source[source.index("campaign_error"):source.index("def sha256")]
    assert "subprocess.run(campaign_command" not in campaign_source

    engine_source = (root / "phase5/runtime/engine.py").read_text(encoding="utf-8")
    assert "MODEL_GPU_LOAD_START" in engine_source
    assert "MODEL_GPU_MODEL_READY" in engine_source
