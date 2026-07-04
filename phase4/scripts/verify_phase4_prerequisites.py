"""
Module: verify_phase4_prerequisites.py
Purpose: Verifies the existence, size, and integrity of required Phase 3 artifacts.
"""
import os
import sys
import argparse
import logging
from typing import List, Tuple

# We add the parent dir to sys.path so we can import utils easily
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

REQUIRED_ARTIFACTS = [
    "phase3/reports/phase3_final_decision.md",
    "phase3/reports/phase3_cross_model_summary.md",
    "phase3/configs/model_selection_rationale.md",
    "phase3/configs/source_freeze_manifest.json",
    "phase3/tasks/task_corpus.json",
]

def verify_artifacts(artifacts: List[str]) -> Tuple[bool, List[str], List[str], dict]:
    """Checks all artifacts and returns (is_missing, failures, warnings, evidence_dict)."""
    missing = False
    failures = []
    warnings = []
    evidence = {}
    
    for artifact in artifacts:
        # Cross platform path mapping
        norm_path = artifact.replace('/', os.sep)
        if not os.path.exists(norm_path):
            msg = f"Missing required artifact: {artifact}"
            logging.error(msg)
            failures.append(msg)
            evidence[artifact] = {"status": "MISSING", "size_bytes": 0}
            missing = True
        else:
            size = os.path.getsize(norm_path)
            logging.info(f"Verified artifact exists: {artifact} ({size} bytes)")
            evidence[artifact] = {"status": "PRESENT", "size_bytes": size}
            if size == 0:
                warnings.append(f"Artifact {artifact} is exactly 0 bytes.")
                
    return missing, failures, warnings, evidence

def main():
    parser = argparse.ArgumentParser(description="Verify Phase 4 Prerequisites")
    parser.add_argument("--output", default="phase4/validation/phase4_preflight_audit.md", help="Output report path")
    args = parser.parse_args()

    missing, failures, warnings, evidence = verify_artifacts(REQUIRED_ARTIFACTS)
    
    summary = "Phase 4 Preflight Audit completed successfully."
    if missing:
        summary = "Phase 4 Preflight Audit FAILED due to missing dependencies."

    generate_report(
        filepath=args.output,
        title="Phase 4 Preflight Audit",
        purpose="Verify that all required upstream Phase 3 artifacts exist before freezing the protocol.",
        inputs=REQUIRED_ARTIFACTS,
        checks=["File existence check", "File size check"],
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
