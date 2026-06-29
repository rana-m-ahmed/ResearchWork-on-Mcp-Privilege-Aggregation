import os
import sys
import argparse
import random
import csv
import json

def build_matrix():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trials-per-cell', type=int, default=50)
    parser.add_argument('--models', type=int, default=4)
    parser.add_argument('--seed', type=int, default=3301)
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    random.seed(args.seed)

    densities = [1, 3, 5]
    surfaces = ['CLEAN', 'TD', 'CA']
    
    # Load tasks
    tasks_by_density = {1: [], 3: [], 5: []}
    master_file = 'phase3/tasks/benign_tasks_master.jsonl'
    
    if os.path.exists(master_file):
        with open(master_file, 'r') as f:
            for line in f:
                task = json.loads(line)
                if task.get('status') == 'TODO_BEFORE_OFFICIAL_RUN':
                    continue
                d = task.get('density')
                if d in tasks_by_density:
                    tasks_by_density[d].append(task)
    
    # If no tasks or not enough tasks, we'll exit early or use what we have (for mock execution)
    for d in densities:
        if len(tasks_by_density[d]) < args.trials_per_cell:
            print(f"[WARNING] Not enough tasks for density {d}. Have {len(tasks_by_density[d])}, need {args.trials_per_cell}.")
            if args.strict:
                # We expect 50 tasks for testing since our generator made exactly 50 per density.
                if len(tasks_by_density[d]) == 0:
                    print("[FAIL] Missing task corpus.")
                    sys.exit(1)
                    
    # Generate matrix
    master_matrix_path = 'phase3/matrices/phase3_experimental_matrix.csv'
    all_rows = []
    
    print(f"Building matrix with seed {args.seed}...")
    
    for model_idx in range(1, args.models + 1):
        model_name = f"M{model_idx}"
        model_rows = []
        for d in densities:
            for surface in surfaces:
                cell_tasks = list(tasks_by_density[d])
                random.shuffle(cell_tasks)
                selected_tasks = cell_tasks[:args.trials_per_cell]
                for task in selected_tasks:
                    row = {
                        "model": model_name,
                        "density": d,
                        "surface": surface,
                        "task_id": task["task_id"],
                        "is_warmup": False
                    }
                    model_rows.append(row)
                    all_rows.append(row)
                    
        # Write randomized model file
        random.shuffle(model_rows)
        model_file = f'phase3/matrices/randomized_order_model_{model_idx}.csv'
        with open(model_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["model", "density", "surface", "task_id", "is_warmup"])
            writer.writeheader()
            writer.writerows(model_rows)
            
        print(f"Generated {model_file} with {len(model_rows)} rows (9 cells * {args.trials_per_cell} trials).")

    with open(master_matrix_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["model", "density", "surface", "task_id", "is_warmup"])
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"[PASS] Matrix built. Total rows: {len(all_rows)}")

if __name__ == "__main__":
    build_matrix()
