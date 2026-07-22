"""Fail-closed resolution of durable Phase 5.5 official checkpoints."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from phase5.attempts import AttemptLineageRecord, AttemptLineageStore
from phase5.attempts.lineage import render_lineage_csv
from phase5.domain.errors import MissingFrozenSettingError, SchemaInvariantError


CHECKPOINT_ARTIFACT = "phase5_5_trial_checkpoint_v2"
LEGACY_SUPERSESSION_ARTIFACT = "phase5_5_campaign_supersession_v1"
SOURCE_BOUND_SUPERSESSION_ARTIFACT = "phase5_5_campaign_supersession_v2"
_TERMINAL_STATUSES = frozenset({"INVALID", "OFFICIAL_ACCEPTED", "ORPHAN"})


class ResumeMode(str, Enum):
    NEW = "NEW"
    RESUME = "RESUME"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class OfficialResumeResolution:
    mode: ResumeMode
    run_id: str
    checkpoint_sequence: int
    completed_target_count: int
    diagnostic: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _portable_text_sha256(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _text_sha256_variants(path: Path) -> frozenset[str]:
    """Return hashes for the same text under LF and CRLF materialization."""

    raw = path.read_bytes()
    lf = raw.replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    return frozenset(hashlib.sha256(data).hexdigest() for data in (raw, lf, crlf))


def _require_lineage_sha256(payload: Mapping[str, Any], path: Path, label: str) -> None:
    """Validate a lineage digest across Git's Windows newline materialization."""

    raw = path.read_bytes()
    accepted = {hashlib.sha256(raw).hexdigest()}
    if b"\r\n" in raw:
        accepted.add(hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest())
    actual = payload.get("lineage_sha256")
    if actual not in accepted:
        raise SchemaInvariantError(
            f"{label} lineage_sha256 mismatch: expected one of {sorted(accepted)!r}, got {actual!r}"
        )


