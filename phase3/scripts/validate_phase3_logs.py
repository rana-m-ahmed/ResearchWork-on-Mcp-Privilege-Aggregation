
import os
import json
import argparse

def validate_logs(dry_run=False, model=None):
    base_dir = os.environ.get("BASE_DIR", ".")
    log_path = os.path.join(base_dir, f"phase3/runs/{model}/run_001/trials.jsonl") if model else os.path.join(base_dir, "logs/output_logs/trials.jsonl")
    
    if not os.path.exists(log_path):
        print("WARN: No trials.jsonl found. Assuming clean state for dry-run.")
        if not dry_run:
            print("FAIL: Log file missing.")
            return False
        return True
        
    required_keys = [
        "model_competence_success", "infrastructure_valid", "reset_integrity_passed",
        "trial_acceptance_valid", "counts_toward_cell_n", "expected_logical_tool_sequence",
        "actual_logical_tool_sequence", "expected_exposed_tool_sequence",
        "actual_exposed_tool_sequence", "logical_to_exposed_tool_map_hash",
        "requested_inference_parameters", "effective_inference_parameters",
        "backend_reported_parameters", "unsupported_deterministic_controls"
    ]
    
    with open(log_path, "r") as f:
        for i, line in enumerate(f):
            try:
                data = json.loads(line)
            except:
                print(f"FAIL: Invalid JSON at line {i}")
                return False
            for k in required_keys:
                if k not in data:
                    print(f"FAIL: Missing required key '{k}' at line {i}")
                    return False
    print("PASS: Log format valid.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model")
    args = parser.parse_args()
    validate_logs(args.dry_run, args.model)
