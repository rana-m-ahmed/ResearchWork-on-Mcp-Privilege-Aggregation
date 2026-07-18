from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from phase5_5.checkpointing import GitEvidenceCheckpointPublisher


def test_checkpoint_publisher_writes_hash_bound_receipt(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path
    lineage = root / "phase5_5/evidence/lineage.csv"
    lineage.parent.mkdir(parents=True)
    lineage.write_text("lineage\n", encoding="utf-8")
    monkeypatch.setattr("phase5_5.checkpointing._git_head", lambda _: "a" * 40)

    def fake_run(command, *, cwd, capture_output, text, check):
        output = Path(command[command.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        receipt = {
            "publication_commit": "b" * 40,
            "remote_head_after_push": "b" * 40,
        }
        output.write_text(json.dumps(receipt), encoding="utf-8")
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("phase5_5.checkpointing.subprocess.run", fake_run)
    publisher = GitEvidenceCheckpointPublisher(
        root=root,
        model_slot="M2",
        run_id="P5RUN-P5-DV-1.0.2-A7C91E42-M2-20260718-ABCDEF12",
        output_dir=tmp_path / "receipts",
    )

    publisher.on_trial_completed(
        SimpleNamespace(batch_id="batch-1"),
        SimpleNamespace(attempt_id="attempt-1", target_trial_id="trial-1"),
        6,
    )

    checkpoint = next((root / "phase5_5/evidence/checkpoints").rglob("checkpoint-000001.json"))
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    assert payload["parent_head"] == "a" * 40
    assert payload["lineage_sha256"]
    assert publisher._last_parent == "b" * 40