def _load_object(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SchemaInvariantError(f"{label} is unreadable: {path.as_posix()}") from exc
    if not isinstance(value, dict):
        raise SchemaInvariantError(f"{label} must be a JSON object: {path.as_posix()}")
    return value


def _require_equal(payload: Mapping[str, Any], key: str, expected: object, label: str) -> None:
    if payload.get(key) != expected:
        raise SchemaInvariantError(
            f"{label} {key} mismatch: expected {expected!r}, got {payload.get(key)!r}"
        )


def _run_prefix(dataset_version: str, model_slot: str) -> str:
    return f"P5RUN-{dataset_version}-{model_slot}-"


def _current_records(
    records: tuple[AttemptLineageRecord, ...],
    *,
    dataset_version: str,
    model_slot: str,
) -> tuple[AttemptLineageRecord, ...]:
    prefix = _run_prefix(dataset_version, model_slot)
    relevant = tuple(record for record in records if record.dataset_version == dataset_version)
    foreign = sorted({record.run_id for record in relevant if not record.run_id.startswith(prefix)})
    if foreign:
        raise SchemaInvariantError(
            f"current-dataset lineage contains runs outside {model_slot}: {foreign}"
        )
    return relevant


def _checkpoint_documents(checkpoint_root: Path) -> dict[str, list[tuple[Path, dict[str, Any]]]]:
    documents: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    if not checkpoint_root.exists():
        return documents
    for path in sorted(checkpoint_root.glob("*/checkpoint-*.json")):
        payload = _load_object(path, "official checkpoint")
        run_id = payload.get("run_id")
        if not isinstance(run_id, str) or not run_id:
            raise SchemaInvariantError(f"official checkpoint has no run_id: {path.as_posix()}")
        documents.setdefault(run_id, []).append((path, payload))
    return documents


def _records_sha256(records: tuple[AttemptLineageRecord, ...]) -> str:
    return hashlib.sha256(render_lineage_csv(records).encode("utf-8")).hexdigest()


def _validated_superseded_runs(
    *,
    evidence_root: Path,
    relevant: tuple[AttemptLineageRecord, ...],
    documents: Mapping[str, list[tuple[Path, dict[str, Any]]]],
    model_slot: str,
    dataset_version: str,
) -> frozenset[str]:
    supersession_root = evidence_root / "supersessions"
    if not supersession_root.exists():
        return frozenset()
    records_by_run: dict[str, tuple[AttemptLineageRecord, ...]] = {}
    for run_id in sorted({record.run_id for record in relevant}):
        records_by_run[run_id] = tuple(record for record in relevant if record.run_id == run_id)
    superseded: set[str] = set()
    for path in sorted(supersession_root.glob("*.json")):
        payload = _load_object(path, "campaign supersession")
        label = f"campaign supersession {path.as_posix()}"
        artifact = payload.get("artifact")
        if artifact not in {LEGACY_SUPERSESSION_ARTIFACT, SOURCE_BOUND_SUPERSESSION_ARTIFACT}:
            raise SchemaInvariantError(f"{label} has an unsupported artifact version")
        _require_equal(payload, "model_slot", model_slot, label)
        _require_equal(payload, "dataset_version", dataset_version, label)
        authorization = (
            "explicit_user_authorization_2026-07-22"
            if artifact == LEGACY_SUPERSESSION_ARTIFACT
            else "explicit_user_authorization_2026-07-23"
        )
        _require_equal(payload, "authorization_basis", authorization, label)
        run_id = payload.get("superseded_run_id")
        if not isinstance(run_id, str) or not run_id.startswith(_run_prefix(dataset_version, model_slot)):
            raise SchemaInvariantError(f"{label} has an invalid superseded_run_id")
        if run_id in superseded:
            raise SchemaInvariantError(f"multiple campaign supersessions exist for {run_id}")
        run_records = records_by_run.get(run_id)
        if not run_records:
            raise SchemaInvariantError(f"{label} does not identify existing current-dataset lineage")
        _require_equal(payload, "superseded_lineage_count", len(run_records), label)
        _require_equal(payload, "superseded_lineage_sha256", _records_sha256(run_records), label)
        status_counts = {
            status: sum(record.attempt_status == status for record in run_records)
            for status in sorted({record.attempt_status for record in run_records})
        }
        _require_equal(payload, "status_counts", status_counts, label)

        checkpoint_entries = documents.get(run_id, [])
        source_bound = any(document.get("artifact") == CHECKPOINT_ARTIFACT for _, document in checkpoint_entries)
        if artifact == LEGACY_SUPERSESSION_ARTIFACT and source_bound:
            raise SchemaInvariantError(f"{label} cannot supersede a source-bound v2 campaign")
        if artifact == SOURCE_BOUND_SUPERSESSION_ARTIFACT:
            if not checkpoint_entries or not all(
                document.get("artifact") == CHECKPOINT_ARTIFACT for _, document in checkpoint_entries
            ):
                raise SchemaInvariantError(f"{label} must identify one source-bound v2 checkpoint chain")
            _require_equal(payload, "reason", "canceled_partial_official_run_before_remediation", label)
            _require_equal(payload, "replacement_run_required", True, label)
            source_commit = payload.get("source_commit")
            batch_sha = payload.get("batch_manifest_sha256")
            plan_sha = payload.get("run_plan_sha256")
            if not all(isinstance(value, str) for value in (source_commit, batch_sha, plan_sha)):
                raise SchemaInvariantError(f"{label} lacks its frozen source binding")
            latest = _validate_checkpoint_chain(
                checkpoint_entries,
                run_id=run_id,
                model_slot=model_slot,
                dataset_version=dataset_version,
                source_commit=source_commit,
                batch_manifest_sha256=batch_sha,
                run_plan_sha256=plan_sha,
            )
            _require_equal(latest, "run_lineage_count", len(run_records), label)
            _require_equal(latest, "last_attempt_id", run_records[-1].attempt_id, label)
            _require_equal(latest, "last_target_trial_id", run_records[-1].target_trial_id, label)
            if _is_complete(evidence_root, run_id):
                raise SchemaInvariantError(f"{label} cannot supersede a completed campaign")
        checkpoint_hashes = {
            checkpoint_path.relative_to(evidence_root).as_posix(): _portable_text_sha256(checkpoint_path)
            for checkpoint_path, _ in checkpoint_entries
        }
        expected_hashes = payload.get("checkpoint_sha256")
        if artifact == LEGACY_SUPERSESSION_ARTIFACT:
            if not isinstance(expected_hashes, Mapping) or set(expected_hashes) != set(checkpoint_hashes):
                raise SchemaInvariantError(f"{label} checkpoint_sha256 mismatch")
            for checkpoint_path, _ in checkpoint_entries:
                relative = checkpoint_path.relative_to(evidence_root).as_posix()
                if expected_hashes[relative] not in _text_sha256_variants(checkpoint_path):
                    raise SchemaInvariantError(f"{label} checkpoint_sha256 mismatch")
        else:
            _require_equal(payload, "checkpoint_sha256", checkpoint_hashes, label)
        _require_equal(payload, "checkpoint_count", len(checkpoint_entries), label)
        superseded.add(run_id)
    return frozenset(superseded)


def _validate_checkpoint_chain(
    entries: list[tuple[Path, dict[str, Any]]],
    *,
    run_id: str,
    model_slot: str,
    dataset_version: str,
    source_commit: str,
    batch_manifest_sha256: str,
    run_plan_sha256: str,
) -> dict[str, Any]:
    ordered = sorted(entries, key=lambda item: item[1].get("checkpoint_sequence", -1))
    for expected_sequence, (path, payload) in enumerate(ordered, start=1):
        label = f"checkpoint {path.as_posix()}"
        _require_equal(payload, "artifact", CHECKPOINT_ARTIFACT, label)
        _require_equal(payload, "checkpoint_sequence", expected_sequence, label)
        _require_equal(payload, "run_id", run_id, label)
        _require_equal(payload, "model_slot", model_slot, label)
        _require_equal(payload, "dataset_version", dataset_version, label)
        _require_equal(payload, "source_commit", source_commit, label)
        _require_equal(payload, "batch_manifest_sha256", batch_manifest_sha256, label)
        _require_equal(payload, "run_plan_sha256", run_plan_sha256, label)
    if not ordered:
        raise SchemaInvariantError(f"resume run has no checkpoints: {run_id}")
    return ordered[-1][1]


def _is_complete(evidence_root: Path, run_id: str) -> bool:
    publication_root = evidence_root / "publications" / run_id
    manifest_path = publication_root / "official_publication_manifest.json"
    receipt_path = publication_root / "official_publication_receipt.json"
    if not manifest_path.exists() and not receipt_path.exists():
        return False
    if not manifest_path.is_file() or not receipt_path.is_file():
        raise SchemaInvariantError("official completion marker is incomplete")
    manifest = _load_object(manifest_path, "official publication manifest")
    receipt = _load_object(receipt_path, "official publication receipt")
    _require_equal(manifest, "run_id", run_id, "official publication manifest")
    _require_equal(receipt, "run_id", run_id, "official publication receipt")
    return True


def _validate_attempt_evidence(evidence_root: Path, record: AttemptLineageRecord) -> None:
    attempts_root = (evidence_root / "attempts").resolve()
    # The lineage path is authoritative for the physical evidence location.
    # Current campaigns use attempts/<run_id>/<attempt_id>; legacy evidence
    # remains valid at attempts/<attempt_id>.
    recorded_root = Path(record.raw_attempt_directory)
    if not recorded_root.is_absolute():
        attempt_root = (evidence_root.parent.parent / recorded_root).resolve()
    else:
        try:
            attempt_root = recorded_root.resolve()
            attempt_root.relative_to(attempts_root)
        except ValueError:
            parts = recorded_root.as_posix().split("/")
            marker = ("phase5_5", "evidence", "attempts")
            marker_start = next(
                (index for index in range(len(parts) - len(marker) + 1)
                 if tuple(parts[index:index + len(marker)]) == marker),
                None,
            )
            if marker_start is None:
                raise SchemaInvariantError(
                    f"resume attempt directory is outside the evidence root: {record.attempt_id}"
                )
            suffix = parts[marker_start + len(marker):]
            if not suffix or any(part in {"", ".", ".."} for part in suffix):
                raise SchemaInvariantError(f"resume attempt directory is not canonical: {record.attempt_id}")
            attempt_root = attempts_root.joinpath(*suffix).resolve()
    try:
        attempt_root.relative_to(attempts_root)
    except ValueError as exc:
        raise SchemaInvariantError(f"resume attempt escapes the evidence root: {record.attempt_id}") from exc
    if not attempt_root.is_dir():
        raise SchemaInvariantError(f"resume attempt directory is missing: {record.attempt_id}")

    index_path = attempt_root / "evidence_hash_index.jsonl"
    if not index_path.is_file():
        raise SchemaInvariantError(f"resume attempt hash index is missing: {record.attempt_id}")
    indexed: set[str] = set()
    for line_number, line in enumerate(index_path.read_text(encoding="utf-8").splitlines(), start=1):
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SchemaInvariantError(
                f"resume attempt hash index is malformed at line {line_number}: {record.attempt_id}"
            ) from exc
        if not isinstance(item, dict):
            raise SchemaInvariantError(f"resume attempt hash entry is not an object: {record.attempt_id}")
        relative = item.get("path")
        digest = item.get("sha256")
        size = item.get("bytes")
        if not isinstance(relative, str) or Path(relative).name != relative or relative in indexed:
            raise SchemaInvariantError(f"resume attempt hash path is non-canonical: {record.attempt_id}")
        candidate = attempt_root / relative
        if not candidate.is_file() or _sha256(candidate) != digest or candidate.stat().st_size != size:
            raise SchemaInvariantError(f"resume attempt evidence hash mismatch: {record.attempt_id}/{relative}")
        indexed.add(relative)

    required = {"attempt_manifest.json", "attempt_events.jsonl", "grader_evidence.json"}
    if not required.issubset(indexed):
        raise SchemaInvariantError(f"resume attempt hash index lacks required evidence: {record.attempt_id}")
    manifest = _load_object(attempt_root / "attempt_manifest.json", "resume attempt manifest")
    for key, expected in (
        ("attempt_id", record.attempt_id),
        ("target_trial_id", record.target_trial_id),
        ("run_id", record.run_id),
        ("dataset_version", record.dataset_version),
        ("batch_id", record.batch_id),
    ):
        _require_equal(manifest, key, expected, f"resume attempt manifest {record.attempt_id}")
    grader = _load_object(attempt_root / "grader_evidence.json", "resume grader evidence")
    if grader.get("official_trial") is not True or not isinstance(grader.get("analysis_eligible_trial"), bool):
        raise SchemaInvariantError(f"resume grader evidence is not an eligible official record: {record.attempt_id}")
    if record.attempt_status != "ORPHAN":
        events = (attempt_root / "attempt_events.jsonl").read_text(encoding="utf-8").splitlines()
        try:
            final_event = json.loads(events[-1])
        except (IndexError, json.JSONDecodeError) as exc:
            raise SchemaInvariantError(f"resume attempt event log is incomplete: {record.attempt_id}") from exc
        if not isinstance(final_event, dict) or final_event.get("event_type") != "FINALIZED":
            raise SchemaInvariantError(f"resume attempt is not finalized: {record.attempt_id}")


def resolve_official_resume(
    *,
    root: Path,
    model_slot: str,
    dataset_version: str,
    source_commit: str,
    batch_manifest_sha256: str,
    run_plan_sha256: str,
    proposed_run_id: str,
) -> OfficialResumeResolution:
    """Resolve a new, resumable, or completed campaign without guessing."""

    normalized_root = root.resolve()
    slot = model_slot.upper()
    if slot not in {"M1", "M2", "M3", "M4"}:
        raise MissingFrozenSettingError(f"unsupported model slot: {model_slot}")
    if len(source_commit) != 40 or any(character not in "0123456789abcdef" for character in source_commit.lower()):
        raise SchemaInvariantError("source commit must be a full Git SHA-1")
    for label, digest in (("batch manifest", batch_manifest_sha256), ("run plan", run_plan_sha256)):
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest.lower()):
            raise SchemaInvariantError(f"{label} digest must be SHA-256")
    if not proposed_run_id.startswith(_run_prefix(dataset_version, slot)):
        raise SchemaInvariantError("proposed run ID does not match the selected slot and dataset")

    evidence_root = normalized_root / "phase5_5/evidence"
    lineage_path = evidence_root / "lineage.csv"
    records = AttemptLineageStore(lineage_path).load_records()
    relevant = _current_records(records, dataset_version=dataset_version, model_slot=slot)
    documents = _checkpoint_documents(evidence_root / "checkpoints")
    superseded_runs = _validated_superseded_runs(
        evidence_root=evidence_root,
        relevant=relevant,
        documents=documents,
        model_slot=slot,
        dataset_version=dataset_version,
    )
    relevant = tuple(record for record in relevant if record.run_id not in superseded_runs)
    v2_runs = {
        run_id: entries
        for run_id, entries in documents.items()
        if any(payload.get("artifact") == CHECKPOINT_ARTIFACT for _, payload in entries)
        and run_id.startswith(_run_prefix(dataset_version, slot))
        and run_id not in superseded_runs
    }

    if not relevant and not v2_runs:
        return OfficialResumeResolution(
            mode=ResumeMode.NEW,
            run_id=proposed_run_id,
            checkpoint_sequence=0,
            completed_target_count=0,
            diagnostic="no durable current-dataset campaign exists",
        )
    if len(v2_runs) != 1:
        reason = "legacy current-dataset lineage has no source-bound v2 checkpoint" if relevant and not v2_runs else "multiple source-bound resume runs exist"
        raise SchemaInvariantError(reason)

    run_id, entries = next(iter(v2_runs.items()))
    lineage_runs = {record.run_id for record in relevant}
    if lineage_runs != {run_id}:
        raise SchemaInvariantError(
            f"current-dataset lineage does not belong exclusively to resume run {run_id}: {sorted(lineage_runs)}"
        )
    if any(record.attempt_status not in _TERMINAL_STATUSES for record in relevant):
        raise SchemaInvariantError("resume lineage contains a non-terminal attempt status")
    by_attempt_id = {record.attempt_id: record for record in records}
    by_target: dict[str, list[AttemptLineageRecord]] = {}
    for record in relevant:
        by_target.setdefault(record.target_trial_id, []).append(record)
    for target, histories in by_target.items():
        ordered = sorted(histories, key=lambda record: record.attempt_index)
        start_index = ordered[0].attempt_index
        if [record.attempt_index for record in ordered] != list(range(start_index, start_index + len(ordered))):
            raise SchemaInvariantError(f"resume lineage has a non-contiguous attempt chain for {target}")
        first = ordered[0]
        if start_index == 0:
            if first.parent_attempt_id is not None:
                raise SchemaInvariantError(f"resume lineage has an invalid root parent for {target}")
        else:
            boundary_parent = by_attempt_id.get(first.parent_attempt_id or "")
            if (
                boundary_parent is None
                or boundary_parent.target_trial_id != target
                or boundary_parent.dataset_version == dataset_version
                or boundary_parent.attempt_index != start_index - 1
                or boundary_parent.attempt_status not in _TERMINAL_STATUSES
            ):
                raise SchemaInvariantError(f"resume lineage has an invalid dataset-epoch boundary for {target}")
        for index, record in enumerate(ordered):
            expected_parent = (
                first.parent_attempt_id
                if index == 0 and start_index > 0
                else None
                if index == 0
                else ordered[index - 1].attempt_id
            )
            if record.parent_attempt_id != expected_parent:
                raise SchemaInvariantError(f"resume lineage has an invalid parent chain for {target}")
            if index < len(ordered) - 1 and record.attempt_status != "ORPHAN":
                raise SchemaInvariantError(f"resume lineage retries a non-orphan target {target}")
    for record in relevant:
        _validate_attempt_evidence(evidence_root, record)

    latest = _validate_checkpoint_chain(
        entries,
        run_id=run_id,
        model_slot=slot,
        dataset_version=dataset_version,
        source_commit=source_commit,
        batch_manifest_sha256=batch_manifest_sha256,
        run_plan_sha256=run_plan_sha256,
    )
    _require_equal(latest, "run_lineage_count", len(relevant), "latest checkpoint")
    _require_lineage_sha256(latest, lineage_path, "latest checkpoint")
    if relevant:
        _require_equal(latest, "last_attempt_id", relevant[-1].attempt_id, "latest checkpoint")
        _require_equal(latest, "last_target_trial_id", relevant[-1].target_trial_id, "latest checkpoint")

    sequence = int(latest["checkpoint_sequence"])
    complete = _is_complete(evidence_root, run_id)
    return OfficialResumeResolution(
        mode=ResumeMode.COMPLETE if complete else ResumeMode.RESUME,
        run_id=run_id,
        checkpoint_sequence=sequence,
        completed_target_count=sum(
            1 for histories in by_target.values() if histories[-1].attempt_status != "ORPHAN"
        ),
        diagnostic="publication receipt proves completion" if complete else "latest remote checkpoint reconciled",
    )
