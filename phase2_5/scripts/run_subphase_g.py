import json
import os
import sys

def main():
    ra_file = "phase2_5/profiling/researcher_a/summary_ra.json"
    rb_file = "phase2_5/profiling/researcher_b/summary_rb.json"
    
    with open(ra_file, "r") as f:
        ra_data = json.load(f)
    with open(rb_file, "r") as f:
        rb_data = json.load(f)
        
    ra_matrix = {item["Condition"]: item for item in ra_data["matrix"]}
    rb_matrix = {item["Condition"]: item for item in rb_data["matrix"]}
    
    reconciled_matrix = []
    log_notes = []
    
    all_ok = True
    max_utilization_pct = 0.0
    max_total_tokens = 0
    
    for cond in ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9"]:
        ra_item = ra_matrix[cond]
        rb_item = rb_matrix[cond]
        
        components = ["SystemTokens", "SchemaTokens", "CapAdvTokens", "PayloadTokens", "TaskTokens", "TotalTokens"]
        
        reconciled_item = {
            "Condition": cond,
            "SchemaFile": ra_item["SchemaFile"],
            "MetadataCondition": ra_item["MetadataCondition"],
        }
        
        for comp in components:
            val_a = ra_item[comp]
            val_b = rb_item[comp]
            diff = abs(val_a - val_b)
            
            if diff <= 3:
                # Auto-round to the higher value to be safe
                reconciled_item[comp] = max(val_a, val_b)
            elif 4 <= diff <= 10:
                log_notes.append(f"REVIEW: Condition {cond} {comp} differed by {diff} (A={val_a}, B={val_b}). Proceeding with max.")
                reconciled_item[comp] = max(val_a, val_b)
            else:
                log_notes.append(f"FATAL DISCREPANCY: Condition {cond} {comp} differed by {diff} (A={val_a}, B={val_b}) which is > 10! Halt triggered.")
                reconciled_item[comp] = max(val_a, val_b) # Keep max for reporting purposes, but will flag failure
                all_ok = False
                
        # Also copy other fields from A
        reconciled_item["ComponentSum"] = sum([reconciled_item[c] for c in components[:-1]])
        reconciled_item["AlignmentDrift"] = reconciled_item["TotalTokens"] - reconciled_item["ComponentSum"]
        
        # Recalculate utilization
        util_pct = (reconciled_item["TotalTokens"] / 3584) * 100
        max_utilization_pct = max(max_utilization_pct, util_pct)
        max_total_tokens = max(max_total_tokens, reconciled_item["TotalTokens"])
        
        reconciled_item["BudgetUtilization"] = f"{util_pct:.1f}%"
        
        if not all_ok:
            reconciled_item["Status"] = "HALT-DISCREPANCY"
        else:
            reconciled_item["Status"] = "SAFE" if reconciled_item["TotalTokens"] <= 2688 else "WARNING" if reconciled_item["TotalTokens"] <= 3225 else "CRITICAL"
            
        reconciled_item["Schema_SHA256"] = ra_item["Schema_SHA256"]
        reconciled_item["Payload_SHA256"] = ra_item["Payload_SHA256"]
        reconciled_item["Prompt_SHA256"] = ra_item["Prompt_SHA256"]
        
        reconciled_matrix.append(reconciled_item)
        
    out_data = {
        "reconciliation_notes": log_notes,
        "max_utilization_pct": max_utilization_pct,
        "max_total_tokens": max_total_tokens,
        "matrix": reconciled_matrix
    }
    
    with open("phase2_5/profiling/reconciled/reconciled_measurements.json", "w") as f:
        json.dump(out_data, f, indent=2)
        
    print("Reconciliation complete. Wrote reconciled_measurements.json")
    
    # Generate reconciliation_log.md
    log_content = [
        "# Phase 2.5 Final Reconciliation Log",
        "",
        "## 1. Reconciliation Scope",
        "Reconciliation between Researcher A artifacts and independent verification by Researcher B for Phase 2.5 token profiling.",
        "",
        "## 2. Researcher Artifact Availability",
        "Researcher A generated artifacts in `phase2_5/profiling/researcher_a/`.",
        "Researcher B generated independent raw execution logs in `phase2_5/profiling/researcher_b/`.",
        "",
        "## 3. Difference Analysis",
    ]
    if log_notes:
        for note in log_notes:
            log_content.append(f"- {note}")
    else:
        log_content.append("- All token counts aligned within <= 3 tolerance.")
        
    log_content.extend([
        "",
        "## 4. Final Status"
    ])
    
    if all_ok:
        log_content.append("PASS - RECONCILED. No differences > 10 tokens observed.")
    else:
        log_content.append("HALT - RECONCILIATION FAILED. Differences > 10 tokens observed between Researcher A and Researcher B. A formal re-profiling pass is required.")
    
    with open("phase2_5/profiling/reconciled/reconciliation_log.md", "w") as f:
        f.write("\n".join(log_content))
        
    print("reconciliation_log.md generated.")

if __name__ == "__main__":
    main()
