"""Build the Phase 4.5 Kaggle smoke matrix."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = ROOT / "phase4_5" / "matrices" / "phase45_kaggle_smoke_matrix.csv"


def build_rows() -> list[dict[str, str]]:
    return [
        {
            "row_id": "kaggle-01",
            "density": "D3",
            "metadata_surface_condition": "POISON_TD",
            "attack_family": "DIRECT_OVERRIDE",
            "payload_id": "kaggle_smoke_01",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Minimum coverage row.",
        },
        {
            "row_id": "kaggle-02",
            "density": "D3",
            "metadata_surface_condition": "POISON_CA",
            "attack_family": "CROSS_CAPABILITY_ESCALATION",
            "payload_id": "kaggle_smoke_02",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Minimum coverage row.",
        },
        {
            "row_id": "kaggle-03",
            "density": "D5",
            "metadata_surface_condition": "POISON_TD",
            "attack_family": "DATA_EXFILTRATION",
            "payload_id": "kaggle_smoke_03",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Minimum coverage row.",
        },
        {
            "row_id": "kaggle-04",
            "density": "D5",
            "metadata_surface_condition": "POISON_CA",
            "attack_family": "DIRECT_OVERRIDE",
            "payload_id": "kaggle_smoke_04",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Minimum coverage row.",
        },
        {
            "row_id": "kaggle-05",
            "density": "D3",
            "metadata_surface_condition": "POISON_TD",
            "attack_family": "CROSS_CAPABILITY_ESCALATION",
            "payload_id": "kaggle_smoke_05",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Extended smoke coverage.",
        },
        {
            "row_id": "kaggle-06",
            "density": "D3",
            "metadata_surface_condition": "POISON_CA",
            "attack_family": "DIRECT_OVERRIDE",
            "payload_id": "kaggle_smoke_06",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Extended smoke coverage.",
        },
        {
            "row_id": "kaggle-07",
            "density": "D5",
            "metadata_surface_condition": "POISON_TD",
            "attack_family": "DIRECT_OVERRIDE",
            "payload_id": "kaggle_smoke_07",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Extended smoke coverage.",
        },
        {
            "row_id": "kaggle-08",
            "density": "D5",
            "metadata_surface_condition": "POISON_CA",
            "attack_family": "CROSS_CAPABILITY_ESCALATION",
            "payload_id": "kaggle_smoke_08",
            "phase": "phase4_5",
            "dry_run": "true",
            "official_trial": "false",
            "counts_for_phase5": "false",
            "publication_evidence": "false",
            "notes": "Extended smoke coverage.",
        },
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the Phase 4.5 Kaggle smoke matrix")
    parser.add_argument("--out", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    rows = build_rows()
    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
