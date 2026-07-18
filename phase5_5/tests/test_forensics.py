from __future__ import annotations

import csv
import json

from phase5_5.forensics import (
    ORPHANED_INVALID,
    discover_orphan_closures,
    reconcile_closures,
    write_append_only_closure,
)


def test_discover_and_reconcile_orphan_closure_without_rewriting_history(tmp_path) -> None:
    evidence = tmp_path / "evidence"
    attempt = evidence / "attempts" / "P5ATT-T1-A000-ABCDEF12"
    attempt.mkdir(parents=True)
    (attempt / "model_outputs.jsonl").write_text('{"raw_output":"bad"}\n', encoding="utf-8")
    (attempt / "parser_events.jsonl").write_text(
        json.dumps({"event_type": "PARSE_FAILURE", "details": "incomplete output"}) + "\n",
        encoding="utf-8",
    )
    lineage = evidence / "lineage.csv"
    with lineage.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "dataset_version", "frozen_row_id", "target_trial_id", "attempt_id",
                "attempt_index", "parent_attempt_id", "run_id", "batch_id",
                "attempt_status", "invalid_reason", "counts_toward_cell_n", "accepted_attempt",
                "raw_attempt_directory",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "dataset_version": "P5-DV-1.0.2",
            "frozen_row_id": "core-1",
            "target_trial_id": "T1",
            "attempt_id": "P5ATT-T1-A000-ABCDEF12",
            "attempt_index": "0",
            "parent_attempt_id": "",
            "run_id": "RUN-M2",
            "batch_id": "BATCH-M2-1",
            "attempt_status": "INVALID",
            "invalid_reason": "reject at parser",
            "counts_toward_cell_n": "False",
            "accepted_attempt": "False",
            "raw_attempt_directory": str(attempt),
        })

    records = discover_orphan_closures(evidence, source_branch="phase5-model-2", closed_utc="2026-01-01T00:00:00Z")

    assert len(records) == 1
    assert records[0].forensic_status == ORPHANED_INVALID
    assert records[0].parser_reason == "incomplete output"
    assert (attempt / "parser_events.jsonl").exists()
    assert reconcile_closures(records)["reconciliation_pass"] is True


def test_closure_ledger_rejects_history_loss(tmp_path) -> None:
    path = tmp_path / "closure.jsonl"
    first = {
        "attempt_id": "A1",
        "forensic_status": ORPHANED_INVALID,
    }
    path.write_text(json.dumps(first) + "\n", encoding="utf-8")

    write_append_only_closure([], path)
    assert json.loads(path.read_text(encoding="utf-8"))["attempt_id"] == "A1"
