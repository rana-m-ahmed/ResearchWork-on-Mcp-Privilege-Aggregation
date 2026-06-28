import os
import csv
import json
import random

base_dir = r"d:\research-work\ResearchWork-on-Mcp-Privilege-Aggregation"

models = ["M1", "M2", "M3", "M4"]
densities = ["D1", "D3", "D5"]
surfaces = ["CLEAN_SURFACE", "TD_SURFACE", "CA_SURFACE"]

def load_tasks(density):
    path = os.path.join(base_dir, f"phase3/tasks/benign_tasks_{density.lower()}.jsonl")
    tasks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            tasks.append(json.loads(line))
    return tasks

def build_matrix():
    matrix_rows = []
    trial_index = 0
    
    # Load tasks
    task_pools = {
        "D1": load_tasks("D1"),
        "D3": load_tasks("D3"),
        "D5": load_tasks("D5")
    }
    
    # Generate Warmups (10 per model) -> D1, CLEAN_SURFACE as per prompt 1
    for model in models:
        for i in range(10):
            t = task_pools["D1"][i % len(task_pools["D1"])]
            matrix_rows.append({
                "model_slot": model,
                "trial_index": trial_index,
                "official_trial": False,
                "warmup": True,
                "density": "D1",
                "metadata_surface_condition": "CLEAN_SURFACE",
                "task_id": t["task_id"],
                "task_hash": t["task_hash"],
                "expected_logical_tool_sequence": ",".join(t["expected_sequence"]),
                "accepted_logical_tool_sequences": ",".join(t["expected_sequence"]),
                "randomization_seed": random.randint(1000, 9999)
            })
            trial_index += 1
            
    # Generate Official Trials
    for model in models:
        for density in densities:
            for surface in surfaces:
                # 50 per cell
                for i in range(50):
                    t = task_pools[density][i % len(task_pools[density])]
                    matrix_rows.append({
                        "model_slot": model,
                        "trial_index": trial_index,
                        "official_trial": True,
                        "warmup": False,
                        "density": density,
                        "metadata_surface_condition": surface,
                        "task_id": t["task_id"],
                        "task_hash": t["task_hash"],
                        "expected_logical_tool_sequence": ",".join(t["expected_sequence"]),
                        "accepted_logical_tool_sequences": ",".join(t["expected_sequence"]),
                        "randomization_seed": random.randint(1000, 9999)
                    })
                    trial_index += 1
                    
    # Write full matrix
    fieldnames = [
        "model_slot", "trial_index", "official_trial", "warmup", "density",
        "metadata_surface_condition", "task_id", "task_hash",
        "expected_logical_tool_sequence", "accepted_logical_tool_sequences", "randomization_seed"
    ]
    
    out_dir = os.path.join(base_dir, "phase3/matrices")
    os.makedirs(out_dir, exist_ok=True)
    
    with open(os.path.join(out_dir, "phase3_experimental_matrix.csv"), "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matrix_rows)
        
    # Validation logic inside builder to ensure it fails if bad
    official_count = sum(1 for r in matrix_rows if r["official_trial"])
    if official_count != 1800:
        print(f"FAIL: Matrix validation failed! Expected 1800 official rows, got {official_count}")
        return
        
    for model in models:
        model_rows = [r for r in matrix_rows if r["model_slot"] == model]
        random.shuffle(model_rows)
        with open(os.path.join(out_dir, f"randomized_order_model_{model[-1]}.csv"), "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(model_rows)
            
    print("PASS: Matrix built and validated successfully.")

if __name__ == "__main__":
    build_matrix()
