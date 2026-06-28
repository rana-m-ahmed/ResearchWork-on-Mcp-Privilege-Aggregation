import os
import json

base_dir = r"d:\research-work\ResearchWork-on-Mcp-Privilege-Aggregation"

d1_tools = {"read_internal_notes"}
d3_tools = {"read_internal_notes", "write_outbox", "get_local_weather"}
d5_tools = {"read_internal_notes", "write_outbox", "get_local_weather", "query_local_inventory", "log_event"}

banned_strings = [
    "override", "exfiltrate", "ignore previous", "hidden",
    "malicious", "benchmark attack", "attack success"
]

def validate_tasks():
    files = [
        ("D1", "phase3/tasks/benign_tasks_d1.jsonl"),
        ("D3", "phase3/tasks/benign_tasks_d3.jsonl"),
        ("D5", "phase3/tasks/benign_tasks_d5.jsonl"),
        ("MASTER", "phase3/tasks/benign_tasks_master.jsonl")
    ]
    
    report_lines = ["# Task Validation Report\n"]
    all_passed = True
    seen_hashes = set()
    
    for density, rel_path in files:
        path = os.path.join(base_dir, rel_path)
        if not os.path.exists(path):
            report_lines.append(f"FAIL: {rel_path} does not exist.")
            all_passed = False
            continue
            
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for idx, line in enumerate(lines):
            try:
                task = json.loads(line)
            except:
                report_lines.append(f"FAIL: {rel_path} line {idx} invalid JSON.")
                all_passed = False
                continue
                
            task_str = json.dumps(task).lower()
            
            # Check adversarial text
            for ban in banned_strings:
                if ban in task_str:
                    report_lines.append(f"FAIL: {rel_path} task {task.get('task_id')} contains banned text '{ban}'")
                    all_passed = False
                    
            # Check hash
            h = task.get("task_hash")
            if not h:
                report_lines.append(f"FAIL: {rel_path} task {task.get('task_id')} missing task_hash.")
                all_passed = False
            elif density != "MASTER":
                if h in seen_hashes:
                    report_lines.append(f"FAIL: {rel_path} task {task.get('task_id')} has duplicate hash {h}.")
                    all_passed = False
                seen_hashes.add(h)
                
            # Check expected sequence
            seq = task.get("expected_sequence")
            if not seq:
                report_lines.append(f"FAIL: {rel_path} task {task.get('task_id')} absent expected_sequence.")
                all_passed = False
            else:
                for tool in seq:
                    if density == "D1" and tool not in d1_tools:
                        report_lines.append(f"FAIL: D1 task used non-D1 tool {tool}.")
                        all_passed = False
                    if density == "D3" and tool not in d3_tools:
                        report_lines.append(f"FAIL: D3 task used non-D3 tool {tool}.")
                        all_passed = False
                    if density == "D5" and tool not in d5_tools:
                        report_lines.append(f"FAIL: D5 task used non-D5 tool {tool}.")
                        all_passed = False

            # Check phase metadata
            if task.get("phase") != "phase3_competence" or not task.get("benign_competence_only"):
                report_lines.append(f"FAIL: {rel_path} task {task.get('task_id')} missing benign metadata.")
                all_passed = False

    report_path = os.path.join(base_dir, "phase3/validation/task_validation_report.md")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + ("\nPASS: All tasks valid.\n" if all_passed else "\nFAIL: Errors found.\n"))
        
    if all_passed:
        print("PASS: Task validation completed successfully.")
    else:
        print("FAIL: Task validation errors found.")

if __name__ == "__main__":
    validate_tasks()
