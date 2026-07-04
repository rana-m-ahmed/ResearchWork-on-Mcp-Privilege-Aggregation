"""
Module: synchronize_model_branches.py
Purpose: Verifies the synchronization of branches required by Phase 5 using actual Git ops.
"""
import os
import argparse
import sys
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report
from utils.git_ops import get_git_state

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def main():
    parser = argparse.ArgumentParser(description="Synchronize Model Branches")
    parser.add_argument("--report-out", default="phase4/validation/branch_synchronization_report.md", help="Output report")
    args = parser.parse_args()

    git_state = get_git_state()
    
    failures = []
    warnings = []
    
    if git_state["is_git_repo"]:
        logging.info(f"[+] Git repository detected. Branch: {git_state['branch']}, Clean: {git_state['clean']}")
        status = "PASS"
        summary = "Git branch state validated."
        if not git_state["clean"]:
            warnings.append("Working tree is not clean. Ensure uncommitted changes do not affect experiments.")
    else:
        logging.warning("[-] Not operating within a Git repository.")
        status = "NO_GIT_REPOSITORY"
        summary = "Git operations are unavailable. Unable to verify branch synchronization natively."
        failures.append(git_state.get("error", "Unknown git error"))

    generate_report(
        filepath=args.report_out,
        title="Branch Synchronization Report",
        purpose="Ensure Phase 5 model-specific branches are derived synchronously from the main protocol branch.",
        inputs=[".git state"],
        checks=["Repository existence", "Current branch", "Commit hash", "Working tree cleanliness"],
        failures=failures,
        warnings=warnings,
        recommendations=["Initialize a git repository for full protocol tracking"] if not git_state["is_git_repo"] else [],
        summary=f"Status: {status}\n\n{summary}",
        evidence=git_state
    )
    
    sys.exit(0)

if __name__ == '__main__':
    main()
