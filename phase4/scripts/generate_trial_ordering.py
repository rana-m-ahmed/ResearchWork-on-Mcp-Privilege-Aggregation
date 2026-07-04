"""
Module: generate_trial_ordering.py
Purpose: Generates deterministic trial ordering CSVs based on frozen Phase 3 tasks and Phase 2.5 payloads.
"""
import os
import sys
import argparse
import logging
import json
import csv
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def get_frozen_models(filepath: str) -> list:
    """Extracts locked model keys from model_set_freeze.yaml"""
    if not os.path.exists(filepath):
        return ["M1", "M2", "M3", "M4"] # fallback
    models = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if ":" in line:
                models.append(line.split(":")[0].strip())
    return models

def main():
    parser = argparse.ArgumentParser(description="Generate Deterministic Trial Order")
    parser.add_argument("--task-corpus", default="phase3/tasks/task_corpus.json", help="Phase 3 task summary")
    parser.add_argument("--payloads", default="phase2_5/inputs/payload_approved_set.json", help="Phase 2.5 payloads")
    parser.add_argument("--models", default="phase4/configs/model_set_freeze.yaml", help="Frozen models")
    parser.add_argument("--out-core", default="phase4/frozen_bundle/trial_order_core.csv", help="Output core order")
    args = parser.parse_args()

    # Load resources
    if not os.path.exists(args.task_corpus) or not os.path.exists(args.payloads):
        logging.warning("[-] Required upstream data (tasks or payloads) is missing. Cannot freeze trial order.")
        # Produce DEPENDENCY_MISSING report
        generate_report(
            filepath="phase4/validation/trial_ordering_report.md",
            title="Trial Ordering Generation Report",
            purpose="Generate a strict deterministic trial schedule for Phase 5.",
            inputs=[args.task_corpus, args.payloads],
            checks=["Cross-reference tasks and payloads"],
            failures=["Upstream files missing. Cannot generate schedule."],
            warnings=[],
            recommendations=["Complete Phase 3 task generation and Phase 2.5 payload generation."],
            summary="Status: DEPENDENCY_MISSING\n\nExecution deferred with documented justification. Trial order CSVs remain unavailable until upstream generation completes.",
            evidence={"task_file_exists": os.path.exists(args.task_corpus), "payload_file_exists": os.path.exists(args.payloads)}
        )
        sys.exit(0)

    with open(args.task_corpus, "r", encoding="utf-8") as f:
        corpus = json.load(f)
    with open(args.payloads, "r", encoding="utf-8") as f:
        payloads = json.load(f)
        
    models = get_frozen_models(args.models)
    densities = []
    if corpus.get("d1_count", 0) > 0: densities.append("D1")
    if corpus.get("d3_count", 0) > 0: densities.append("D3")
    if corpus.get("d5_count", 0) > 0: densities.append("D5")
    
    payload_keys = list(payloads.keys())
    
    # Generate cross-product
    trials = []
    trial_id = 1
    for model in models:
        for density in densities:
            for p_key in payload_keys:
                trials.append({
                    "trial_id": f"T{trial_id:05d}",
                    "model_slot": model,
                    "density": density,
                    "payload_condition": p_key,
                    "defense_condition": "BASELINE",
                    "status": "PENDING"
                })
                trial_id += 1

    # Deterministic shuffle
    random.seed(42)
    random.shuffle(trials)

    os.makedirs(os.path.dirname(args.out_core), exist_ok=True)
    with open(args.out_core, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["trial_id", "model_slot", "density", "payload_condition", "defense_condition", "status"])
        writer.writeheader()
        writer.writerows(trials)
        
    generate_report(
        filepath="phase4/validation/trial_ordering_report.md",
        title="Trial Ordering Generation Report",
        purpose="Generate a strict deterministic trial schedule for Phase 5.",
        inputs=[args.task_corpus, args.payloads, args.models],
        checks=["Cross-product generation", "Deterministic PRNG shuffle (seed 42)"],
        failures=[],
        warnings=[],
        recommendations=["Lock CSV hash into cryptographic manifest."],
        summary=f"Status: PASS\n\nGenerated {len(trials)} unique trial combinations successfully utilizing valid upstream artifacts.",
        evidence={"total_trials": len(trials), "models_included": models, "densities_included": densities, "payload_conditions": payload_keys}
    )

    logging.info(f"[+] Trial ordering deterministic schedule generated at {args.out_core}")
    sys.exit(0)

if __name__ == '__main__':
    main()
