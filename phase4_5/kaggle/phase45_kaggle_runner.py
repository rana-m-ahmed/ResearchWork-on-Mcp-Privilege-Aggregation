"""Phase 4.5 Kaggle smoke runner scaffold.

This module stays intentionally small so the notebook can call the same logic
without drifting into notebook-only behavior.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class KaggleSmokePlan:
    phase: str
    execution_surface: str
    official_trial: bool
    counts_for_phase5: bool
    selected_model_slot: str
    selected_model_identifier: str
    current_status: str


def build_smoke_plan() -> KaggleSmokePlan:
    return KaggleSmokePlan(
        phase="phase4_5_kaggle_smoke",
        execution_surface="kaggle",
        official_trial=False,
        counts_for_phase5=False,
        selected_model_slot="M1",
        selected_model_identifier="Qwen/Qwen2.5-7B-Instruct",
        current_status="KAGGLE_SMOKE_PREPARED",
    )


def main() -> int:
    plan = build_smoke_plan()
    print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
