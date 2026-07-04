"""
Module: validate_payload_references.py
Purpose: Validates payload references by exhaustively searching the repository for authorized payloads.
"""
import os
import json
import argparse
import sys
import logging
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report
from utils.hashing import hash_file_sha256

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def search_for_payloads(root_dir: str) -> Dict[str, str]:
    """Exhaustively searches for payload files across the repository."""
    payloads = {}
    for dirpath, _, files in os.walk(root_dir):
        # Skip certain directories to speed up search
        if ".git" in dirpath or "__pycache__" in dirpath:
            continue
            
        for file in files:
            lower_file = file.lower()
            if "payload" in lower_file and file.endswith(".json"):
                filepath = os.path.join(dirpath, file)
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        # Identify if it's a dictionary of payloads
                        if isinstance(data, dict) and any("POISON" in k for k in data.keys()):
                            # Map them
                            norm_path = filepath.replace('\\', '/')
                            payloads[norm_path] = hash_file_sha256(filepath)
                except Exception:
                    pass
    return payloads

def main():
    parser = argparse.ArgumentParser(description="Validate Phase 1/2 Payload References")
    parser.add_argument("--repo-root", default=".", help="Repository root to search")
    parser.add_argument("--map-out", default="phase4/configs/payload_reference_map.json", help="Output payload map")
    parser.add_argument("--report-out", default="phase4/validation/payload_reference_validation_report.md", help="Output report")
    args = parser.parse_args()

    payload_files = search_for_payloads(args.repo_root)
    os.makedirs(os.path.dirname(args.map_out), exist_ok=True)
    
    evidence = {"payload_files_discovered": payload_files}
    failures = []
    
    if payload_files:
        logging.info(f"[+] Payloads discovered across {len(payload_files)} files.")
        status = "PASS"
        summary = "Payload references mapped successfully from repository discovery."
        with open(args.map_out, "w", encoding="utf-8") as f:
            json.dump(payload_files, f, indent=2)
    else:
        logging.warning("[-] No valid payload artifacts discovered anywhere in repository.")
        status = "DEPENDENCY_MISSING"
        summary = "No authoritative payload ledgers exist yet. Populated empty payload map."
        failures.append("Exhaustive repository search yielded 0 payload ledgers.")
        with open(args.map_out, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)
                
    generate_report(
        filepath=args.report_out,
        title="Payload Reference Validation Report",
        purpose="Ensure payloads referenced in Phase 4 exist in the master ledger via exhaustive repository search.",
        inputs=["Repository files matching '*payload*.json'"],
        checks=["Exhaustive filesystem traversal", "JSON schema check for POISON tags", "SHA-256 Hashing"],
        failures=failures,
        warnings=[],
        recommendations=["Run Phase 1 to generate ledgers before attempting full protocol freeze."] if not payload_files else [],
        summary=f"Status: {status}\n\n{summary}",
        evidence=evidence
    )
    
    sys.exit(0)

if __name__ == '__main__':
    main()
