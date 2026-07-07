"""
Module: hashing.py
Purpose: Reusable hashing functions for Phase 4 validation.
"""
import hashlib
import os
from typing import Dict
from pathlib import Path

def hash_file_sha256(filepath: str) -> str:
    """Computes the SHA-256 hash of a file."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cannot hash missing file: {filepath}")
        
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def hash_directory_sha256(dirpath: str, exclude_files: list = None) -> Dict[str, str]:
    """Hashes all files in a directory recursively, returning a dict of filepath -> hash."""
    if exclude_files is None:
        exclude_files = []
        
    hashes = {}
    for root, dirs, files in os.walk(dirpath):
        dirs.sort()
        for file in sorted(files):
            if file in exclude_files:
                continue
            filepath = os.path.join(root, file)
            # Normalize path for cross-platform consistency
            norm_path = Path(filepath).as_posix()
            hashes[norm_path] = hash_file_sha256(filepath)
    return hashes
