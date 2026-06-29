import os
import sys
import hashlib
import json
import argparse

def get_hash(filepath):
    with open(filepath, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

def create_manifest(strict):
    freeze_targets = [
        'client/',
        'server/',
        'schemas/',
        'prompts/',
        'tests/',
        'scripts/',
        'docker/',
        'phase3/tasks/',
        'phase3/matrices/',
        'phase3/scripts/',
        'phase3/configs/phase3_global.yaml',
        'phase3/configs/deterministic_inference.yaml',
        'phase3/configs/reset_policy.yaml'
    ]

    manifest = {}
    all_passed = True
    
    for target in freeze_targets:
        if not os.path.exists(target):
            print(f"[FAIL] Target not found: {target}")
            all_passed = False
            continue
            
        if os.path.isdir(target):
            for root, _, files in os.walk(target):
                for file in sorted(files):
                    # Exclude compiled pyc, etc
                    if file.endswith('.pyc') or '__pycache__' in root:
                        continue
                    filepath = os.path.join(root, file)
                    manifest[filepath] = get_hash(filepath)
        else:
            manifest[target] = get_hash(target)

    manifest_path = 'phase3/configs/source_freeze_manifest.json'
    
    with open(manifest_path, 'w') as f:
        json.dump({
            "status": "FROZEN",
            "targets_hashed": len(manifest),
            "hashes": manifest
        }, f, indent=2)

    print(f"[PASS] Source freeze manifest created at {manifest_path} with {len(manifest)} files.")

    if not all_passed:
        if strict:
            sys.exit(1)
            
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--create-manifest', action='store_true')
    parser.add_argument('--strict', action='store_true')
    args = parser.parse_args()
    
    if args.create_manifest:
        create_manifest(args.strict)
    else:
        print("[FAIL] Missing --create-manifest flag.")
        if args.strict:
            sys.exit(1)
