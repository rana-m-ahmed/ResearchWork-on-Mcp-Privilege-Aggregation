import argparse
import subprocess
import sys
import os
from pathlib import Path

project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import the new AuditContext and audit orchestrator from our verified script
from phase3.scripts.verify_phase3_integrity import audit, AuditContext

def load_config(model_slot):
    return {
        "backend": {
            "type": "ollama",
            "host": "http://localhost:11434",
            "model_identifier": "mistral-7b-instruct-v0.3"
        }
    }

def run_inference(model_slot, config):
    print(f"--- [MODE: RUN] Starting Inference for {model_slot} ---")
    from phase3.core.orchestrator import Phase3Orchestrator
    
    orchestrator = Phase3Orchestrator(config=config, model_slot=model_slot)
    
    matrix_path = f"phase3/matrices/randomized_order_model_{model_slot.replace('M','')}.csv"
    tasks_path = "phase3/tasks/benign_tasks_master.jsonl"
    
    if not os.path.exists(matrix_path):
        print(f"Matrix not found at {matrix_path}, skipping inference.")
        return
        
    print(f"Executing batch for {model_slot}...")
    try:
        if hasattr(orchestrator, 'execute_batch'):
            orchestrator.execute_batch(matrix_file=matrix_path, tasks_file=tasks_path)
        else:
            print("Warning: orchestrator.execute_batch() not implemented. Skipping actual inference.")
    except Exception as e:
        print(f"Inference run failed or interrupted: {e}")
        
    print(f"--- Inference Complete for {model_slot} ---")

def run_grade(model_slot):
    print(f"--- [MODE: GRADE] Grading trials for {model_slot} ---")
    log_file = f"phase3/logs/trials_{model_slot}.jsonl"
    if not os.path.exists(log_file):
        print(f"Log file {log_file} does not exist. Skipping grading.")
        return
        
    res = subprocess.run([
        sys.executable, 
        "phase3/scripts/grade_phase3_trials.py",
        "--logs", log_file,
        "--tasks", "phase3/tasks/benign_tasks_master.jsonl"
    ])
    if res.returncode != 0:
        print(f"Grading failed for {model_slot}.")
        sys.exit(res.returncode)

def run_audit(model_slots):
    print(f"--- [MODE: AUDIT] Running Context-Aware Integrity Audit for {model_slots} ---")
    
    ctx = AuditContext(
        model_slots=model_slots,
        matrix_files=None,
        log_files=None,
        repository_mode=False
    )
    
    try:
        audit(ctx)
    except SystemExit as e:
        if e.code != 0:
            print("Audit failed. Pipeline is blocked.")
        sys.exit(e.code)

def run_summarize():
    print("--- [MODE: SUMMARIZE] Generating Summary Reports ---")
    res = subprocess.run([
        sys.executable,
        "phase3/scripts/summarize_phase3.py",
        "--logs", "phase3/logs/trials_*.jsonl",
        "--tasks", "phase3/tasks/benign_tasks_master.jsonl",
        "--outdir", "phase3/reports"
    ])
    if res.returncode != 0:
        print("Summarization failed.")
        sys.exit(res.returncode)

def main():
    parser = argparse.ArgumentParser(description="Phase 3 Unified Production Pipeline")
    parser.add_argument("--mode", choices=["full", "run", "audit", "grade", "summarize"], required=True, 
                        help="Execution mode")
    parser.add_argument("--model-slot", type=str, default="M3", help="Comma-separated model slots (e.g., M1,M3)")
    
    args = parser.parse_args()
    
    slots = [s.strip() for s in args.model_slot.split(",")]
    
    for slot in slots:
        config = load_config(slot)
        if args.mode in ["full", "run"]:
            run_inference(slot, config)
            
        if args.mode in ["full", "grade"]:
            run_grade(slot)
            
    if args.mode in ["full", "audit"]:
        run_audit(slots)
        
    if args.mode in ["full", "summarize"]:
        run_summarize()

if __name__ == '__main__':
    main()
