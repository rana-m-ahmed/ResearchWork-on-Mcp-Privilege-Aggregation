"""Remote checkpoint publication for long-running Phase 5.5 campaigns."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git_head(root: Path) -> str:
    return subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()


@dataclass(slots=True)
class GitEvidenceCheckpointPublisher:
    root: Path
    model_slot: str
    run_id: str
    output_dir: Path
    sequence: int = 0
    _last_parent: str | None = field(default=None, init=False)

    def on_trial_completed(self, batch: Any, lineage: Any, completed_lineage_count: int) -> None:
        self.sequence += 1
        parent = _git_head(self.root)
        checkpoint_relative = (
            Path("phase5_5/evidence/checkpoints")
            / self.run_id
            / f"checkpoint-{self.sequence:06d}.json"
        ).as_posix()
        checkpoint_path = self.root / checkpoint_relative
        lineage_path = self.root / "phase5_5/evidence/lineage.csv"
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_text(
            json.dumps(
                {
                    "artifact": "phase5_5_trial_checkpoint_v1",
                    "batch_id": batch.batch_id,
                    "checkpoint_sequence": self.sequence,
                    "completed_lineage_count": completed_lineage_count,
                    "last_attempt_id": lineage.attempt_id,
                    "last_target_trial_id": lineage.target_trial_id,
                    "lineage_sha256": _sha256(lineage_path),
                    "model_slot": self.model_slot,
                    "parent_head": parent,
                    "run_id": self.run_id,
                    "written_utc": datetime.now(timezone.utc).isoformat(),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        receipt_path = self.output_dir / f"{self.model_slot}_checkpoint_{self.sequence:06d}.json"
        command = [
            sys.executable,
            "phase5_5/scripts/publish_checkpoint.py",
            "--root",
            str(self.root),
            "--model-slot",
            self.model_slot,
            "--run-id",
            self.run_id,
            "--checkpoint-sequence",
            str(self.sequence),
            "--checkpoint",
            checkpoint_relative,
            "--expected-parent",
            parent,
            "--output",
            str(receipt_path),
        ]
        completed = subprocess.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if completed.returncode != 0:
            raise RuntimeError(f"checkpoint publication failed: {completed.stderr.strip()}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if receipt.get("remote_head_after_push") != receipt.get("publication_commit"):
            raise RuntimeError("checkpoint receipt failed remote-head reconciliation")
        self._last_parent = str(receipt["remote_head_after_push"])
        print(
            f"OFFICIAL_CHECKPOINT_PUBLISHED: sequence={self.sequence}; "
            f"completed_lineage={completed_lineage_count}; remote_head={self._last_parent}",
            flush=True,
        )

