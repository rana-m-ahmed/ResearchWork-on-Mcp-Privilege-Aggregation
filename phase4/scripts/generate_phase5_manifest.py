"""
Module: generate_phase5_manifest.py
Purpose: Generates the strict execution manifest for Phase 5.
"""
import os
import sys
import json
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Generate Phase 5 Execution Manifest")
    parser.add_argument("--manifest-out", default="phase4/frozen_bundle/phase5_execution_manifest.json", help="Output path")
    args = parser.parse_args()

    manifest = {
        "repository_version": "1.0.0",
        "schema_version": "1.2",
        "dependencies": {
            "model_freeze": "phase4/configs/model_set_freeze.yaml",
            "payload_map": "phase4/configs/payload_reference_map.json",
            "defense_freeze": "phase4/configs/defense_config_freeze.yaml",
            "statistical_plan": "phase4/configs/statistical_plan.yaml",
            "trial_order": "phase4/frozen_bundle/trial_order_core.csv"
        },
        "execution_groups": [
            "benign_baseline",
            "adversarial_core",
            "adversarial_defense",
            "utility_preservation"
        ],
        "expected_outputs": {
            "required_reports": [
                "phase5_final_evaluation_report.md",
                "phase5_attack_success_rate_summary.md"
            ],
            "required_csvs": [
                "phase5_results_core.csv",
                "phase5_results_defense.csv"
            ]
        }
    }
    
    os.makedirs(os.path.dirname(args.manifest_out), exist_ok=True)
    with open(args.manifest_out, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    logging.info(f"[+] Phase 5 execution manifest built successfully at {args.manifest_out}")
    sys.exit(0)

if __name__ == '__main__':
    main()
