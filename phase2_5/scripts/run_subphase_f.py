import json

def main():
    # Load reconciled data
    with open("phase2_5/profiling/reconciled/reconciled_measurements.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    matrix = {item["Condition"]: item for item in data["matrix"]}
    
    # D1 = C1, C2, C3
    # D3 = C4, C5, C6
    # D5 = C7, C8, C9
    
    # We'll use CLEAN conditions for schema size growth since schema size mostly depends on D-level, though poison adds capabilities.
    # The prompt doesn't specify, but looking at the data:
    d1_clean = matrix["C1"]["SchemaTokens"]
    d3_clean = matrix["C4"]["SchemaTokens"]
    d5_clean = matrix["C7"]["SchemaTokens"]
    
    d1_td = matrix["C2"]["SchemaTokens"]
    d3_td = matrix["C5"]["SchemaTokens"]
    d5_td = matrix["C8"]["SchemaTokens"]

    d1_ca = matrix["C3"]["SchemaTokens"]
    d3_ca = matrix["C6"]["SchemaTokens"]
    d5_ca = matrix["C9"]["SchemaTokens"]

    report = [
        "# Phase 2.5 Schema Growth Analysis",
        "",
        "## Table 16.3: Schema Growth Deltas",
        "| Condition | D1 Tokens | D3 Tokens | D5 Tokens | D1->D3 \u0394 | D3->D5 \u0394 | D1->D5 \u0394 |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| CLEAN | {d1_clean} | {d3_clean} | {d5_clean} | {d3_clean - d1_clean} | {d5_clean - d3_clean} | {d5_clean - d1_clean} |",
        f"| POISON-TD | {d1_td} | {d3_td} | {d5_td} | {d3_td - d1_td} | {d5_td - d3_td} | {d5_td - d1_td} |",
        f"| POISON-CA | {d1_ca} | {d3_ca} | {d5_ca} | {d3_ca - d1_ca} | {d5_ca - d3_ca} | {d5_ca - d1_ca} |"
    ]
    
    with open("phase2_5/reports/Schema_Growth_Analysis.md", "w", encoding="utf-8") as f:
        f.write("\n".join(report))
        
    print("Schema Growth Analysis generated.")

if __name__ == "__main__":
    main()
