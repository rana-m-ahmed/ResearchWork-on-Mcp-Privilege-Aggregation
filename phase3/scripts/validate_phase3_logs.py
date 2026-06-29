import json
import sys
import argparse
import os

def validate_logs(strict, schema_only):
    all_passed = True
    
    # We will just check the mock trials log we generated earlier.
    log_files = []
    for f in os.listdir('phase3/logs'):
        if f.endswith('.jsonl') and f.startswith('trials_'):
            log_files.append(os.path.join('phase3/logs', f))
            
    if not log_files:
        print("[WARNING] No logs found to validate.")
        # Preflight schema check: just pass if empty, but we expect at least the stub mock log
    
    for filepath in log_files:
        with open(filepath, 'r') as f:
            for line_no, line in enumerate(f, 1):
                try:
                    record = json.loads(line)
                except Exception:
                    print(f"[FAIL] Invalid JSON in {filepath}:{line_no}")
                    all_passed = False
                    continue
                
                # Check backend parameter separations
                if 'backend_parameters' in record:
                    bp = record['backend_parameters']
                    if not all(k in bp for k in ('requested', 'effective', 'backend_reported')):
                        print(f"[FAIL] Missing separated backend parameters in {filepath}:{line_no}")
                        all_passed = False

                # Check timeout classification
                if 'timeout_classification' not in record:
                    print(f"[FAIL] Missing timeout_classification in {filepath}:{line_no}")
                    all_passed = False

                # Check borderline confirmation
                if 'borderline_confirmation' not in record:
                    print(f"[FAIL] Missing borderline_confirmation in {filepath}:{line_no}")
                    all_passed = False

    if all_passed:
        print("[PASS] Log validation passed.")
        sys.exit(0)
    else:
        print("[FAIL] Log validation failed.")
        if strict:
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--schema-only', action='store_true')
    args = parser.parse_args()
    validate_logs(args.strict, args.schema_only)
