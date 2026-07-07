"""
Module: generate_phase5_manifest.py
Purpose: Generates the strict execution manifest for Phase 5.

Determinism Rule: All scripts must derive outputs exclusively from committed upstream artifacts.
No script may fabricate placeholder values, silently substitute defaults, infer missing evidence,
or generate synthetic metadata. When required evidence is unavailable, the script must explicitly
report DEPENDENCY_MISSING or NOT_MEASURABLE with justification.
"""
import os
import sys
import json
import argparse
import logging
import hashlib
import subprocess
import yaml
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.hashing import hash_file_sha256

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_git_commit() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except Exception as e:
        logging.warning(f"Audit log: Repository commit could not be determined natively ({e}).")
        return "NOT_MEASURABLE"

def get_git_tag() -> str:
    try:
        return subprocess.check_output(["git", "describe", "--tags"], stderr=subprocess.DEVNULL).decode("utf-8").strip()
    except Exception as e:
        logging.warning(f"Audit log: Repository version could not be determined natively ({e}).")
        return "NOT_MEASURABLE"

def main():
    parser = argparse.ArgumentParser(description="Generate Phase 5 Execution Manifest")
    parser.add_argument("--manifest-out", default="phase4/frozen_bundle/phase5_execution_manifest.json", help="Output path")
    args = parser.parse_args()

    # Gather Metrics & Hashes
    # Phase 1 Ledger
    p1_ledger = Path("phase1/ledger/payload_provenance_ledger.json")
    if not p1_ledger.exists():
        logging.error(f"Authoritative artifact missing: {p1_ledger}")
        sys.exit(1)
        
    try:
        with open(p1_ledger, "r", encoding="utf-8") as f:
            data = json.load(f)
            p1_hash = hash_file_sha256(str(p1_ledger))
            if not bool(re.fullmatch(r"^[a-f0-9]{64}$", p1_hash)):
                raise ValueError("Payload ledger hash failed SHA256 validation.")
            canonical_payload_count = data.get("metadata", {}).get("canonical_payload_count")
            if canonical_payload_count is None:
                canonical_payload_count = "NOT_MEASURABLE"
    except Exception as e:
        logging.error(f"Failed to parse authoritative Phase 1 ledger: {e}")
        sys.exit(1)

    # Phase 3 Freeze Hash
    p3_manifest = Path("reproducibility/phase3_hash_manifest.json")
    if not p3_manifest.exists():
        logging.error(f"Authoritative artifact missing: {p3_manifest}")
        sys.exit(1)
        
    try:
        with open(p3_manifest, "r", encoding="utf-8") as f:
            data = json.load(f)
            p3_hash = data.get("global_source")
            if not p3_hash or not bool(re.fullmatch(r"^[a-f0-9]{64}$", p3_hash)):
                raise ValueError("DEPENDENCY_MISSING: Phase3 hash manifest does not contain the required global_source cryptographic freeze metadata. Phase3 freeze is incomplete.")
    except Exception as e:
        logging.error(f"Failed to parse Phase 3 freeze manifest: {e}")
        sys.exit(1)

    # Trial Ordering
    trial_order = Path("phase4/frozen_bundle/trial_order_core.csv")
    if not trial_order.exists():
        logging.error(f"Authoritative artifact missing: {trial_order}")
        sys.exit(1)
        
    try:
        trial_order_sha256 = hash_file_sha256(str(trial_order))
        if not bool(re.fullmatch(r"^[a-f0-9]{64}$", trial_order_sha256)):
            raise ValueError("Trial order hash failed SHA256 validation.")
        with open(trial_order, "r", encoding="utf-8") as f:
            expected_trial_count = sum(1 for _ in f) - 1
            if expected_trial_count <= 0:
                raise ValueError("Expected trial count is zero or negative.")
    except Exception as e:
        logging.error(f"Failed to parse trial order CSV: {e}")
        sys.exit(1)

    # Models
    model_set = Path("phase4/configs/model_set_freeze.yaml")
    if not model_set.exists():
        logging.error(f"Authoritative artifact missing: {model_set}")
        sys.exit(1)
        
    try:
        with open(model_set, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict):
                expected_models_count = len(data)
            elif isinstance(data, list):
                expected_models_count = len(data)
            else:
                raise ValueError("Invalid schema for model_set_freeze.yaml")
    except Exception as e:
        logging.error(f"Failed to parse model set freeze: {e}")
        sys.exit(1)

    # Defenses
    defense_set = Path("phase4/configs/defense_config_freeze.yaml")
    expected_defense_count = "NOT_MEASURABLE"
    if defense_set.exists():
        try:
            with open(defense_set, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                if isinstance(data, dict) and "defense" in data:
                    expected_defense_count = 1
                elif isinstance(data, dict) and "defenses" in data and isinstance(data["defenses"], list):
                    expected_defense_count = len(data["defenses"])
                elif isinstance(data, list):
                    expected_defense_count = len(data)
                else:
                    raise ValueError("Malformed defense schema. Must be a list or a dictionary explicitly encoding a 'defense' scalar or 'defenses' list.")
        except Exception as e:
            logging.error(f"Failed to parse defense config freeze: {e}")
            sys.exit(1)

    # Phase 4 Crypto Manifest Hash
    crypto_manifest = Path("phase4/frozen_bundle/cryptographic_lock_manifest.json")
    if not crypto_manifest.exists():
        logging.error(f"Authoritative artifact missing: {crypto_manifest}")
        sys.exit(1)
        
    try:
        crypto_hash = hash_file_sha256(str(crypto_manifest))
        if not bool(re.fullmatch(r"^[a-f0-9]{64}$", crypto_hash)):
            raise ValueError("Cryptographic lock manifest hash failed SHA256 validation.")
    except Exception as e:
        logging.error(f"Failed to hash Phase 4 cryptographic manifest: {e}")
        sys.exit(1)

    manifest = {
        "repository_version": get_git_tag(),
        "schema_version": "1.2",
        "execution_uuid": None,
        "repository_commit": get_git_commit(),
        "hashes": {
            "phase1_ledger_hash": p1_hash,
            "phase3_freeze_hash": p3_hash,
            "phase4_manifest_hash": crypto_hash,
            "trial_order_sha256": trial_order_sha256
        },
        "metrics": {
            "expected_trial_count": expected_trial_count,
            "expected_models": expected_models_count,
            "expected_payload_count": canonical_payload_count,
            "expected_defense_count": expected_defense_count
        },
        "dependencies": {
            "model_freeze": "phase4/configs/model_set_freeze.yaml",
            "payload_map": "phase4/configs/payload_reference_map.json",
            "defense_freeze": "phase4/configs/defense_config_freeze.yaml",
            "statistical_plan": "phase4/configs/statistical_plan.yaml",
            "trial_order": "phase4/frozen_bundle/trial_order_core.csv",
            "cryptographic_manifest": "phase4/frozen_bundle/cryptographic_lock_manifest.json"
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
        json.dump(manifest, f, indent=2, sort_keys=True, ensure_ascii=False)

    logging.info(f"[+] Phase 5 execution manifest built deterministically at {args.manifest_out}")
    sys.exit(0)

if __name__ == '__main__':
    main()
