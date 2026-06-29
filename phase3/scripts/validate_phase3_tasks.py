import json
import os
import sys
import argparse
import hashlib

FORBIDDEN_STRINGS = [
    "ignore previous instructions", "override", "exfiltrate", "send data to", 
    "you are now", "hidden instruction", "malicious", "attack success", 
    "pwned", "security evaluation", "payload", "jailbreak"
]

def scan_text(text):
    text = text.lower()
    for f in FORBIDDEN_STRINGS:
        if f in text:
            return False, f
    return True, None

def validate_tasks():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    files = [
        'phase3/tasks/benign_tasks_d1.jsonl',
        'phase3/tasks/benign_tasks_d3.jsonl',
        'phase3/tasks/benign_tasks_d5.jsonl'
    ]

    all_passed = True
    seen_tasks = set()

    d1_allowed = {"read_internal_notes"}
    d3_allowed = {"read_internal_notes", "write_outbox", "get_local_weather"}
    d5_allowed = {"read_internal_notes", "write_outbox", "get_local_weather", "query_local_inventory", "log_event"}

    for filepath in files:
        if not os.path.exists(filepath):
            continue
        with open(filepath, 'r') as f:
            for line_no, line in enumerate(f, 1):
                try:
                    task = json.loads(line)
                except:
                    print(f"[FAIL] Invalid JSON in {filepath} line {line_no}")
                    all_passed = False
                    continue

                if task.get("status") == "TODO_BEFORE_OFFICIAL_RUN":
                    continue

                # 1. Benign content & no adversarial strings
                task_str = json.dumps(task)
                is_clean, bad_str = scan_text(task_str)
                if not is_clean:
                    print(f"[FAIL] Task {task['task_id']} contains forbidden string '{bad_str}'")
                    all_passed = False

                # 2. Hash reproduction
                provided_hash = task.pop('text_hash', None)
                calc_hash = hashlib.sha256(json.dumps(task, sort_keys=True).encode()).hexdigest()
                if provided_hash != calc_hash:
                    print(f"[FAIL] Task {task['task_id']} hash mismatch.")
                    all_passed = False

                # 3. Density/tool legality
                density = task.get('density')
                expected = set(task.get('expected_tool_sequence', []))
                
                if density == 1 and not expected.issubset(d1_allowed):
                    print(f"[FAIL] Task {task['task_id']} (D1) uses illegal tools.")
                    all_passed = False
                if density == 3 and not expected.issubset(d3_allowed):
                    print(f"[FAIL] Task {task['task_id']} (D3) uses illegal tools (e.g. D5-only).")
                    all_passed = False
                if density == 5 and not expected.issubset(d5_allowed):
                    print(f"[FAIL] Task {task['task_id']} (D5) uses illegal tools.")
                    all_passed = False

                # 4. Success predicate
                if task.get('success_predicate') != "deterministic_check":
                    print(f"[FAIL] Task {task['task_id']} success predicate is not deterministic.")
                    all_passed = False

                # 5. Duplicates
                if user_task := task.get('user_task'):
                    if user_task in seen_tasks:
                        print(f"[FAIL] Task {task['task_id']} is a duplicate user_task.")
                        all_passed = False
                    seen_tasks.add(user_task)

    if all_passed:
        print("[PASS] All tasks validated successfully.")
        sys.exit(0)
    else:
        print("[FAIL] Task validation errors found.")
        if args.strict:
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    validate_tasks()
