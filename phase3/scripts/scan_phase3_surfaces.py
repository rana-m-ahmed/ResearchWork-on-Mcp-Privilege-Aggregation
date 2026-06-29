import os
import sys
import argparse

FORBIDDEN_STRINGS = [
    "ignore previous instructions",
    "override",
    "exfiltrate",
    "send data to",
    "you are now",
    "hidden instruction",
    "malicious",
    "attack success",
    "pwned",
    "security evaluation",
    "payload",
    "jailbreak"
]

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read().lower()
        for forbidden in FORBIDDEN_STRINGS:
            if forbidden in content:
                print(f"[FAIL] Found forbidden string '{forbidden}' in {filepath}")
                return False
    return True

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()

    directories_to_scan = [
        'schemas/phase3_surface',
        'prompts'
    ]

    all_passed = True
    for directory in directories_to_scan:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.json') or file.endswith('.txt'):
                    filepath = os.path.join(root, file)
                    if not scan_file(filepath):
                        all_passed = False

    if all_passed:
        print("[PASS] All Phase 3 surfaces and prompts are strictly benign.")
        sys.exit(0)
    else:
        print("[FAIL] Adversarial or forbidden language detected.")
        if args.strict:
            sys.exit(1)
        sys.exit(0)

if __name__ == "__main__":
    main()
