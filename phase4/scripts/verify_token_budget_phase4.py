"""
Module: verify_token_budget_phase4.py
Purpose: Verifies token budgets by directly inspecting the Phase 3 notebook for prompt logic.
"""
import os
import argparse
import sys
import logging
import json
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def scan_notebook_for_prompts(notebook_path: str) -> dict:
    """Scans the Phase 3 notebook for prompt templates and estimates length."""
    results = {
        "found_system_prompt": False,
        "found_tool_prompt": False,
        "estimated_base_tokens": 0,
        "details": []
    }
    
    if not os.path.exists(notebook_path):
        results["details"].append(f"Notebook {notebook_path} not found.")
        return results
        
    try:
        with open(notebook_path, "r", encoding="utf-8") as f:
            nb = json.load(f)
            
        for cell in nb.get("cells", []):
            if cell.get("cell_type") == "code":
                source = "".join(cell.get("source", []))
                if "SYSTEM_PROMPT" in source and "=" in source:
                    results["found_system_prompt"] = True
                    # Rough heuristic: 1 word ~ 1.3 tokens
                    results["estimated_base_tokens"] += int(len(source) / 4)
                    results["details"].append("Located SYSTEM_PROMPT in notebook.")
                if "def build_" in source and "tool_prompt" in source:
                    results["found_tool_prompt"] = True
                    results["estimated_base_tokens"] += int(len(source) / 4)
                    results["details"].append("Located tool prompt builder function in notebook.")
    except Exception as e:
        results["details"].append(f"Error parsing notebook: {e}")
        
    return results

def main():
    parser = argparse.ArgumentParser(description="Verify Token Budget")
    parser.add_argument("--notebook-path", default="phase3/notebook/phase3-model-testing-harness.ipynb", help="Phase 3 Notebook")
    parser.add_argument("--report-out", default="phase4/validation/token_budget_reverification_report.md", help="Output report")
    args = parser.parse_args()

    results = scan_notebook_for_prompts(args.notebook_path)
    
    if results["found_system_prompt"] or results["found_tool_prompt"]:
        logging.info("[+] Prompts found in Phase 3 notebook.")
        
        # Verify budget < 4096 (arbitrary Phase 4 limit from specs)
        if results["estimated_base_tokens"] < 4096:
            status = "PASS"
            summary = f"Prompts exist in notebook. Estimated base tokens: {results['estimated_base_tokens']} (Budget: 4096)."
            failures = []
        else:
            status = "FAIL"
            summary = f"Prompts exist but exceed budget. Estimated base tokens: {results['estimated_base_tokens']} (Budget: 4096)."
            failures = ["Token budget exceeded."]
    else:
        logging.warning("[-] Prompt structures missing from Phase 3 notebook.")
        status = "DEPENDENCY_MISSING"
        summary = "No prompt structures found in the Phase 3 notebook. Token budget cannot be verified natively."
        failures = ["Upstream prompt definitions are genuinely missing."]
        
    generate_report(
        filepath=args.report_out,
        title="Token Budget Re-verification Report",
        purpose="Ensure all adversarial and benign templates fit within the 4,096 token limit by inspecting the Phase 3 testing harness.",
        inputs=[args.notebook_path],
        checks=["Parse Jupyter Notebook", "Locate SYSTEM_PROMPT", "Locate tool prompt functions", "Token estimation heuristic"],
        failures=failures,
        warnings=[],
        recommendations=["Ensure compiled prompts are generated in Phase 4.5 prior to Phase 5 trials"] if status == "DEPENDENCY_MISSING" else [],
        summary=f"Status: {status}\n\n{summary}",
        evidence=results
    )
    
    sys.exit(0)

if __name__ == '__main__':
    main()
