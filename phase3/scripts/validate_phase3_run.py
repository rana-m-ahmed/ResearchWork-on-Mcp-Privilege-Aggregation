import argparse
import json
import logging
import os
import sys
import subprocess
import datetime
import hashlib

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

def parse_args():
    parser = argparse.ArgumentParser(description="Phase 3 Validation Script")
    parser.add_argument("--model-slot", type=str, required=True, help="Model slot to validate (e.g., M1, M2)")
    return parser.parse_args()

def get_git_info():
    """Retrieve git branch and commit evidence."""
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], text=True).strip()
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
        return branch, commit
    except Exception as e:
        logging.error(f"Failed to get git info: {e}")
        return "UNKNOWN", "UNKNOWN"

def validate_run(model_slot):
    log_file = f"phase3/logs/trials_{model_slot}.jsonl"
    if not os.path.exists(log_file):
        logging.error(f"Log file {log_file} does not exist.")
        return False, "File not found"

    valid_count = 0
    total_count = 0
    all_trials_valid = True

    try:
        with open(log_file, "r") as f:
            for line in f:
                total_count += 1
                record = json.loads(line)
                
                # Strict check that counts_toward_cell_n implies other checks passed
                if record.get("counts_toward_cell_n"):
                    if not (record.get("infrastructure_valid") and 
                            record.get("reset_integrity_passed") and 
                            record.get("trial_acceptance_valid") and
                            not record.get("malformed_output")):
                        logging.error(f"Trial {record.get('trial_id')} counted towards cell_n but failed strict validation!")
                        all_trials_valid = False
                    else:
                        valid_count += 1
    except Exception as e:
        logging.error(f"Error parsing log file: {e}")
        return False, str(e)

    # Compute a dummy hash of the log file for auditing
    try:
        with open(log_file, "rb") as f:
            file_hash = hashlib.sha256(f.read()).hexdigest()
    except Exception:
        file_hash = "UNKNOWN"

    passed = all_trials_valid and valid_count > 0

    return passed, {
        "total_trials_run": total_count,
        "valid_trials_completed": valid_count,
        "log_file_hash": file_hash,
        "checked_files": [log_file]
    }

def main():
    args = parse_args()
    branch, commit = get_git_info()
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()
    
    # Run validation
    passed, details = validate_run(args.model_slot)
    
    status_str = "PASS" if passed else "FAIL"
    exit_code = 0 if passed else 1

    report = {
        "timestamp": timestamp,
        "model_slot": args.model_slot,
        "status": status_str,
        "branch": branch,
        "commit": commit,
        "exit_code": exit_code,
        "validation_details": details
    }

    report_file = f"phase3/logs/validation_report_{args.model_slot}.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=4)
        
    logging.info(f"Validation Report generated: {report_file}")
    print(f"\n--- VALIDATION RESULT: {status_str} ---")
    print(json.dumps(report, indent=2))
    
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
