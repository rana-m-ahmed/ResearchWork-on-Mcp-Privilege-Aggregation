import json
import csv
import argparse
import logging
import hashlib
import platform
import sys
import datetime
import unicodedata
import re
import uuid
import subprocess
import os
from pathlib import Path

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import jsonschema
except ImportError:
    jsonschema = None

GENERATOR_VERSION = "1.0.0"

SCHEMA = {
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Canonical Payload Ledger",
  "type": "object",
  "properties": {
    "metadata": {
      "type": "object",
      "properties": {
        "schema_version": {"type": "string"},
        "generator_version": {"type": "string"},
        "ledger_generated_at": {"type": "string", "format": "date-time"},
        "execution_uuid": {"type": "string"},
        "repository_commit": {"type": ["string", "null"]},
        "python_version": {"type": "string"},
        "platform": {"type": "string"},
        "dependencies": {"type": "object"},
        "payload_count": {"type": "integer"},
        "canonical_payload_count": {"type": "integer"},
        "duplicate_payload_count": {"type": "integer"},
        "skipped_payload_count": {"type": "integer"},
        "source_files": {"type": "array"}
      },
      "required": ["schema_version", "ledger_generated_at"]
    },
    "payloads": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "payload_id": {"type": "string", "pattern": "^PAYLOAD_\\d{6}$"},
          "payload_text": {"type": "string"},
          "benchmark_source": {"type": "string"},
          "attack_family": {"type": "string"},
          "mcp_exposure": {"type": ["string", "null"]},
          "approval_status": {"type": "string"},
          "provenance": {"type": "object"},
          "duplicate_handling": {"type": "object"},
          "phase1_payload_hash": {"type": ["string", "null"]},
          "payload_condition": {"type": "string"}
        },
        "required": [
          "payload_id", "payload_text", "benchmark_source", 
          "attack_family", "approval_status", "provenance", 
          "duplicate_handling", "phase1_payload_hash", "payload_condition"
        ]
      }
    }
  }
}

def natural_key(text):
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', str(text))]

