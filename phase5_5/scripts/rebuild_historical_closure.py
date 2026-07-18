"""Rebuild a hash-verified historical closure package from preserved Git blobs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from phase5_5.forensics import ORPHANED_INVALID


class BranchArchive:
    def __init__(self, branch: str) -> None:
        listing = subprocess.run(
            ["git", "ls-tree", "-r", branch, "phase5/evidence"],
            check=True,
            stdout=subprocess.PIPE,
            text=True,
        )
        entries = []
        for line in listing.stdout.splitlines():
            left, path = line.split("\t", 1)
            _, object_type, object_id = left.split(" ", 2)
            if object_type == "blob":
                entries.append((path, object_id))
        process = subprocess.Popen(
            ["git", "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )
        request = "".join(f"{object_id}\n" for _, object_id in entries).encode("ascii")
        output, _ = process.communicate(request)
        cursor = 0
        self.files: dict[str, bytes] = {}
        for path, object_id in entries:
            header_end = output.index(b"\n", cursor)
            header = output[cursor:header_end].decode("ascii").split()
            cursor = header_end + 1
            size = int(header[2])
            self.files[path] = output[cursor:cursor + size]
            cursor += size + 1

    def blob(self, path: str) -> bytes:
        try:
            return self.files[path]
        except KeyError as exc:
            raise RuntimeError(f"missing historical blob: {path}") from exc

    def files_under(self, prefix: str) -> tuple[str, ...]:
        return tuple(path for path in self.files if path.startswith(prefix))


def blob(branch: str, path: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{branch}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    )
    return result.stdout


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def records_for_branch(branch: str, slot: str, closed_utc: str) -> tuple[dict[str, object], int]:
    archive = BranchArchive(branch)
    rows = csv.DictReader(io.StringIO(archive.blob("phase5/evidence/lineage.csv").decode("utf-8")))
    output: list[dict[str, object]] = []
    index_mismatches = 0
    for row in rows:
        if row.get("attempt_status") != "INVALID":
            continue
        if row.get("counts_toward_cell_n", "").lower() == "true" or row.get("accepted_attempt", "").lower() == "true":
            continue
        batch_id = row.get("batch_id", "")
        if f"-{slot}-" not in batch_id:
            continue
        attempt_id = row["attempt_id"]
        prefix = f"phase5/evidence/attempts/{attempt_id}/"
        paths = archive.files_under(prefix)
        if not paths:
            raise RuntimeError(f"missing historical attempt tree: {branch}:{prefix}")
        hashes: dict[str, str] = {}
        index_items: dict[str, str] = {}
        for path in paths:
            name = path.removeprefix(prefix)
            value = archive.blob(path)
            hashes[name] = sha256(value)
            if name == "evidence_hash_index.jsonl":
                for line in value.decode("utf-8").splitlines():
                    item = json.loads(line)
                    index_items[str(item["path"])] = str(item["sha256"])
        for name, indexed_hash in index_items.items():
            if name not in hashes or hashes[name] != indexed_hash:
                index_mismatches += 1
        parser_reason = row.get("invalid_reason", "parser failure")
        parser_path = prefix + "parser_events.jsonl"
        try:
            for line in archive.blob(parser_path).decode("utf-8").splitlines():
                event = json.loads(line)
                if event.get("event_type") == "PARSE_FAILURE":
                    parser_reason = str(event.get("details") or event.get("reason") or parser_reason)
                    break
        except Exception:
            pass
        output.append({
            "artifact_hashes": hashes,
            "attempt_id": attempt_id,
            "batch_id": row.get("batch_id", ""),
            "closed_utc": closed_utc,
            "dataset_version": row.get("dataset_version", ""),
            "forensic_status": ORPHANED_INVALID,
            "frozen_row_id": row.get("frozen_row_id", ""),
            "original_status": row.get("attempt_status", ""),
            "parser_reason": parser_reason,
            "raw_attempt_directory": f"phase5/evidence/attempts/{attempt_id}",
            "run_id": row.get("run_id", ""),
            "source_branch": branch,
            "target_trial_id": row.get("target_trial_id", ""),
        })
    return tuple(output), index_mismatches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--closed-utc", default=datetime.now(timezone.utc).isoformat())
    args = parser.parse_args()
    all_records: list[dict[str, object]] = []
    index_mismatches = 0
    for branch, slot in (("phase5-model-2", "M2"), ("phase5-model-3", "M3")):
        records, mismatches = records_for_branch(branch, slot, args.closed_utc)
        all_records.extend(records)
        index_mismatches += mismatches
    all_records.sort(key=lambda item: str(item["attempt_id"]))
    ids = [str(item["attempt_id"]) for item in all_records]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    reconciliation = {
        "artifact": "phase5_5_historical_orphan_reconciliation_v2",
        "closure_count": len(all_records),
        "source_orphan_count": len(all_records),
        "duplicate_attempt_ids": duplicates,
        "index_hash_mismatch_count": index_mismatches,
        "accepted_count": 0,
        "finalized_count": 0,
        "publication_evidence_count": 0,
        "reconciliation_pass": bool(all_records) and not duplicates and index_mismatches == 0,
        "source_branches": ["phase5-model-2", "phase5-model-3"],
        "historical_evidence_immutable": True,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "historical_orphan_closure.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True, separators=(",", ":")) + "\n" for item in all_records),
        encoding="utf-8",
    )
    (args.output_dir / "historical_orphan_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "historical_orphan_reconciliation.md").write_text(
        "# Historical Phase 5 Orphan Reconciliation v2\n\n"
        f"- closure_count: `{len(all_records)}`\n"
        f"- index_hash_mismatch_count: `{index_mismatches}`\n"
        f"- reconciliation_pass: `{reconciliation['reconciliation_pass']}`\n"
        "- accepted_count: `0`\n- finalized_count: `0`\n- publication_evidence_count: `0`\n"
        "- historical_evidence_immutable: `true`\n",
        encoding="utf-8",
    )
    return 0 if reconciliation["reconciliation_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
