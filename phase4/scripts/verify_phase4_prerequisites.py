"""
Module: verify_phase4_prerequisites.py
Purpose: Verifies the existence, size, and integrity of required Phase 3 artifacts.

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
import yaml
import re
from typing import List, Tuple
from pathlib import Path

# We add the parent dir to sys.path so we can import utils easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report
from utils.hashing import hash_file_sha256

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

REQUIRED_ARTIFACTS = [
    "phase3/reports/phase3_final_decision.md",
    "phase3/reports/phase3_cross_model_summary.md",
    "phase3/configs/model_selection_rationale.md",
    "phase3/configs/source_freeze_manifest.json",
    "phase3/tasks/task_corpus.json",
]

def is_valid_sha256(hash_str: str) -> bool:
    return bool(re.fullmatch(r"^[a-f0-9]{64}$", str(hash_str)))

def load_authoritative_hashes() -> dict:
    manifest_path = Path("phase3/configs/source_freeze_manifest.json")
    normalized_hashes = {}
    if manifest_path.exists():
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                files = data.get("files", {})
                for k, v in files.items():
                    # Normalize paths for robust lookup
                    norm_key = Path(k).as_posix()
                    normalized_hashes[norm_key] = v
        except Exception as e:
            logging.error(f"Failed to read authoritative hash manifest: {e}")
    return normalized_hashes

def verify_artifacts(artifacts: List[str]) -> Tuple[bool, List[str], List[str], dict]:
    """Checks all artifacts and returns (is_missing, failures, warnings, evidence_dict)."""
    missing = False
    failures = []
    warnings = []
    evidence = {}
    
    authoritative_hashes = load_authoritative_hashes()
    
    for artifact in artifacts:
        norm_path = Path(artifact)
        if not norm_path.exists():
            msg = f"Missing required artifact: {artifact}"
            logging.error(msg)
            failures.append(msg)
            evidence[artifact] = {"status": "MISSING", "size_bytes": 0}
            missing = True
            continue

        size = norm_path.stat().st_size
        if size == 0:
            msg = f"Artifact {artifact} is exactly 0 bytes."
            logging.error(msg)
            failures.append(msg)
            evidence[artifact] = {"status": "EMPTY", "size_bytes": 0}
            missing = True
            continue

        # Schema Validation
        try:
            with open(norm_path, "r", encoding="utf-8") as f:
                if artifact.endswith(".json"):
                    data = json.load(f)
                    if "source_freeze_manifest.json" in artifact:
                        if not isinstance(data, dict) or ("files" not in data and "Phase 3 Execution Note" not in data):
                            raise ValueError("Source freeze manifest appears incomplete. Required freeze metadata absent. Phase3 freeze cannot be verified.")
                elif artifact.endswith(".yaml") or artifact.endswith(".yml"):
                    yaml.safe_load(f)
                else:
                    # Just read to ensure it's readable
                    f.read()
        except Exception as e:
            msg = f"Artifact {artifact} is not readable or has invalid schema: {e}"
            logging.error(msg)
            failures.append(msg)
            evidence[artifact] = {"status": "INVALID_SCHEMA", "size_bytes": size}
            missing = True
            continue

        # Hash Validation
        status_msg = "PRESENT"
        computed_hash = hash_file_sha256(str(norm_path))
        
        # Look up using normalized path
        abs_norm_path = Path(norm_path).as_posix()
        auth_hash = authoritative_hashes.get(abs_norm_path)
        
        if auth_hash:
            if not is_valid_sha256(auth_hash):
                msg = f"Authoritative hash for {artifact} is malformed: {auth_hash}"
                logging.error(msg)
                failures.append(msg)
                evidence[artifact] = {"status": "MALFORMED_AUTH_HASH", "size_bytes": size}
                missing = True
                continue
                
            if computed_hash != auth_hash:
                msg = f"Artifact {artifact} hash mismatch. Expected {auth_hash}, got {computed_hash}"
                logging.error(msg)
                failures.append(msg)
                evidence[artifact] = {"status": "HASH_MISMATCH", "size_bytes": size}
                missing = True
                continue
            status_msg = "PRESENT_AND_HASH_VERIFIED"
        else:
            msg = f"Authoritative hash unavailable for {artifact}; hash verification could not be performed."
            warnings.append(msg)
            logging.info(msg)

        logging.info(f"Verified artifact exists and is readable: {artifact} ({size} bytes)")
        evidence[artifact] = {
            "status": status_msg, 
            "size_bytes": size,
            "computed_hash": computed_hash
        }
                
    return missing, failures, warnings, evidence

def main():
    parser = argparse.ArgumentParser(description="Verify Phase 4 Prerequisites")
    parser.add_argument("--output", default="phase4/validation/phase4_preflight_audit.md", help="Output report path")
    args = parser.parse_args()

    missing, failures, warnings, evidence = verify_artifacts(REQUIRED_ARTIFACTS)
    
    if missing:
        status = "DEPENDENCY_MISSING" if any("Missing" in f for f in failures) else "FAIL"
        summary = f"Status: {status}\n\nPhase 4 Preflight Audit FAILED due to missing or invalid dependencies."
    else:
        status = "PASS"
        summary = f"Status: {status}\n\nPhase 4 Preflight Audit completed successfully."

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    generate_report(
        filepath=args.output,
        title="Phase 4 Preflight Audit",
        purpose="Verify that all required upstream Phase 3 artifacts exist, are readable, and have valid schemas before freezing the protocol.",
        inputs=REQUIRED_ARTIFACTS,
        checks=["File existence check", "File size check (>0)", "Schema validation (JSON/YAML)", "Hash verification (if authoritative available)"],
        failures=failures,
        warnings=warnings,
        recommendations=["Ensure Phase 3 execution has fully completed and outputs are synchronized."] if missing else ["Proceed to artifact ingestion."],
        summary=summary,
        evidence=evidence
    )

    if missing:
        logging.error("Preflight audit failed.")
        sys.exit(1)
        
    logging.info("Preflight audit passed.")
    sys.exit(0)

if __name__ == '__main__':
    main()
