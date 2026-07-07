"""
Module: compile_cryptographic_lock_manifest.py
Purpose: Recursively hashes Phase 4 configuration and frozen artifacts.

Determinism Rule: All scripts must derive outputs exclusively from committed upstream artifacts.
No script may fabricate placeholder values, silently substitute defaults, infer missing evidence,
or generate synthetic metadata. When required evidence is unavailable, the script must explicitly
report DEPENDENCY_MISSING or NOT_MEASURABLE with justification.
"""
import os
import json
import argparse
import sys
import logging
import hashlib
from typing import Dict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def hash_file_bytes(filepath: str) -> str:
    """Hashes the raw bytes of a file. Does NOT include filesystem metadata."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def compile_manifest(targets: list, exclude: list) -> Dict[str, str]:
    file_hashes = {}
    for target in targets:
        target_path = Path(target)
        if target_path.exists():
            for root, dirs, files in os.walk(target_path):
                dirs.sort()
                files.sort()
                for file in files:
                    if file in exclude:
                        continue
                    filepath = Path(root) / file
                    # Normalize paths to use forward slashes for cross-platform determinism
                    norm_path = filepath.as_posix()
                    file_hashes[norm_path] = hash_file_bytes(str(filepath))
        else:
            logging.warning(f"Target directory for hashing not found: {target}")
            
    # Sort normalized paths lexicographically
    sorted_hashes = dict(sorted(file_hashes.items()))
    return sorted_hashes

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
        
    # Serialize with sort_keys=True for strict determinism
    manifest_bytes = json.dumps(file_hashes, sort_keys=True).encode("utf-8")
    overall_hash = hashlib.sha256(manifest_bytes).hexdigest()
    
    os.makedirs(os.path.dirname(args.manifest_out), exist_ok=True)
    with open(args.manifest_out, "w", encoding="utf-8") as f:
        json.dump({
            "manifest_hash": overall_hash, 
            "files": file_hashes
        }, f, indent=2, sort_keys=True, ensure_ascii=False)
        
    os.makedirs(os.path.dirname(args.csv_out), exist_ok=True)
    with open(args.csv_out, "w", encoding="utf-8") as f:
        f.write("file_path,sha256_hash\n")
        # Already sorted lexicographically above
        for k, v in file_hashes.items():
            f.write(f"{k},{v}\n")

    logging.info("[+] Cryptographic lock manifest compiled deterministically.")
    sys.exit(0)

if __name__ == '__main__':
    main()
