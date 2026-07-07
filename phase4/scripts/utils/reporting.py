"""
Module: reporting.py
Purpose: Reusable markdown report generation.
"""
import os
import datetime
from typing import Dict, List, Any

def generate_report(
    filepath: str, 
    title: str, 
    purpose: str, 
    inputs: List[str], 
    checks: List[str], 
    failures: List[str], 
    warnings: List[str], 
    recommendations: List[str], 
    summary: str,
    evidence: Dict[str, Any]
):
    """Generates a highly structured, evidence-backed Markdown report."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # For now, default software version to 1.0.0
    software_version = "1.0.0"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"**Timestamp (UTC):** {timestamp}\n")
        f.write(f"**Software Version:** {software_version}\n\n")
        
        f.write("## Purpose\n")
        f.write(f"{purpose}\n\n")
        
        f.write("## Inputs Evaluated\n")
        if not inputs:
            f.write("- None\n")
        for i in inputs:
            f.write(f"- {i}\n")
        f.write("\n")
        
        f.write("## Checks Performed\n")
        if not checks:
            f.write("- None\n")
        for c in checks:
            f.write(f"- {c}\n")
        f.write("\n")
        
        f.write("## Summary\n")
        f.write(f"{summary}\n\n")
        
        f.write("## Failures\n")
        if not failures:
            f.write("No failures detected.\n")
        else:
            for fail in failures:
                f.write(f"- **FAIL**: {fail}\n")
        f.write("\n")
        
        f.write("## Warnings\n")
        if not warnings:
            f.write("No warnings detected.\n")
        else:
            for warn in warnings:
                f.write(f"- **WARNING**: {warn}\n")
        f.write("\n")
        
        f.write("## Recommendations\n")
        if not recommendations:
            f.write("- None\n")
        else:
            for rec in recommendations:
                f.write(f"- {rec}\n")
        f.write("\n")
        
        f.write("## Evidence Log\n")
        f.write("```json\n")
        import json
        f.write(json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False))
        f.write("\n```\n")
