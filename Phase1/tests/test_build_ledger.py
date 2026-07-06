import pytest
import os
import sys
import json
import uuid
import tempfile
import hashlib
import datetime
from pathlib import Path
import subprocess

# Reliably add scripts to path
repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(repo_root / 'Phase1' / 'scripts'))

from build_json_ledger import PayloadLedgerBuilder, GENERATOR_VERSION, natural_key

def test_normalization():
    builder = PayloadLedgerBuilder(Path('.'))
    assert builder._normalize("test\r\nstring") == "test\nstring"
    assert builder._normalize("test\rstring") == "test\nstring"
    assert builder._normalize("test  \n") == "test  \n"
    assert builder._normalize(None) == None

def test_unicode_nfc():
    builder = PayloadLedgerBuilder(Path('.'))
    composed = "caf\u00e9"
    decomposed = "cafe\u0301"
    assert composed != decomposed
    assert builder._normalize(composed) == builder._normalize(decomposed)

def test_bom_stripping(tmp_path):
    builder = PayloadLedgerBuilder(tmp_path)
    p = tmp_path / "bom_test.jsonl"
    with open(p, "w", encoding="utf-8-sig") as f:
        f.write(json.dumps({"Attacker Instruction": "payload_with_bom"}) + "\n")
    builder.load_jsonl(p.name, "Test", "TestFam")
    assert len(builder.raw_payloads) == 1
    assert builder.raw_payloads[0]["payload_text"] == "payload_with_bom"

def test_fail_fast_missing_file():
    builder = PayloadLedgerBuilder(Path('.'))
    with pytest.raises(SystemExit):
        builder._record_file(Path("does_not_exist_ever.jsonl"))

def test_natural_sorting():
    keys = ["1", "10", "2", "20", "11"]
    sorted_keys = sorted(keys, key=natural_key)
    assert sorted_keys == ["1", "2", "10", "11", "20"]

def test_deterministic_ordering():
    builder = PayloadLedgerBuilder(Path('.'))
    builder.add_payload("payload_b", "Z", "Fam1", "b.json", "2")
    builder.add_payload("payload_a", "A", "Fam2", "a.json", "1")
    builder.add_payload("payload_a", "A", "Fam1", "a.json", "1")
    builder.add_payload("payload_a", "A", "Fam1", "a.json", "10")
    
    lst = builder.build_canonical_list("commit", "timestamp")
    assert lst[0]['benchmark_source'] == "A"
    assert lst[0]['attack_family'] == "Fam1"
    assert lst[0]['provenance']['original_identifier'] == "1"
    assert lst[1]['benchmark_source'] == "A"
    assert lst[1]['attack_family'] == "Fam1"
    assert lst[1]['provenance']['original_identifier'] == "10"
    assert lst[2]['benchmark_source'] == "A"
    assert lst[2]['attack_family'] == "Fam2"
    assert lst[3]['benchmark_source'] == "Z"

def test_duplicate_detection_and_id_policy():
    builder = PayloadLedgerBuilder(Path('.'))
    builder.add_payload("same_payload", "Bench1", "Fam1", "1.json", "1")
    builder.add_payload("same_payload", "Bench1", "Fam1", "2.json", "2")
    builder.add_payload("same_payload", "Bench2", "Fam1", "3.json", "1")
    
    lst = builder.build_canonical_list("commit", "timestamp")
    assert lst[0]['duplicate_handling']['is_canonical'] == True
    first_id = lst[0]['payload_id']
    
    assert lst[1]['duplicate_handling']['is_canonical'] == False
    assert lst[1]['duplicate_handling']['canonical_reference'] == first_id
    assert lst[1]['payload_id'] != first_id  # Duplicate ID Policy: unique payload IDs
    
    assert lst[2]['duplicate_handling']['is_canonical'] == True
    assert lst[2]['duplicate_handling']['text_duplicate_across_benchmarks'] == True

def test_skip_empty_payloads():
    builder = PayloadLedgerBuilder(Path('.'))
    builder.add_payload("   ", "AgentDojo", "DOS", "a.xlsx", "1")
    builder.add_payload("", "AgentDojo", "DOS", "a.xlsx", "2")
    builder.add_payload(None, "AgentDojo", "DOS", "a.xlsx", "3")
    assert len(builder.raw_payloads) == 0
    assert len(builder.skipped_records) == 3

def test_manifest_integrity(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    builder = PayloadLedgerBuilder(Path('.'), execution_uuid="manifest-test-1234")
    out_json = tmp_path / "ledger.json"
    out_csv = tmp_path / "canonical_inventory.csv"
    out_phase25 = tmp_path / "p25.json"
    
    builder.execute(out_json, out_csv, out_phase25, build_timestamp="2024-01-01T00:00:00Z")
    
    manifest_path = out_json.parent / "manifest.json"
    assert manifest_path.exists()
    
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)
        
    actual_ledger_hash = hashlib.sha256(out_json.read_bytes()).hexdigest()
    actual_csv_hash = hashlib.sha256(out_csv.read_bytes()).hexdigest()
    actual_p25_hash = hashlib.sha256(out_phase25.read_bytes()).hexdigest()
    
    assert manifest["ledger_sha256"] == actual_ledger_hash
    assert manifest["csv_sha256"] == actual_csv_hash
    assert manifest["phase25_ledger_sha256"] == actual_p25_hash

