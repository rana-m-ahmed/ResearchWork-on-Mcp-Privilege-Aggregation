import os
import sys
import argparse
import csv

def verify_preflight(strict, no_official_runs):
    all_passed = True
    
    # 1. Phase 2/2.5 GO Artifacts
    p2_go = 'docs/phase2_go_no_go_record.md'
    p25_go = 'phase2_5/reports/Budget_Decision_Report.md'
    if not os.path.exists(p2_go):
        print(f"[FAIL] Phase 2 GO artifact not found: {p2_go}")
        all_passed = False
    if not os.path.exists(p25_go):
        print(f"[FAIL] Phase 2.5 GO artifact not found: {p25_go}")
        all_passed = False
        
    # 2. Matrix counts
    matrix_path = 'phase3/matrices/phase3_experimental_matrix.csv'
    if not os.path.exists(matrix_path):
        print("[FAIL] Matrix not found.")
        all_passed = False
    else:
        with open(matrix_path, 'r') as f:
            reader = list(csv.DictReader(f))
            if len(reader) != 1800:
                print(f"[FAIL] Matrix row count is {len(reader)}, expected 1800.")
                all_passed = False

    # 3. Model selection rationale TODOs
    rationale = 'phase3/configs/model_selection_rationale.md'
    if os.path.exists(rationale):
        with open(rationale, 'r') as f:
            if "TODO_BEFORE_OFFICIAL_RUN" not in f.read():
                print("[WARNING] model_selection_rationale.md doesn't have TODO_BEFORE_OFFICIAL_RUN, might be fully initialized.")
                
    # 4. Check for official runs
    if no_official_runs:
        for i in range(1, 5):
            if os.path.exists(f"phase3/logs/official_M{i}.jsonl"):
                print(f"[FAIL] Found official run for M{i} before freeze.")
                all_passed = False

    if all_passed:
        print("[PASS] Preflight verification passed.")
        sys.exit(0)
    else:
        print("[FAIL] Preflight verification failed.")
        if strict:
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    parser.add_argument('--no-official-runs', action='store_true')
    args = parser.parse_args()
    verify_preflight(args.strict, args.no_official_runs)
