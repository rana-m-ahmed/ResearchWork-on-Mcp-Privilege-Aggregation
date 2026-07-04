"""
Module: compile_cryptographic_lock_manifest.py
Purpose: Recursively hashes Phase 4 configuration and frozen artifacts.
"""
import os
import json
import argparse
import sys
import logging
import hashlib
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from utils.hashing import hash_directory_sha256
from utils.reporting import generate_report

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def compile_manifest(targets: list, exclude: list) -> Dict[str, str]:
    file_hashes = {}
    for target in targets:
        if os.path.exists(target):
            hashes = hash_directory_sha256(target, exclude)
            file_hashes.update(hashes)
        else:
            logging.warning(f"Target directory for hashing not found: {target}")
    return file_hashes

def main():
    parser = argparse.ArgumentParser(description="Compile Cryptographic Lock Manifest")
    parser.add_argument("--targets", nargs="+", default=["phase4/configs", "phase4/frozen_bundle"], help="Dirs to hash")
    parser.add_argument("--exclude", nargs="+", default=["cryptographic_lock_manifest.json", "master_hash_ledger.csv"], help="Files to exclude")
    parser.add_argument("--manifest-out", default="phase4/frozen_bundle/cryptographic_lock_manifest.json", help="Manifest output")
    parser.add_argument("--csv-out", default="phase4/frozen_bundle/master_hash_ledger.csv", help="CSV ledger output")
    args = parser.parse_args()

    logging.info("[*] Hashing frozen files...")
    file_hashes = compile_manifest(args.targets, args.exclude)
    
    if not file_hashes:
        logging.error("No files found to hash. Cannot compile cryptographic lock.")
        sys.exit(1)
        
    manifest_bytes = json.dumps(file_hashes, sort_keys=True).encode("utf-8")
    overall_hash = hashlib.sha256(manifest_bytes).hexdigest()
    
    os.makedirs(os.path.dirname(args.manifest_out), exist_ok=True)
    with open(args.manifest_out, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_hash": overall_hash, 
            "files": file_hashes
        }, f, indent=2)
        
    os.makedirs(os.path.dirname(args.csv_out), exist_ok=True)
    with open(args.csv_out, "w", encoding="utf-8") as f:
        f.write("file_path,sha256_hash\n")
        for k, v in file_hashes.items():
            f.write(f"{k},{v}\n")

    logging.info("[+] Cryptographic lock manifest compiled.")
    sys.exit(0)

if __name__ == '__main__':
    main()
