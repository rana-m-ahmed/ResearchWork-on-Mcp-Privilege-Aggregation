"""
Test: Schema Hash Consistency

Verifies that:
  - Every schema file can be loaded, canonicalized, and hashed
  - Hashes are stable (same content → same hash)
  - The hash ledger CSV can be generated and all 9 entries are present
  - Schema hashes match between re-export runs
"""

from __future__ import annotations

import csv
import os

import pytest

from schemas.export_and_hash import (
    canonical_json,
    hash_schema,
    load_and_hash,
    export_all,
    _SCHEMA_FILES,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_all_schema_files_exist() -> None:
    """All 9 schema variant files must exist."""
    for rel_path, variant_id in _SCHEMA_FILES:
        full_path = os.path.join(PROJECT_ROOT, rel_path)
        assert os.path.isfile(full_path), (
            f"Schema file missing: {rel_path} (variant {variant_id})"
        )


def test_canonical_json_deterministic() -> None:
    """canonical_json must produce identical output for identical input."""
    obj = {"b": 2, "a": 1, "c": {"z": 26, "a": 1}}
    c1 = canonical_json(obj)
    c2 = canonical_json(obj)
    assert c1 == c2


def test_hash_deterministic() -> None:
    """Same canonical JSON → same SHA-256."""
    obj = {"hello": "world"}
    c = canonical_json(obj)
    h1 = hash_schema(c)
    h2 = hash_schema(c)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex digest


@pytest.mark.parametrize("rel_path,variant_id", _SCHEMA_FILES)
def test_load_and_hash_succeeds(rel_path: str, variant_id: str) -> None:
    """Every schema file must load, canonicalize, and hash without error."""
    full_path = os.path.join(PROJECT_ROOT, rel_path)
    schema, canonical, sha = load_and_hash(full_path)
    assert isinstance(schema, dict)
    assert isinstance(canonical, str)
    assert len(sha) == 64
    assert schema.get("schema_variant_id") == variant_id


def test_hash_stability_across_runs() -> None:
    """Re-hashing the same file must produce the same result."""
    full_path = os.path.join(PROJECT_ROOT, _SCHEMA_FILES[0][0])
    _, _, h1 = load_and_hash(full_path)
    _, _, h2 = load_and_hash(full_path)
    assert h1 == h2


def test_export_all_produces_ledger() -> None:
    """export_all must produce 9 rows and write the CSV ledger."""
    rows = export_all(PROJECT_ROOT)
    assert len(rows) == 9

    ledger_path = os.path.join(PROJECT_ROOT, "reproducibility", "schema_hash_ledger.csv")
    assert os.path.isfile(ledger_path)

    with open(ledger_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        csv_rows = list(reader)
    assert len(csv_rows) == 9

    variant_ids = {r["variant_id"] for r in csv_rows}
    expected = {v for _, v in _SCHEMA_FILES}
    assert variant_ids == expected


def test_all_hashes_unique() -> None:
    """Each schema variant should have a distinct hash (content differs)."""
    rows = export_all(PROJECT_ROOT)
    hashes = [r["sha256"] for r in rows]
    # Clean and poisoned versions of the same density MUST differ
    assert len(set(hashes)) == 9, (
        f"Expected 9 unique hashes, got {len(set(hashes))}"
    )
