"""Build the Phase 4.5 local dry-run matrix."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MODEL_SET_PATH = ROOT / "phase4" / "configs" / "model_set_freeze.yaml"
PAYLOAD_MAP_PATH = ROOT / "phase4" / "configs" / "payload_reference_map.json"
SELECTED_MODEL_PATH = ROOT / "phase4_5" / "configs" / "phase45_selected_model.yaml"
LOCAL_CONFIG_PATH = ROOT / "phase4_5" / "configs" / "phase45_local_dryrun.yaml"
OUTPUT_PATH = ROOT / "phase4_5" / "matrices" / "phase45_local_dryrun_matrix.csv"


def load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a mapping")
    return data


def load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 4.5 local dry-run matrix")
    parser.add_argument("--out", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    model_set = load_yaml(MODEL_SET_PATH)
    selected = load_yaml(SELECTED_MODEL_PATH)
    local_config = load_yaml(LOCAL_CONFIG_PATH)
    payload_map = load_json(PAYLOAD_MAP_PATH)

    selected_slot = selected["model_slot"]
    selected_identifier = selected["exact_model_identifier"]
    if selected_slot not in model_set:
        raise ValueError(f"Selected model slot {selected_slot} is not in the frozen model set")
    if model_set[selected_slot] != selected_identifier:
        raise ValueError("Selected model identifier does not match the frozen model set")

    payload_reference_key, payload_reference_hash = next(iter(payload_map.items()))
    densities = list(local_config["densities"])
    surfaces = list(local_config["metadata_surfaces"])
    attack_families = ["DIRECT_OVERRIDE", "CROSS_CAPABILITY_ESCALATION"]

    rows = []
    trial_counter = 0
    for density_index, density in enumerate(densities, start=1):
        for surface_index, surface in enumerate(surfaces, start=1):
            attack_family = attack_families[(density_index + surface_index - 2) % len(attack_families)]
            for trial_index in range(1, 7):
                trial_counter += 1
                rows.append(
                    {
                        "row_id": f"local-{trial_counter:02d}",
                        "cell_id": f"{selected_slot}-{density}-{surface}-{attack_family}",
                        "trial_index": trial_index,
                        "phase": "phase4_5",
                        "dry_run": "true",
                        "official_trial": "false",
                        "counts_for_phase5": "false",
                        "publication_evidence": "false",
                        "payload_reference_validated": "true",
                        "model_slot": selected_slot,
                        "exact_model_identifier": selected_identifier,
                        "density": density,
                        "metadata_surface_condition": surface,
                        "attack_family": attack_family,
                        "payload_id": f"{payload_reference_key}#{trial_counter:02d}",
                        "payload_reference_key": payload_reference_key,
                        "payload_reference_hash": payload_reference_hash,
                        "trial_phase": "phase5_adversarial_core",
                        "trial_defense_condition": "BASELINE",
                        "notes": "Phase 4.5 local dry-run planning row; no official Phase 5 credit.",
                    }
                )

    fieldnames = list(rows[0].keys()) if rows else []
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
