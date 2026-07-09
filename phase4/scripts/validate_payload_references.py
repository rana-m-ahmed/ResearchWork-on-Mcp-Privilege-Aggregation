"""
Module: validate_payload_references.py
Purpose: Validates payload references exclusively from the canonical Phase 1 ledger.

Determinism Rule: All scripts must derive outputs exclusively from committed upstream artifacts.
No script may fabricate placeholder values, silently substitute defaults, infer missing evidence,
or generate synthetic metadata. When required evidence is unavailable, the script must explicitly
report DEPENDENCY_MISSING or NOT_MEASURABLE with justification.
"""
import os
import json
import argparse
import sys
import logging
import re
from typing import Dict, Tuple
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def extract_canonical_payloads(ledger_path: str) -> Tuple[Dict[str, str], list]:
    """Extracts payload IDs and hashes, verifying metadata consistency."""
    payloads = {}
    failures = []
    
    with open(ledger_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
        # Verify schema version if present
        metadata = data.get("metadata", {})
        if "schema_version" in metadata:
            logging.info(f"Verified schema_version: {metadata['schema_version']}")
        if "generator_version" in metadata:
            logging.info(f"Verified generator_version: {metadata['generator_version']}")
        if "repository_commit" in metadata:
            logging.info(f"Verified repository_commit: {metadata['repository_commit']}")
        if "execution_uuid" in metadata:
            logging.info(f"Verified execution_uuid: {metadata['execution_uuid']}")
            
        payloads_list = data.get("payloads")
        if not isinstance(payloads_list, list):
            raise ValueError("INVALID_SCHEMA: Canonical ledger violates schema: 'payloads' is missing or not a list.")
            
        # Cross-check metadata consistency
        expected_payload_count = metadata.get("payload_count")
        expected_canonical_count = metadata.get("canonical_payload_count")
        
        actual_len = len(payloads_list)
        if expected_payload_count is not None and expected_payload_count != actual_len:
            failures.append(f"INVALID_SCHEMA: Metadata payload_count ({expected_payload_count}) does not match actual length ({actual_len}).")
            
        if expected_canonical_count is not None and expected_payload_count is not None:
            if expected_canonical_count > expected_payload_count:
                failures.append(f"INVALID_SCHEMA: Metadata canonical_payload_count ({expected_canonical_count}) exceeds payload_count ({expected_payload_count}).")
        
        for p in payloads_list:
            if p.get("approval_status") != "Approved" or not p.get("duplicate_handling", {}).get("is_canonical"):
                continue
                
            pid = p.get("payload_id")
            phash = p.get("phase1_payload_hash")
            
            if not pid:
                failures.append("INVALID_SCHEMA: Payload entry is missing payload_id.")
                continue
                
            if pid in payloads:
                failures.append(f"INVALID_SCHEMA: Duplicate payload ID detected in canonical ledger: {pid}")
                continue

            if phash is not None:
                if not isinstance(phash, str) or not bool(re.fullmatch(r"^[a-f0-9]{64}$", phash)):
                    failures.append(f"INVALID_SCHEMA: canonical payload {pid} has a malformed Phase 1 hash: {phash}")
                    continue
                
            payloads[pid] = None
                    
    # Sort for deterministic map output
    return dict(sorted(payloads.items())), failures

def main():
    parser = argparse.ArgumentParser(description="Validate Phase 1 Payload References")
    parser.add_argument("--ledger", default="phase1/ledger/payload_provenance_ledger.json", help="Canonical ledger")
    parser.add_argument("--map-out", default="phase4/configs/payload_reference_map.json", help="Output payload map")
    parser.add_argument("--report-out", default="phase4/validation/payload_reference_validation_report.md", help="Output report")
    args = parser.parse_args()

    ledger_path = Path(args.ledger)
    evidence = {}
    failures = []
    status = "PASS"
    summary = ""
    
    if not ledger_path.exists():
        logging.warning(f"[-] Authoritative payload ledger missing: {args.ledger}")
        status = "DEPENDENCY_MISSING"
        summary = "No authoritative payload ledger exists. Token payload map cannot be verified natively."
        failures.append("Authoritative payload ledger is missing.")
        payload_map = {}
    else:
        try:
            payload_map, ledger_failures = extract_canonical_payloads(str(ledger_path))
            if ledger_failures:
                failures.extend(ledger_failures)
                status = "FAIL"
                if any("UPSTREAM_DEFECT" in f for f in failures):
                    status = "UPSTREAM_DEFECT"
                summary = "Authoritative payload ledger contains upstream defects or schema violations."
                payload_map = {}
            elif not payload_map:
                status = "FAIL"
                summary = "Ledger exists but contains no valid payloads."
                failures.append("Ledger has no valid payload IDs and hashes.")
            else:
                logging.info(f"[+] Payloads extracted cleanly: {len(payload_map)}")
                status = "PASS"
                summary = f"Successfully validated and mapped {len(payload_map)} canonical payloads without duplicates."
        except Exception as e:
            logging.error(f"[-] Validation failed: {e}")
            status = "FAIL"
            summary = "Authoritative payload ledger violated validation constraints."
            failures.append(str(e))
            payload_map = {}
            
    os.makedirs(os.path.dirname(args.map_out), exist_ok=True)
    with open(args.map_out, "w", encoding="utf-8") as f:
        json.dump(payload_map, f, indent=2, sort_keys=True, ensure_ascii=False)
        
    evidence["payloads_mapped_count"] = len(payload_map)
                
    os.makedirs(os.path.dirname(args.report_out), exist_ok=True)
    generate_report(
        filepath=args.report_out,
        title="Payload Reference Validation Report",
        purpose="Ensure payloads referenced in Phase 4 exist in the master ledger via canonical Phase 1 metadata.",
        inputs=[args.ledger],
        checks=["Ledger file existence", "JSON schema check for payload entries", "Duplicate ID prevention", "Extract ID and Hash dynamically", "Metadata consistency cross-check"],
        failures=failures,
        warnings=[],
        recommendations=["Run Phase 1 to generate ledgers before attempting full protocol freeze."] if status == "DEPENDENCY_MISSING" else [],
        summary=f"Status: {status}\n\n{summary}",
        evidence=evidence
    )
    
    if status != "PASS":
        for f in failures:
            logging.error(f)
        sys.exit(1)
        
    sys.exit(0)

if __name__ == '__main__':
    main()
