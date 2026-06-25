"""
Schema export and SHA-256 hashing utility.

Normalisation rules (from PHASE2.md §2.5):
  1. Export as canonical JSON
  2. UTF-8 encoding
  3. NFC Unicode normalisation
  4. \\n line endings
  5. Sorted keys
  6. SHA-256 hash

Output:
  reproducibility/schema_hash_ledger.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import os
import unicodedata

# All 9 schema variant files
_SCHEMA_FILES: list[tuple[str, str]] = [
    ("schemas/clean/density1.json", "D1-CLEAN"),
    ("schemas/clean/density3.json", "D3-CLEAN"),
    ("schemas/clean/density5.json", "D5-CLEAN"),
    ("schemas/poisoned_tool_description/density1.json", "D1-POISON-TD"),
    ("schemas/poisoned_tool_description/density3.json", "D3-POISON-TD"),
    ("schemas/poisoned_tool_description/density5.json", "D5-POISON-TD"),
    ("schemas/poisoned_capability_advertisement/density1.json", "D1-POISON-CA"),
    ("schemas/poisoned_capability_advertisement/density3.json", "D3-POISON-CA"),
    ("schemas/poisoned_capability_advertisement/density5.json", "D5-POISON-CA"),
]


def canonical_json(obj: dict) -> str:
    """Produce canonical JSON: sorted keys, UTF-8, NFC-normalised, \\n endings."""
    raw = json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2)
    # NFC Unicode normalisation
    normalised = unicodedata.normalize("NFC", raw)
    # Ensure \n line endings (strip \r)
    normalised = normalised.replace("\r\n", "\n").replace("\r", "\n")
    # Ensure trailing newline
    if not normalised.endswith("\n"):
        normalised += "\n"
    return normalised


def hash_schema(canonical: str) -> str:
    """Compute SHA-256 of canonical JSON string (UTF-8 encoded)."""
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_and_hash(filepath: str) -> tuple[dict, str, str]:
    """Load a schema file, produce canonical JSON, and compute hash.

    Returns:
        (schema_dict, canonical_json_str, sha256_hex)
    """
    with open(filepath, "r", encoding="utf-8") as f:
        schema = json.load(f)
    canonical = canonical_json(schema)
    sha = hash_schema(canonical)
    return schema, canonical, sha


def export_all(project_root: str | None = None) -> list[dict]:
    """Export all schema variants and write the hash ledger CSV.

    Returns a list of dicts with variant_id, filepath, and sha256.
    """
    if project_root is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    ledger_path = os.path.join(project_root, "reproducibility", "schema_hash_ledger.csv")
    rows: list[dict] = []

    for rel_path, variant_id in _SCHEMA_FILES:
        full_path = os.path.join(project_root, rel_path)
        _schema, _canonical, sha = load_and_hash(full_path)
        rows.append({
            "variant_id": variant_id,
            "filepath": rel_path,
            "sha256": sha,
        })

    # Write CSV ledger
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["variant_id", "filepath", "sha256"])
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return rows


if __name__ == "__main__":
    results = export_all()
    for r in results:
        print(f"{r['variant_id']:20s}  {r['sha256']}  {r['filepath']}")
