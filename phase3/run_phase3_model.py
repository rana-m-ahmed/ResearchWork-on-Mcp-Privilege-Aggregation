import argparse
import subprocess
import sys
import os
from pathlib import Path

project_root = str(Path(__file__).parent.parent.absolute())
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from phase3.scripts.verify_phase3_integrity import audit, AuditContext


# ==========================================================
# MODEL CONFIGURATION
# ==========================================================

MODEL_MAP = {
    "M1": "Qwen/Qwen2.5-7B-Instruct",
    "M2": "meta-llama/Llama-3.1-8B-Instruct",
    "M3": "mistralai/Mistral-7B-Instruct-v0.3",
    "M4": "google/gemma-2-9b-it",
}


def load_config(model_slot):
    if model_slot not in MODEL_MAP:
        raise ValueError(f"Unknown model slot: {model_slot}")

    return {
        "backend": {
            "type": "transformers",
            "model_identifier": MODEL_MAP[model_slot]
        }
    }


# ==========================================================
# RUN INFERENCE
# ==========================================================

def run_inference(model_slot, config):

    print(f"\n{'='*70}")
    print(f"Starting inference for {model_slot}")
    print(f"Model: {config['backend']['model_identifier']}")
    print(f"{'='*70}")

    from phase3.core.orchestrator import Phase3Orchestrator

    orchestrator = Phase3Orchestrator(
        config=config,
        model_slot=model_slot
    )

    matrix_path = (
        f"phase3/matrices/randomized_order_model_"
        f"{model_slot.replace('M','')}.csv"
    )

    tasks_path = "phase3/tasks/benign_tasks_master.jsonl"

    if not os.path.exists(matrix_path):
        print(f"Matrix missing: {matrix_path}")
        return

    if not os.path.exists(tasks_path):
        print(f"Task file missing: {tasks_path}")
        return

    try:

        status = orchestrator.execute_batch(
            matrix_file=matrix_path,
            tasks_file=tasks_path
        )

        print("\nExecution finished.")
        print(f"Trials run: {status.total_trials_run}")
        print(f"Valid trials: {status.valid_trials_completed}")
        print(f"Interrupted: {status.interrupted}")

    except Exception as e:

        print("\nInference failed.")
        print(e)

    print(f"Finished {model_slot}\n")


# ==========================================================
# GRADING
# ==========================================================

def run_grade(model_slot):

    print(f"\nGrading {model_slot}")

    log_file = f"phase3/logs/trials_{model_slot}.jsonl"

    if not os.path.exists(log_file):
        print("Log file not found.")
        return

    res = subprocess.run([
        sys.executable,
        "phase3/scripts/grade_phase3_trials.py",
        "--logs",
        log_file,
        "--tasks",
        "phase3/tasks/benign_tasks_master.jsonl"
    ])

    if res.returncode != 0:
        print("Grading failed.")
        sys.exit(res.returncode)


# ==========================================================
# AUDIT
# ==========================================================

def run_audit(model_slots):

    print("\nRunning integrity audit...")

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
            print("Audit failed.")

        sys.exit(e.code)


# ==========================================================
# SUMMARY
# ==========================================================

def run_summarize():

    print("\nGenerating reports...")

    res = subprocess.run([
        sys.executable,
        "phase3/scripts/summarize_phase3.py",
        "--logs",
        "phase3/logs/trials_*.jsonl",
        "--tasks",
        "phase3/tasks/benign_tasks_master.jsonl",
        "--outdir",
        "phase3/reports"
    ])

    if res.returncode != 0:
        print("Summary generation failed.")
        sys.exit(res.returncode)


# ==========================================================
# MAIN
# ==========================================================

def main():

    parser = argparse.ArgumentParser(
        description="Phase 3 Unified Pipeline"
    )

    parser.add_argument(
        "--mode",
        required=True,
        choices=[
            "full",
            "run",
            "grade",
            "audit",
            "summarize"
        ]
    )

    parser.add_argument(
        "--model-slot",
        default="M1",
        help="Examples: M1 or M1,M2,M3,M4"
    )

    args = parser.parse_args()

    slots = [
        s.strip()
        for s in args.model_slot.split(",")
    ]

    for slot in slots:

        if slot not in MODEL_MAP:
            raise ValueError(f"Unknown slot: {slot}")

        config = load_config(slot)

        if args.mode in ("run", "full"):
            run_inference(slot, config)

        if args.mode in ("grade", "full"):
            run_grade(slot)

    if args.mode in ("audit", "full"):
        run_audit(slots)

    if args.mode in ("summarize", "full"):
        run_summarize()


if __name__ == "__main__":
    main()