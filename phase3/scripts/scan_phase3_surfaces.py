import os
import json

base_dir = r"d:\research-work\ResearchWork-on-Mcp-Privilege-Aggregation"

def scan_surfaces():
    surfaces = [
        "schemas/clean/schema.json",
        "schemas/phase3_surface/td_surface/schema.json",
        "schemas/phase3_surface/ca_surface/schema.json"
    ]
    
    banned_strings = [
        "phase1_payload",
        "payload",
        "override",
        "exfiltrate",
        "ignore previous",
        "hidden",
        "malicious",
        "benchmark attack",
        "attack success",
        "five-state"
    ]
    
    report_lines = ["# Metadata Surface Sanitization Report\n"]
    all_passed = True
    
    for s in surfaces:
        path = os.path.join(base_dir, s)
        if not os.path.exists(path):
            report_lines.append(f"FAIL: {s} does not exist.")
            all_passed = False
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().lower()
            
        failed = False
        for ban in banned_strings:
            if ban in content:
                report_lines.append(f"FAIL: {s} contains banned string: {ban}")
                failed = True
                all_passed = False
                
        if not failed:
            report_lines.append(f"PASS: {s} is clean.")
            
    report_path = os.path.join(base_dir, "phase3/validation/metadata_surface_sanitization_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines))
        
    if all_passed:
        print("PASS: Surface scanning completed successfully. No adversarial material found.")
    else:
        print("FAIL: Surface scanning found adversarial material or missing files.")

if __name__ == "__main__":
    scan_surfaces()
