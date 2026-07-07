"""
Module: generate_trial_ordering.py
Purpose: Generates deterministic trial ordering CSVs based on frozen Phase 3 tasks and Phase 1 payloads.

Determinism Rule: All scripts must derive outputs exclusively from committed upstream artifacts.
No script may fabricate placeholder values, silently substitute defaults, infer missing evidence,
or generate synthetic metadata. When required evidence is unavailable, the script must explicitly
report DEPENDENCY_MISSING or NOT_MEASURABLE with justification.
"""
import os
import sys
import argparse
import logging
import json
import csv
import random
import hashlib
import yaml
import re
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_frozen_models(filepath: str) -> list:
    """Extracts locked model keys from model_set_freeze.yaml"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Missing required model freeze artifact: {filepath}")
        
    models = []
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if isinstance(data, dict):
            models = list(data.keys())
        elif isinstance(data, list):
            models = data
            
    # Validate model schema
    for m in models:
        if not isinstance(m, str) or not m.strip():
            raise ValueError(f"Model validation failed: invalid model identifier '{m}'. Must be a non-empty string.")
            
    return models

def get_frozen_defenses(filepath: str) -> list:
    """Extracts locked defense conditions from defense_config_freeze.yaml"""
    if not os.path.exists(filepath):
        raise ValueError("NOT_MEASURABLE: The authoritative defense freeze artifact is missing.")
        
    defenses = []
    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
        if isinstance(data, dict) and "defense" in data:
            defenses = [data["defense"]]
        elif isinstance(data, dict) and "defenses" in data:
            defenses = data["defenses"]
        elif isinstance(data, list):
            defenses = data
        elif isinstance(data, dict):
            defenses = list(data.keys())
            
    if not defenses:
        raise ValueError("NOT_MEASURABLE: The authoritative schema does not explicitly expose defense conditions.")
        
    for d in defenses:
        if not isinstance(d, str) or not d.strip():
            raise ValueError(f"Defense validation failed: invalid defense identifier '{d}'. Must be a non-empty string.")
            
    return sorted(defenses)

def extract_densities_from_schema(schema_file: str) -> list:
    """
    Derives density labels directly from the authoritative Phase 5 Schema Freeze.
    """
    if not os.path.exists(schema_file):
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
    densities = []
    with open(schema_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        
        if "density" in data and isinstance(data["density"], str):
            densities = data["density"].split("|")
                
    if not densities:
        raise ValueError("NOT_MEASURABLE: The finalized schema does not explicitly encode density labels.")
        
    for d in densities:
        if not isinstance(d, str) or not d.strip():
            raise ValueError(f"Density validation failed: invalid density label '{d}'. Must be a non-empty string.")
            
    return densities

def main():
    parser = argparse.ArgumentParser(description="Generate Deterministic Trial Order")
    parser.add_argument("--schema", default="phase4/configs/phase5_schema_freeze.json", help="Phase 5 Schema")
    parser.add_argument("--payloads", default="phase1/ledger/payload_provenance_ledger.json", help="Phase 1 payload ledger")
    parser.add_argument("--models", default="phase4/configs/model_set_freeze.yaml", help="Frozen models")
    parser.add_argument("--defenses", default="phase4/configs/defense_config_freeze.yaml", help="Frozen defenses")
    parser.add_argument("--out-core", default="phase4/frozen_bundle/trial_order_core.csv", help="Output core order")
    args = parser.parse_args()

    # Verify dependencies
    missing = [p for p in [args.schema, args.payloads, args.models, args.defenses] if not os.path.exists(p)]

    if missing:
        logging.warning(f"[-] Required upstream data missing: {missing}. Cannot freeze trial order.")
        os.makedirs("phase4/validation", exist_ok=True)
        generate_report(
            filepath="phase4/validation/trial_ordering_report.md",
            title="Trial Ordering Generation Report",
            purpose="Generate a strict deterministic trial schedule for Phase 5.",
            inputs=[args.schema, args.payloads, args.models, args.defenses],
            checks=["Cross-reference schemas and payloads"],
            failures=[f"Upstream files missing: {missing}"],
            warnings=[],
            recommendations=["Complete upstream generation."],
            summary="Status: DEPENDENCY_MISSING\n\nExecution deferred. Trial order CSVs remain unavailable until upstream generation completes.",
            evidence={"missing_files": missing}
        )
        sys.exit(1)

    failures = []
    models = []
    defenses = []
    densities = []

    # Load resources and aggregate errors
    try:
        models = get_frozen_models(args.models)
    except Exception as e:
        failures.append(f"Model freeze error: {e}")

    try:
        defenses = get_frozen_defenses(args.defenses)
    except Exception as e:
        failures.append(str(e))

    try:
        densities = extract_densities_from_schema(args.schema)
    except Exception as e:
        failures.append(str(e))

    try:
        with open(args.payloads, "r", encoding="utf-8") as f:
            payload_ledger = json.load(f)
    except Exception as e:
        failures.append(f"Payload ledger read error: {e}")
        payload_ledger = {}

    if failures:
        logging.error("[-] Upstream dependency validation failed.")
        for f in failures:
            logging.error(f"    {f}")
        os.makedirs("phase4/validation", exist_ok=True)
        generate_report(
            filepath="phase4/validation/trial_ordering_report.md",
            title="Trial Ordering Generation Report",
            purpose="Generate a strict deterministic trial schedule for Phase 5.",
            inputs=[args.schema, args.payloads, args.models, args.defenses],
            checks=["Validate authoritative configurations and ledgers natively"],
            failures=failures,
            warnings=[],
            recommendations=[],
            summary=f"Status: {'NOT_MEASURABLE' if any('NOT_MEASURABLE' in f for f in failures) else 'FAIL'}\n\nValidation failures occurred during data extraction.",
            evidence={"failures": failures}
        )
        sys.exit(1)
        
    # Extract canonical payload IDs, preserving deterministic ordering and checking hash integrity
    payload_hash_map = {}
    hash_to_pid_map = {}
    
    payloads_list = payload_ledger.get("payloads", [])
    if not isinstance(payloads_list, list) or len(payloads_list) == 0:
        failures.append("Payload ledger validation failed: payload list is missing or empty.")
        payloads_list = []
        
    for p in payloads_list:
        pid = p.get("payload_id")
        phash = p.get("phase1_payload_hash")
        
        if pid:
            if phash is not None and (not isinstance(phash, str) or not bool(re.fullmatch(r"[a-f0-9]{64}", phash))):
                failures.append(f"Hash validation failed for {pid}: invalid SHA256 format.")
                continue
                
            # Same payload_id but different hash
            if pid in payload_hash_map and payload_hash_map[pid] != phash:
                failures.append(f"Integrity violation: Conflicting hashes for payload {pid}.")
            
            # Same hash but different payload_id
            if phash is not None and phash in hash_to_pid_map and hash_to_pid_map[phash] != pid:
                failures.append(f"Integrity violation: Multiple payload IDs ({hash_to_pid_map[phash]} and {pid}) map to the same hash {phash}.")
                
            payload_hash_map[pid] = phash
            if phash is not None:
                hash_to_pid_map[phash] = pid

    if failures:
        logging.error("[-] Payload integrity validation failed.")
        for f in failures:
            logging.error(f"    {f}")
        sys.exit(1)

    payload_keys = sorted(list(payload_hash_map.keys()))
            
    if not models or not densities or not payload_keys or not defenses:
        logging.error("Derived components (models, densities, defenses, or payloads) are empty.")
        sys.exit(1)
        
    # Generate cross-product
    trials = []
    trial_id = 1
    for model in sorted(models):
        for density in densities:
            for p_key in payload_keys:
                for defense in defenses:
                    trials.append({
                        "trial_id": f"T{trial_id:05d}",
                        "model_id": model,
                        "density": density,
                        "payload_id": p_key,
                        "payload_condition": "PHASE1_HASH_AUTHORIZED",
                        "defense_condition": defense,
                        "status": "PENDING"
                    })
                    trial_id += 1

    # Deterministic shuffle using isolated PRNG instance
    rng = random.Random(42)
    rng.shuffle(trials)
    
    # Validation: len(unique_trial_ids) == len(csv_rows)
    unique_ids = {t["trial_id"] for t in trials}
    if len(unique_ids) != len(trials):
        logging.error("Uniqueness validation failed: trial IDs are not strictly unique.")
        sys.exit(1)

    os.makedirs(os.path.dirname(args.out_core), exist_ok=True)
    with open(args.out_core, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial_id", "model_id", "density", "payload_id", "payload_condition", "defense_condition", "status"])
        writer.writeheader()
        writer.writerows(trials)
        
    # Hash the output
    with open(args.out_core, "rb") as f:
        csv_hash = hashlib.sha256(f.read()).hexdigest()
        
    os.makedirs("phase4/validation", exist_ok=True)
    generate_report(
        filepath="phase4/validation/trial_ordering_report.md",
        title="Trial Ordering Generation Report",
        purpose="Generate a strict deterministic trial schedule for Phase 5.",
        inputs=[args.schema, args.payloads, args.models, args.defenses],
        checks=["Cross-product generation", "Isolated PRNG shuffle (seed 42)", "Trial uniqueness check", "Payload integrity check"],
        failures=[],
        warnings=[],
        recommendations=["Lock CSV hash into cryptographic manifest."],
        summary=f"Status: PASS\n\nGenerated {len(trials)} unique trial combinations deterministically utilizing valid upstream artifacts.",
        evidence={
            "total_trials": len(trials), 
            "models_included": models, 
            "densities_included": densities, 
            "defenses_included": defenses,
            "payload_count": len(payload_keys),
            "trial_order_sha256": csv_hash
        }
    )

    logging.info(f"[+] Trial ordering deterministic schedule generated at {args.out_core}")
    sys.exit(0)

if __name__ == '__main__':
    main()
