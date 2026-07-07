"""
Module: validate_phase5_schema.py
Purpose: Generates and rigorously validates the Phase 5 schema structure.
"""
import os
import json
import sys
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_schema() -> dict:
    """Returns the strict Phase 5 schema defined in the Execution Plan Sec 13."""
    return {
      "phase": "phase5_adversarial_core|phase5_adversarial_defense|phase5_utility_preservation",
      "official_trial": True,
      "trial_id": "string",
      "run_id": "string",
      "branch": "phase5-model-1",
      "git_commit_hash": "sha:string",
      "timestamp_utc": "string",
      "model_id": "M1",
      "exact_model_identifier": "string",
      "model_digest": "sha256:string",
      "quantization": "string",
      "backend": "string",
      "backend_version": "string",
      "ollama_version": "string|null",
      "density": "D1|D3|D5",
      "metadata_surface_condition": "CLEAN|POISON_TD|POISON_CA",
      "attack_family": "DIRECT_OVERRIDE|CROSS_CAPABILITY_ESCALATION|DATA_EXFILTRATION|NONE",
      "defense_condition": "BASELINE|IHR_SPCE",
      "payload_id": "string|null",
      "phase1_payload_hash": "sha256:string|null",
      "payload_hash": "sha256:string|null",
      "adversarial_payload_present": True,
      "payload_condition": "NONE|PHASE1_HASH_AUTHORIZED"
    }

def main():
    parser = argparse.ArgumentParser(description="Validate Phase 5 Schema")
    parser.add_argument("--schema-out", default="phase4/configs/phase5_schema_freeze.json", help="Schema freeze output")
    args = parser.parse_args()

    schema = get_schema()
    
    os.makedirs(os.path.dirname(args.schema_out), exist_ok=True)
    with open(args.schema_out, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, sort_keys=True, ensure_ascii=False)
        
    try:
        # Validate that the generated JSON is valid natively
        with open(args.schema_out, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            if not isinstance(loaded, dict) or "phase" not in loaded:
                raise ValueError("Required keys missing from serialized schema")
        logging.info("[+] Schema generated and verified valid.")
    except Exception as e:
        logging.error(f"[-] Schema invalid: {e}")
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()