def test_git_fallback(monkeypatch, tmp_path):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    def mock_check_output(*args, **kwargs):
        raise Exception("Mock Git Failure")
    
    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    
    builder = PayloadLedgerBuilder(Path('.'), execution_uuid="git-test-1234")
    builder.execute(tmp_path/"out.json", tmp_path/"out.csv", tmp_path/"out_p25.json", build_timestamp="1")
    
    with open(tmp_path/"out.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["repository_commit"] is None

def test_stable_uuid(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    stable_id = "550e8400-e29b-41d4-a716-446655440000"
    builder = PayloadLedgerBuilder(Path('.'), execution_uuid=stable_id)
    builder.execute(tmp_path/"out.json", tmp_path/"out.csv", tmp_path/"out_p25.json", build_timestamp="1")
    
    with open(tmp_path/"out.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["execution_uuid"] == stable_id

def test_stable_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    os.environ["SOURCE_DATE_EPOCH"] = "1704067200" # 2024-01-01T00:00:00Z
    builder = PayloadLedgerBuilder(Path('.'))
    builder.execute(tmp_path/"out.json", tmp_path/"out.csv", tmp_path/"out_p25.json")
    
    with open(tmp_path/"out.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["ledger_generated_at"] == "2024-01-01T00:00:00+00:00"
    
    del os.environ["SOURCE_DATE_EPOCH"]

def test_newline_determinism(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    builder = PayloadLedgerBuilder(Path('.'), execution_uuid="newline-test")
    out_json = tmp_path / "ledger.json"
    out_csv = tmp_path / "canonical_inventory.csv"
    out_phase25 = tmp_path / "p25.json"
    
    builder.execute(out_json, out_csv, out_phase25, build_timestamp="1")
    builder.write_validation_report(tmp_path / "report.md")
    
    for f in [out_json, out_csv, out_phase25, out_json.parent / "manifest.json", tmp_path / "report.md"]:
        if f.exists():
            content = f.read_bytes()
            assert b'\r\n' not in content
            assert b'\n' in content

def test_extraction_date_determinism():
    builder = PayloadLedgerBuilder(Path('.'))
    builder.add_payload("same_payload", "Bench1", "Fam1", "1.json", "1")
    lst = builder.build_canonical_list("commit", "timestamp")
    assert lst[0]["provenance"]["extraction_date"] == "timestamp"

def test_platform_override(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    builder = PayloadLedgerBuilder(Path('.'), build_platform="Any")
    builder.execute(tmp_path/"out.json", tmp_path/"out.csv", tmp_path/"out_p25.json", build_timestamp="1")
    
    with open(tmp_path/"out.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["platform"] == "Any"
        import platform
        assert data["metadata"]["platform"] != platform.system()

def test_python_override(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    builder = PayloadLedgerBuilder(Path('.'), build_python="Any")
    builder.execute(tmp_path/"out.json", tmp_path/"out.csv", tmp_path/"out_p25.json", build_timestamp="1")
    
    with open(tmp_path/"out.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        assert data["metadata"]["python_version"] == "Any"

def test_repository_commit_override(tmp_path, monkeypatch):
    monkeypatch.setattr(PayloadLedgerBuilder, "load_jsonl", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_skill_inject", lambda *args, **kwargs: None)
    monkeypatch.setattr(PayloadLedgerBuilder, "load_excel", lambda *args, **kwargs: None)
    
    # 1. With Git (succeeds)
    b1 = PayloadLedgerBuilder(Path('.'), repository_commit="abc123", execution_uuid="1")
    b1.execute(tmp_path/"o1.json", tmp_path/"c1.csv", tmp_path/"p1.json", build_timestamp="1")
    
    # 2. Without Git (fails)
    def mock_check_output(*args, **kwargs):
        raise Exception("Mock Git Failure")
    monkeypatch.setattr(subprocess, "check_output", mock_check_output)
    
    b2 = PayloadLedgerBuilder(Path('.'), repository_commit="abc123", execution_uuid="1")
    b2.execute(tmp_path/"o2.json", tmp_path/"c2.csv", tmp_path/"p2.json", build_timestamp="1")
    
    bytes1 = (tmp_path/"o1.json").read_bytes()
    bytes2 = (tmp_path/"o2.json").read_bytes()
    assert bytes1 == bytes2

def test_end_to_end_determinism(tmp_path):
    # This tests the true execution pipeline exactly as shipped without any monkeypatching
    b1 = PayloadLedgerBuilder(
        repo_root, 
        execution_uuid="deterministic-e2e-test", 
        build_platform="Any", 
        build_python="Any", 
        repository_commit="fixed-commit"
    )
    b2 = PayloadLedgerBuilder(
        repo_root, 
        execution_uuid="deterministic-e2e-test", 
        build_platform="Any", 
        build_python="Any", 
        repository_commit="fixed-commit"
    )
    
    o1_dir = tmp_path / "1"
    o1_json = o1_dir / "ledger.json"
    o1_csv = o1_dir / "csv.csv"
    o1_p25 = o1_dir / "p25.json"
    b1.execute(o1_json, o1_csv, o1_p25, build_timestamp="2024-01-01T00:00:00Z")
    
    o2_dir = tmp_path / "2"
    o2_json = o2_dir / "ledger.json"
    o2_csv = o2_dir / "csv.csv"
    o2_p25 = o2_dir / "p25.json"
    b2.execute(o2_json, o2_csv, o2_p25, build_timestamp="2024-01-01T00:00:00Z")
    
    bytes1 = o1_json.read_bytes()
    bytes2 = o2_json.read_bytes()
    assert bytes1 == bytes2
    assert hashlib.sha256(bytes1).hexdigest() == hashlib.sha256(bytes2).hexdigest()
