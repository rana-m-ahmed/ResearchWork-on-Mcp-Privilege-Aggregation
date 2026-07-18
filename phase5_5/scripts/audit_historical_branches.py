"""Generate append-only closure and reconciliation reports for old evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from phase5_5.forensics import discover_orphan_closures, reconcile_closures, write_append_only_closure


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--branch", action="append", required=True, help="BRANCH_NAME=EVIDENCE_ROOT")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    records = []
    for value in args.branch:
        try:
            branch, root = value.split("=", 1)
        except ValueError as exc:
            raise SystemExit("--branch must use BRANCH_NAME=EVIDENCE_ROOT") from exc
        records.extend(
            discover_orphan_closures(Path(root), source_branch=branch)
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    ledger = args.output_dir / "historical_orphan_closure.jsonl"
    write_append_only_closure(records, ledger)
    reconciliation = reconcile_closures(records)
    reconciliation["source_branches"] = sorted({record.source_branch for record in records})
    reconciliation["historical_evidence_immutable"] = True
    (args.output_dir / "historical_orphan_reconciliation.json").write_text(
        json.dumps(reconciliation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "historical_orphan_reconciliation.md").write_text(
        "# Historical Phase 5 Orphan Reconciliation\n\n"
        f"- closure_count: `{reconciliation['closure_count']}`\n"
        f"- reconciliation_pass: `{reconciliation['reconciliation_pass']}`\n"
        f"- accepted_count: `{reconciliation['accepted_count']}`\n"
        f"- finalized_count: `{reconciliation['finalized_count']}`\n"
        f"- publication_evidence_count: `{reconciliation['publication_evidence_count']}`\n"
        "- historical_evidence_immutable: `true`\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
