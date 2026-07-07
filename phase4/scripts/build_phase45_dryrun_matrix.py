"""
Module: build_phase45_dryrun_matrix.py
Purpose: Generates the dry run matrix based on rigorous execution plan rules (Section 20).
"""
import os
import argparse
import sys
import logging
import csv

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Build Phase 4.5 Dry Run Matrix")
    parser.add_argument("--matrix-out", default="phase4_5/dryrun_matrix.csv", help="Output matrix file")
    args = parser.parse_args()

    # The Phase 4.5 execution plan Section 20 strictly specifies:
    # 1 model, D3 and D5 only, POISON_TD and POISON_CA only.
    matrix = [
        {"model_id": "M1", "density": "D3", "metadata_surface_condition": "POISON_TD", "attack_family": "DIRECT_OVERRIDE", "payload_id": "dry_run_payload_1"},
        {"model_id": "M1", "density": "D3", "metadata_surface_condition": "POISON_CA", "attack_family": "DIRECT_OVERRIDE", "payload_id": "dry_run_payload_2"},
        {"model_id": "M1", "density": "D5", "metadata_surface_condition": "POISON_TD", "attack_family": "CROSS_CAPABILITY_ESCALATION", "payload_id": "dry_run_payload_3"},
        {"model_id": "M1", "density": "D5", "metadata_surface_condition": "POISON_CA", "attack_family": "CROSS_CAPABILITY_ESCALATION", "payload_id": "dry_run_payload_4"}
    ]
    
    os.makedirs(os.path.dirname(args.matrix_out), exist_ok=True)
    
    with open(args.matrix_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["model_id", "density", "metadata_surface_condition", "attack_family", "payload_id"])
        writer.writeheader()
        for row in matrix:
            writer.writerow(row)

    logging.info(f"[+] Dry run matrix generated at {args.matrix_out} with {len(matrix)} cells.")
    sys.exit(0)

if __name__ == '__main__':
    main()
