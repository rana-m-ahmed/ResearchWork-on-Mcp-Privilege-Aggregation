"""Build the Phase 4.5 remaining-model loader smoke matrices."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODEL_SET_PATH = ROOT / "phase4" / "configs" / "model_set_freeze.yaml"
LOCAL_OUT = ROOT / "phase4_5" / "matrices" / "phase45_remaining_model_loader_smoke_local.csv"
KAGGLE_OUT = ROOT / "phase4_5" / "matrices" / "phase45_remaining_model_loader_smoke_kaggle.csv"


def load_model_set() -> dict[str, str]:
    data = yaml.safe_load(MODEL_SET_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError("Frozen model set must be a mapping")
    return data


def build_rows(model_set: dict[str, str], local: bool) -> list[dict[str, str]]:
    rows = []
    for model_slot, model_identifier in model_set.items():
        status = "NOT_EXECUTED_LOCALLY_DEFERRED_TO_KAGGLE" if local else "PENDING_KAGGLE_SMOKE"
        if local and model_slot == "M1":
            status = "NOT_EXECUTED_LOCALLY_DEFERRED_TO_KAGGLE"
        rows.append(
            {
                "model_slot": model_slot,
                "exact_model_identifier": model_identifier,
                "loader_status": status,
                "execution_surface": "local" if local else "kaggle",
                "notes": "No fake execution; this is a planning matrix only.",
            }
        )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build loader smoke matrices")
    parser.add_argument("--local-out", default=str(LOCAL_OUT))
    parser.add_argument("--kaggle-out", default=str(KAGGLE_OUT))
    args = parser.parse_args()

    model_set = load_model_set()
    local_rows = build_rows(model_set, local=True)
    kaggle_rows = build_rows(model_set, local=False)
    write_csv(Path(args.local_out), local_rows)
    write_csv(Path(args.kaggle_out), kaggle_rows)
    print(f"Wrote {len(local_rows)} local rows and {len(kaggle_rows)} Kaggle rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
