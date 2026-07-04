"""
Module: lint_phase4_forbidden_claims.py
Purpose: Scans generated markdown reports to ensure no unscientific or forbidden claims exist prior to Phase 5 execution.
"""
import os
import sys
import argparse
import logging
from typing import List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

FORBIDDEN_CLAIMS = [
    "vulnerability proven",
    "robustness proven",
    "attack success established",
    "defense effective",
    "critical exploit discovered",
    "MCP is insecure",
    "model is safe",
    "model is secure",
    "proven",
    "confirmed vulnerability",
    "secure",
    "safe",
    "effective",
    "robust",
    "guaranteed",
    "successful attack"
]

def lint_markdown(dirs: List[str]) -> bool:
    found = False
    for d in dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith(".md"):
                    filepath = os.path.join(root, file)
                    with open(filepath, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                        for claim in FORBIDDEN_CLAIMS:
                            if claim.lower() in content:
                                logging.error(f"Forbidden claim '{claim}' found in {filepath}")
                                found = True
    return found

def main():
    parser = argparse.ArgumentParser(description="Lint Phase 4 Markdown for Forbidden Claims")
    parser.add_argument("--targets", nargs="+", default=["phase4/reports", "phase4/validation", "phase4_5"], help="Directories to lint")
    args = parser.parse_args()

    logging.info(f"[*] Linting {args.targets} for forbidden claims...")
    has_forbidden = lint_markdown(args.targets)
    
    if has_forbidden:
        logging.error("Linter failed: Forbidden claims detected.")
        sys.exit(1)
    else:
        logging.info("[+] No forbidden claims found. Terminology is clean.")
        sys.exit(0)

if __name__ == '__main__':
    main()