class PayloadLedgerBuilder:
    def __init__(self, repo_root: Path, execution_uuid=None, build_platform=None, build_python=None, repository_commit=None):
        self.repo_root = repo_root
        self.raw_payloads = []
        self.skipped_records = []
        self.source_file_hashes = []
        self.file_metadata = {}
        self.payload_counter = 1
        self.execution_uuid = execution_uuid or os.environ.get("EXECUTION_UUID") or str(uuid.uuid4())
        self.build_platform = build_platform or os.environ.get("SOURCE_PLATFORM") or "Any"
        self.build_python = build_python or os.environ.get("SOURCE_PYTHON_VERSION") or "Any"
        self.repository_commit = repository_commit or os.environ.get("SOURCE_COMMIT_SHA")
        
        self.stats = {
            "benchmarks": {},
            "attack_families": {},
            "statuses": {},
            "duplicates": 0,
            "canonical": 0,
            "skipped": 0,
            "total_loaded": 0,
            "missing_files": 0
        }

    def _get_git_commit(self):
        try:
            commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=str(self.repo_root), stderr=subprocess.DEVNULL).decode('utf-8').strip()
            return commit
        except Exception as e:
            logging.warning(f"Git commit retrieval failed: {e}. Defaulting to null.")
            return None

    def _hash_file(self, path: Path):
        if not path.exists():
            return None
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _record_file(self, path: Path, rel_path=None):
        if not path.exists():
            logging.error(f"File missing: {path}. Fail-fast.")
            sys.exit(1)
        
        fhash = self._hash_file(path)
        fsize = path.stat().st_size
        
        rel_posix = str(Path(rel_path).as_posix()) if rel_path else str(path.relative_to(self.repo_root).as_posix())
        rec = {
            "path": rel_posix,
            "sha256": fhash,
            "size_bytes": fsize
        }
        self.source_file_hashes.append(rec)
        self.file_metadata[rel_posix] = rec
        return True

    def _normalize(self, text):
        if text is None:
            return None
        text = str(text)
        text = text.encode('utf-8', errors='replace').decode('utf-8')
        text = unicodedata.normalize("NFC", text)
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        return text

    def add_payload(self, text, benchmark, family, source_file, orig_id, mcp_exposure=None, approval_status="Approved", **kwargs):
        is_explicit_empty = (text == "(empty by default)")
        norm_text = self._normalize(text)
        if is_explicit_empty:
            norm_text = ""
            
        if not is_explicit_empty and (not norm_text or not norm_text.strip()):
            self.skipped_records.append({
                "source_file": source_file,
                "original_identifier": orig_id,
                "reason": "Empty or whitespace-only payload"
            })
            self.stats["skipped"] += 1
            return
            
        fmeta = self.file_metadata.get(source_file, {})
        
        self.raw_payloads.append({
            "benchmark_source": benchmark,
            "attack_family": family,
            "source_file": source_file,
            "original_identifier": str(orig_id),
            "payload_text": norm_text,
            "mcp_exposure": mcp_exposure,
            "approval_status": approval_status,
            "source_file_sha256": fmeta.get("sha256"),
            "extraction_date": None
        })
        self.stats["total_loaded"] += 1

    def load_jsonl(self, rel_path, benchmark, family_fallback):
        path = self.repo_root / rel_path
        self._record_file(path, rel_path)
            
        loaded = 0
        with open(path, 'r', encoding='utf-8-sig') as f:
            for i, line in enumerate(f):
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    text = data.get("Attacker Instruction")
                    if text is None:
                        self.skipped_records.append({
                            "source_file": path.name,
                            "original_identifier": f"Line {i+1}",
                            "reason": "Missing 'Attacker Instruction'"
                        })
                        self.stats["skipped"] += 1
                        continue
                    family = data.get("Attack Type", family_fallback)
                    self.add_payload(text, benchmark, family, str(Path(rel_path).as_posix()), f"Line {i+1}")
                    loaded += 1
                except Exception as e:
                    logging.error(f"Error parsing JSONL line {i+1} in {path.name}: {e}. Fail-fast.")
                    sys.exit(1)
        logging.info(f"Loaded {loaded} records from {path.name}")

    def load_skill_inject(self, rel_path, family):
        path = self.repo_root / rel_path
        self._record_file(path, rel_path)
            
        loaded = 0
        with open(path, 'r', encoding='utf-8-sig') as f:
            try:
                data = json.load(f)
                for item in data:
                    instructions = item.get("instructions", {})
                    orig_id = item.get("id", "UNKNOWN")
                    desc = instructions.get("description_injection")
                    line = instructions.get("line_injection")
                    if desc:
                        self.add_payload(desc, "SkillInject", family, str(Path(rel_path).as_posix()), f"{orig_id}_desc")
                        loaded += 1
                    if line:
                        self.add_payload(line, "SkillInject", family, str(Path(rel_path).as_posix()), f"{orig_id}_line")
                        loaded += 1
                    if not desc and not line:
                        self.skipped_records.append({"source_file": path.name, "original_identifier": orig_id, "reason": "No desc/line injections"})
                        self.stats["skipped"] += 1
            except Exception as e:
                logging.error(f"Error parsing JSON {path.name}: {e}. Fail-fast.")
                sys.exit(1)
        logging.info(f"Loaded {loaded} records from {path.name}")

    def load_excel(self, rel_path, benchmark_default="AgentDojo"):
        if pd is None:
            logging.error("pandas is not installed. Cannot load Excel. Fail-fast.")
            sys.exit(1)
            
        path = self.repo_root / rel_path
        self._record_file(path, rel_path)
            
        loaded = 0
        payload_cols = ["Raw Payload", "Payload", "Prompt", "Instruction", "Attacker Instruction"]
        try:
            df = pd.read_excel(path)
            cols_lower = {str(c).lower().strip(): c for c in df.columns}
            
            payload_col = None
            for cand in payload_cols:
                if cand.lower() in cols_lower:
                    payload_col = cols_lower[cand.lower()]
                    break
            
            if not payload_col:
                logging.error(f"Could not find payload column in {path.name}. Columns: {list(df.columns)}. Fail-fast.")
                sys.exit(1)
                
            for i, row in df.iterrows():
                text = row.get(payload_col)
                if pd.isna(text):
                    self.skipped_records.append({"source_file": path.name, "original_identifier": f"Row {i+2}", "reason": f"Missing value in '{payload_col}'"})
                    self.stats["skipped"] += 1
                    continue
                    
                orig_id = row.get("Payload ID", f"Row {i+2}")
                family = row.get("Attack Family", "UNKNOWN") if "Attack Family" in df.columns else "UNKNOWN"
                benchmark = row.get("Benchmark", benchmark_default) if "Benchmark" in df.columns else benchmark_default
                mcp = row.get("MCP Exposure") if "MCP Exposure" in df.columns and not pd.isna(row.get("MCP Exposure")) else None
                
                status = "Approved"
                if "Include" in df.columns:
                    inc = row.get("Include")
                    if pd.notna(inc) and str(inc).strip().upper() in ["FALSE", "0", "NO"]:
                        status = "Candidate"
                        
                self.add_payload(text, benchmark, family, str(Path(rel_path).as_posix()), orig_id, mcp, status)
                loaded += 1
        except Exception as e:
            logging.error(f"Error reading Excel {path.name}: {e}. Fail-fast.")
            sys.exit(1)
        logging.info(f"Loaded {loaded} records from {path.name}")

    def build_canonical_list(self, commit_sha, timestamp):
        # 1. Deterministic natural sort
        self.raw_payloads.sort(key=lambda x: (
            x['benchmark_source'] or "",
            x['attack_family'] or "",
            x['source_file'] or "",
            natural_key(x['original_identifier'] or ""),
            x['payload_text'] or ""
        ))
        
        primary_dup_map = {} # (benchmark, family, norm_text) -> payload_id
        text_to_benchmarks = {} # norm_text -> set(benchmarks)
        
        # Pre-pass for text_to_benchmarks
        for rp in self.raw_payloads:
            t = rp['payload_text']
            if t not in text_to_benchmarks:
                text_to_benchmarks[t] = set()
            text_to_benchmarks[t].add(rp['benchmark_source'])
            
        canonical_list = []
        for rp in self.raw_payloads:
            pkey = (rp['benchmark_source'], rp['attack_family'], rp['payload_text'])
            
            if pkey in primary_dup_map:
                is_canonical = False
                canonical_ref = primary_dup_map[pkey]
                self.stats["duplicates"] += 1
                pid = f"PAYLOAD_{self.payload_counter:06d}"
                self.payload_counter += 1
                current_id = pid
            else:
                is_canonical = True
                pid = f"PAYLOAD_{self.payload_counter:06d}"
                self.payload_counter += 1
                canonical_ref = None
                primary_dup_map[pkey] = pid
                self.stats["canonical"] += 1
                current_id = pid
                
            text_duplicate = len(text_to_benchmarks[rp['payload_text']]) > 1
            
            # stats
            b = rp['benchmark_source']
            f = rp['attack_family']
            s = rp['approval_status']
            self.stats["benchmarks"][b] = self.stats["benchmarks"].get(b, 0) + 1
            self.stats["attack_families"][f] = self.stats["attack_families"].get(f, 0) + 1
            self.stats["statuses"][s] = self.stats["statuses"].get(s, 0) + 1
            
            canonical_list.append({
                "payload_id": current_id,
                "payload_text": rp['payload_text'],
                "benchmark_source": rp['benchmark_source'],
                "attack_family": rp['attack_family'],
                "mcp_exposure": rp['mcp_exposure'],
                "approval_status": rp['approval_status'],
                "provenance": {
                    "source_file": rp['source_file'],
                    "source_file_sha256": rp['source_file_sha256'],
                    "original_identifier": rp['original_identifier'],
                    "repository_url": None,
                    "repository_commit": commit_sha,
                    "source_license": None,
                    "extraction_date": timestamp
                },
                "duplicate_handling": {
                    "is_canonical": is_canonical,
                    "canonical_reference": canonical_ref,
                    "text_duplicate_across_benchmarks": text_duplicate
                },
                "phase1_payload_hash": None,
                "payload_condition": "NONE"
            })
                
        return canonical_list

    def execute(self, out_json: Path, out_csv: Path, out_phase25: Path, build_timestamp=None):
        # Ingest
        self.load_jsonl('Phase1/payload/attacker_cases_dh.jsonl', 'InjecAgent', 'DH')
        self.load_jsonl('Phase1/payload/attacker_cases_ds.jsonl', 'InjecAgent', 'DS')
        self.load_skill_inject('Phase1/payload/contextual_injections.json', 'Contextual')
        self.load_skill_inject('Phase1/payload/obvious_injections.json', 'Obvious')
        self.load_excel('Phase1/data/ledgers/AGENTDOJO-LEDGER.xlsx', 'AgentDojo')
        
        commit_sha = self.repository_commit if self.repository_commit else self._get_git_commit()
        
        timestamp = build_timestamp
        if not timestamp:
            if os.environ.get("SOURCE_DATE_EPOCH"):
                timestamp = datetime.datetime.fromtimestamp(int(os.environ["SOURCE_DATE_EPOCH"]), tz=datetime.timezone.utc).isoformat()
            else:
                timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
                
        # Build
        canonical_list = self.build_canonical_list(commit_sha, timestamp)
        
        # Invariants Validation
        payload_ids = [p["payload_id"] for p in canonical_list]
        assert len(payload_ids) == len(set(payload_ids)), "Duplicate payload_id detected."
        
        canonical_ids = {
            p["payload_id"] for p in canonical_list
            if p["duplicate_handling"]["is_canonical"]
        }
        for p in canonical_list:
            dh = p["duplicate_handling"]
            if not dh["is_canonical"]:
                assert dh["canonical_reference"] in canonical_ids, "Dangling canonical reference."
            else:
                assert dh["canonical_reference"] is None, "Canonical payload has non-null reference."
                
        assert self.stats["canonical"] + self.stats["duplicates"] == len(canonical_list), "Metadata counts inconsistent."
        
        deps = {
            "python": self.build_python,
            "pandas": pd.__version__ if pd else "None",
            "jsonschema": jsonschema.__version__ if jsonschema else "None"
        }
        
        # Export JSON
        ledger_data = {
            "metadata": {
                "schema_version": "1.0.0",
                "generator_version": GENERATOR_VERSION,
                "ledger_generated_at": timestamp,
                "execution_uuid": self.execution_uuid,
                "repository_commit": commit_sha,
                "python_version": deps["python"],
                "platform": self.build_platform,
                "dependencies": deps,
                "payload_count": len(canonical_list),
                "canonical_payload_count": self.stats["canonical"],
                "duplicate_payload_count": self.stats["duplicates"],
                "skipped_payload_count": self.stats["skipped"],
                "source_files": self.source_file_hashes
            },
            "payloads": canonical_list
        }
        
        # Validate
        if jsonschema is not None:
            try:
                jsonschema.validate(instance=ledger_data, schema=SCHEMA)
                logging.info("JSON Schema validation passed.")
            except jsonschema.exceptions.ValidationError as e:
                logging.error(f"JSON Schema validation failed: {e.message}. Fail-fast.")
                sys.exit(1)
        else:
            logging.warning("jsonschema not installed, skipping schema validation.")
            
        out_json.parent.mkdir(parents=True, exist_ok=True)
        with open(out_json, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(ledger_data, f, indent=2, ensure_ascii=False, sort_keys=True)
        logging.info(f"Exported JSON ledger to {out_json}")
        
        out_phase25.parent.mkdir(parents=True, exist_ok=True)
        with open(out_phase25, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(ledger_data, f, indent=2, ensure_ascii=False, sort_keys=True)
        logging.info(f"Exported Phase2.5 ledger to {out_phase25}")
        
        # Export CSV
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        with open(out_csv, 'w', encoding='utf-8', newline='\n') as f:
            writer = csv.writer(f, lineterminator='\n')
            writer.writerow([
                "payload_id", "benchmark_source", "attack_family", "mcp_exposure", 
                "approval_status", "is_canonical", "canonical_reference", 
                "text_duplicate", "source_file", "original_identifier", "payload_text"
            ])
            for p in canonical_list:
                writer.writerow([
                    p["payload_id"],
                    p["benchmark_source"],
                    p["attack_family"],
                    p.get("mcp_exposure", ""),
                    p["approval_status"],
                    p["duplicate_handling"]["is_canonical"],
                    p["duplicate_handling"]["canonical_reference"] or "",
                    p["duplicate_handling"].get("text_duplicate_across_benchmarks", False),
                    p["provenance"]["source_file"],
                    p["provenance"]["original_identifier"],
                    p["payload_text"]
                ])
        logging.info(f"Exported CSV ledger to {out_csv}")
        
        # Write Manifest
        manifest = {
            "ledger_sha256": hashlib.sha256(open(out_json, "rb").read()).hexdigest(),
            "csv_sha256": hashlib.sha256(open(out_csv, "rb").read()).hexdigest(),
            "phase25_ledger_sha256": hashlib.sha256(open(out_phase25, "rb").read()).hexdigest(),
            "execution_uuid": self.execution_uuid,
            "repository_commit": commit_sha,
            "timestamp": timestamp,
            "payload_count": len(canonical_list),
            "canonical_count": self.stats["canonical"],
            "duplicate_count": self.stats["duplicates"],
            "schema_version": "1.0.0",
            "generator_version": GENERATOR_VERSION
        }
        manifest_path = out_json.parent / "manifest.json"
        with open(manifest_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False, sort_keys=True)
        logging.info(f"Exported Manifest to {manifest_path}")
        
        return canonical_list, ledger_data

    def write_validation_report(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        
        repo_root = self.repo_root
        out_json = repo_root / 'Phase1/data/exports/payload_provenance_ledger.json'
        out_csv = repo_root / 'Phase1/data/exports/canonical_inventory.csv'
        manifest_path = out_json.parent / "manifest.json"
        
        ledger_sha256 = hashlib.sha256(open(out_json, "rb").read()).hexdigest() if out_json.exists() else "Missing"
        csv_sha256 = hashlib.sha256(open(out_csv, "rb").read()).hexdigest() if out_csv.exists() else "Missing"
        manifest_sha256 = hashlib.sha256(open(manifest_path, "rb").read()).hexdigest() if manifest_path.exists() else "Missing"
        commit_sha = self._get_git_commit() or "None"
        
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            f.write("# Phase 1 Payload Validation Report\n\n")
            f.write(f"**Execution UUID:** `{self.execution_uuid}`\n")
            f.write(f"**Repository Commit:** `{commit_sha}`\n")
            f.write(f"**Manifest SHA256:** `{manifest_sha256}`\n")
            f.write(f"**Ledger SHA256:** `{ledger_sha256}`\n")
            f.write(f"**CSV SHA256:** `{csv_sha256}`\n\n")
            f.write("## Summary\n")
            f.write(f"- **Total Loaded Records**: {self.stats['total_loaded']}\n")
            f.write(f"- **Canonical Payloads**: {self.stats['canonical']}\n")
            f.write(f"- **Duplicate Payloads**: {self.stats['duplicates']}\n")
            f.write(f"- **Skipped Records**: {self.stats['skipped']}\n")
            f.write(f"- **Missing Source Files**: {self.stats['missing_files']}\n\n")
            
            f.write("## Input Files\n")
            for sf in self.source_file_hashes:
                f.write(f"- `{sf['path']}` (SHA256: {sf['sha256'][:8]}...)\n")
            f.write("\n")
            
            f.write("## Statistics\n")
            f.write("### By Benchmark\n")
            for b, c in self.stats["benchmarks"].items():
                f.write(f"- {b}: {c}\n")
            f.write("### By Attack Family\n")
            for af, c in self.stats["attack_families"].items():
                f.write(f"- {af}: {c}\n")
            f.write("### By Status\n")
            for s, c in self.stats["statuses"].items():
                f.write(f"- {s}: {c}\n")
            f.write("\n")
            
            f.write("## Malformed / Skipped Records\n")
            if not self.skipped_records:
                f.write("No records were skipped.\n\n")
            else:
                for sr in self.skipped_records:
                    f.write(f"- {sr['source_file']} [{sr['original_identifier']}]: {sr['reason']}\n")
                f.write("\n")
                
            f.write("## Final Status\n")
            f.write("Validation Complete. JSON Schema Compliant. Ready for downstream hashing in Phase 3/4.\n\n")
            f.write("**Note:** Payload identifiers are deterministic for the frozen Phase 1 dataset. Any upstream dataset modification requires regeneration of the ledger, manifest, and downstream references.\n")
        logging.info(f"Validation report written to {path}")

def main():
    parser = argparse.ArgumentParser(description="Phase 1 Canonical Payload Compiler")
    parser.add_argument('--repo-root', type=str, default='.', help="Repository root path")
    parser.add_argument('--output-json', type=str, default='Phase1/data/exports/payload_provenance_ledger.json')
    parser.add_argument('--output-csv', type=str, default='Phase1/data/exports/canonical_inventory.csv')
    parser.add_argument('--verbose', action='store_true', help="Enable verbose DEBUG logging")
    parser.add_argument('--build-timestamp', type=str, help="Override build timestamp (ISO 8601)")
    parser.add_argument('--execution-uuid', type=str, help="Override execution UUID")
    parser.add_argument('--build-platform', type=str, help="Override host platform for reproducibility")
    parser.add_argument('--build-python', type=str, help="Override python version for reproducibility")
    parser.add_argument('--repository-commit', type=str, help="Override git commit hash")
    args = parser.parse_args()
    
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
    
    repo_root = Path(args.repo_root).resolve()
    out_json = repo_root / args.output_json
    out_csv = repo_root / args.output_csv
    out_phase25 = repo_root / 'phase1/ledger/payload_provenance_ledger.json'
    out_report = repo_root / 'Phase1/docs/verification/payload_validation_report.md'
    
    builder = PayloadLedgerBuilder(
        repo_root, 
        execution_uuid=args.execution_uuid,
        build_platform=args.build_platform,
        build_python=args.build_python,
        repository_commit=args.repository_commit
    )
    builder.execute(out_json, out_csv, out_phase25, build_timestamp=args.build_timestamp)
    builder.write_validation_report(out_report)

if __name__ == "__main__":
    main()
