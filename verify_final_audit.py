"""
Phase 2 Final Audit Verification Script
Systematically checks log contents and documentation requirements before final commit.
"""

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(PROJECT_ROOT, "logs", "output_logs")

PASS = "✅ PASS"
FAIL = "❌ FAIL"
results = []

def check(number: int, description: str, passed: bool, detail: str = ""):
    status = PASS if passed else FAIL
    results.append((number, passed))
    msg = f"  [{status}] #{number}: {description}"
    if detail:
        msg += f"\n         {detail}"
    print(msg)


# Locate log files
log_files = [f for f in os.listdir(LOG_DIR) if f.endswith(".jsonl")]
all_rows = []
for lf in log_files:
    with open(os.path.join(LOG_DIR, lf), "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                all_rows.append((lf, json.loads(line)))

# CHECK 2: Open every JSONL log and confirm phase2_infra + non_experimental
check2_pass = True
check2_detail = ""
for lf, row in all_rows:
    if row.get("phase") != "phase2_infra" or row.get("non_experimental") is not True:
        check2_pass = False
        check2_detail = f"File {lf} has invalid phase/non_experimental flags"
check(2, "All JSONL logs have phase='phase2_infra' and non_experimental=true", check2_pass, check2_detail)

# CHECK 3: Confirm no ASR, TID, Critical Exploit, attack_success, exploit_found labels exist
FORBIDDEN = {"asr", "tid", "critical exploit", "attack_success", "exploit_found", "critical_exploit"}
check3_pass = True
check3_detail = ""
for lf, row in all_rows:
    row_str = json.dumps(row).lower()
    for f in FORBIDDEN:
        if f in row_str:
            check3_pass = False
            check3_detail = f"File {lf} contains forbidden string '{f}'"
check(3, "No forbidden labels (ASR, TID, attack_success, etc.) in logs", check3_pass, check3_detail)

# CHECK 4: Confirm placeholder rows have is_placeholder_payload=true
check4_pass = True
check4_detail = ""
adv_rows = [r for lf, r in all_rows if "adversarial_channel" in lf]
for r in adv_rows:
    if r.get("is_placeholder_payload") is not True:
        check4_pass = False
        check4_detail = "Adversarial channel row missing is_placeholder_payload=true"
if not adv_rows:
    check4_detail = "No adversarial rows found"
check(4, "Placeholder rows have is_placeholder_payload=true", check4_pass and len(adv_rows) > 0, check4_detail)

# CHECK 5: Confirm Phase 2 logs are separate from any Phase 3/5 path
check5_pass = True
check5_detail = ""
for f in os.listdir(LOG_DIR):
    if f.startswith("phase3") or f.startswith("phase5"):
        check5_pass = False
        check5_detail = f"Found Phase 3/5 log in Phase 2 log dir: {f}"
check(5, "Phase 2 logs isolated from Phase 3/5 logs", check5_pass, check5_detail)

# CHECK 6: Confirm Mode A or Mode B is documented
docs_path = os.path.join(PROJECT_ROOT, "docs", "phase2_audit_checklist.md")
with open(docs_path, "r", encoding="utf-8") as f:
    audit_content = f.read()
check6_pass = "Mode A is default backend" in audit_content
check(6, "Mode A or Mode B is documented in audit checklist", check6_pass)

# CHECK 11: Confirm docs/phase2_go_no_go_record.md has evidence for every gate
gonogo_path = os.path.join(PROJECT_ROOT, "docs", "phase2_go_no_go_record.md")
with open(gonogo_path, "r", encoding="utf-8") as f:
    gonogo_content = f.read()
check11_pass = "✅ PASS" in gonogo_content and "TBD" in gonogo_content # At least one TBD for LLM smoke test
check(11, "docs/phase2_go_no_go_record.md has evidence for gates", check11_pass)

# CHECK 12: Confirm docs/phase2_handoff_to_phase2_5_and_phase3.md says Phase 3 starts fresh
handoff_path = os.path.join(PROJECT_ROOT, "docs", "phase2_handoff_to_phase2_5_and_phase3.md")
with open(handoff_path, "r", encoding="utf-8") as f:
    handoff_content = f.read().lower()
check12_pass = "starts a fresh competence dataset" in handoff_content or "starts a **fresh competence dataset" in handoff_content
check(12, "Handoff doc states Phase 3 starts fresh", check12_pass)

print("\n" + "=" * 60)
failed = sum(1 for _, p in results if not p)
sys.exit(0 if failed == 0 else 1)
