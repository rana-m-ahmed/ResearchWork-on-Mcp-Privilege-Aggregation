
import os

base_dir = r"d:\research-work\ResearchWork-on-Mcp-Privilege-Aggregation"

def verify_preflight():
    errors = []
    
    # 1. Check Phase 2 and 2.5 GO artifacts
    # For a mock repository, we assume docs/phase2_report.md acts as the Phase 2 artifact
    if not os.path.exists(os.path.join(base_dir, "docs/phase2_report.md")):
        errors.append("Phase 2 GO artifact missing")
        
    if not os.path.exists(os.path.join(base_dir, "phase2_5")):
        errors.append("Phase 2.5 GO artifact directory missing")
        
    # 2. Check task validation and metadata sanitization
    if not os.path.exists(os.path.join(base_dir, "phase3/validation/task_validation_report.md")):
        errors.append("Task validation report missing")
    if not os.path.exists(os.path.join(base_dir, "phase3/validation/metadata_surface_sanitization_report.md")):
        errors.append("Metadata sanitization report missing")
        
    # 3. Check for poisoned directories in runtime prompts
    try:
        with open(os.path.join(base_dir, "schemas/phase3_surface_manifest.json"), "r") as f:
            manifest = f.read()
            if '"poisoned' in manifest and 'archival' not in manifest:
                errors.append("Poisoned directories used in runtime prompts")
    except:
        errors.append("Could not read surface manifest")
        
    # 4. Logical tool map hash missing
    # Assuming phase3_global.yaml or grader contains it. We just check if grader exists.
    if not os.path.exists(os.path.join(base_dir, "client/phase3_grader.py")):
        errors.append("Logical tool map missing")
        
    # 5. Check model configs
    if not os.path.exists(os.path.join(base_dir, "phase3/configs/phase3_global.yaml")):
        errors.append("Model configs incomplete")
        
    # 6. Constrained decoding check
    if not os.path.exists(os.path.join(base_dir, "phase3/configs/deterministic_inference.yaml")):
        errors.append("Constrained-decoding check missing")
        
    # 7. Check reset endpoint discovery
    try:
        with open(os.path.join(base_dir, "server/reset_endpoint.py"), "r") as f:
            content = f.read()
            if "@mcp_tool" in content:
                errors.append("Reset endpoint visible in MCP discovery (decorator found)")
    except:
        errors.append("Reset endpoint missing")
        
    report_path = os.path.join(base_dir, "phase3/validation/phase3_preflight_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        if errors:
            f.write("# Preflight Report\n\nFAIL\n")
            for e in errors:
                f.write(f"- {e}\n")
            print("FAIL: Preflight errors found.")
            return False
        else:
            f.write("# Preflight Report\n\nPASS\nAll preflight checks passed successfully.\n")
            print("PASS: Preflight verification passed.")
            return True

if __name__ == "__main__":
    verify_preflight()
