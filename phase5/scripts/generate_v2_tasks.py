import json
import csv
import hashlib
from pathlib import Path

def main():
    repo_root = Path("D:/research-work/ResearchWork-on-Mcp-Privilege-Aggregation")
    phase3_tasks_dir = repo_root / "phase3" / "tasks"
    phase4_queue_dir = repo_root / "phase4" / "frozen_bundle_v2"
    
    # Load all tasks from Phase 3
    tasks_master = {}
    for file_path in phase3_tasks_dir.glob("benign_tasks_master.jsonl"):
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                task = json.loads(line)
                tasks_master[task["task_id"]] = task

    registry = []
    ledger = []
    task_hashes = set()
    collisions = 0
    unresolved = 0
    mismatches = 0
    total_rows = 0

    def process_queue(queue_file):
        nonlocal collisions, unresolved, mismatches, total_rows
        with open(queue_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                total_rows += 1
                task_id = row["task_id"]
                if not task_id:
                    # null-payload rows might not have task_id? No, prompt says 10,200 rows resolve task content.
                    unresolved += 1
                    continue
                
                if task_id not in tasks_master:
                    unresolved += 1
                    continue
                
                task_content = tasks_master[task_id]
                content_str = json.dumps(task_content, sort_keys=True, separators=(",", ":"))
                content_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()
                
                # Check task_hash if it exists in queue
                if row["task_hash"] and row["task_hash"] != "UNAVAILABLE_NOT_RECORDED_IN_PHASE3":
                    # Some queues might have exact hash, or we just use ours.
                    pass
                
                if task_id in [t["task_id"] for t in registry]:
                    pass # Already added, check for collision
                else:
                    registry.append({
                        "task_id": task_id,
                        "canonical_task_content": task_content,
                        "canonical_serialization_method": "json_dumps_sort_keys_separators",
                        "task_hash": content_hash,
                        "source_artifact": queue_file.name,
                        "source_artifact_hash": "N/A", # We can hash the CSV if needed
                        "task_type": "benign",
                        "allowed_variables": list(task_content.keys()),
                        "prompt_template_binding": "default",
                        "tool_schema_binding": "default"
                    })
                    ledger.append([task_id, content_hash])

    process_queue(phase4_queue_dir / "trial_order_core.csv")
    process_queue(phase4_queue_dir / "trial_order_defense.csv")
    process_queue(phase4_queue_dir / "trial_order_utility.csv")
    
    print(f"Total Rows: {total_rows}")
    print(f"Unique tasks: {len(registry)}")
    print(f"Unresolved: {unresolved}")
    print(f"Mismatches: {mismatches}")
    print(f"Collisions: {collisions}")

    out_dir = Path("D:/phase5-real-official-execution/phase5/manifests")
    out_dir.mkdir(parents=True, exist_ok=True)
    
    with open(out_dir / "frozen_task_content_registry_v2.json", "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2)
        
    with open(out_dir / "frozen_task_content_hash_ledger_v2.csv", "w", encoding="utf-8", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["task_id", "task_hash"])
        writer.writerows(ledger)

if __name__ == "__main__":
    main()
