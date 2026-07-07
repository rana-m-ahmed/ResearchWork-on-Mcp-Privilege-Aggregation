"""Append-only and crash-safe file helpers for Phase 5 evidence."""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from ..domain.errors import SchemaInvariantError


def _require_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _stable_json_bytes(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_write_bytes(
    path: Path,
    data: bytes,
    *,
    before_replace_hook: Callable[[], None] | None = None,
) -> None:
    """Write bytes atomically without silently rewriting existing content."""

    _require_parent(path)
    if path.exists():
        current = path.read_bytes()
        if current == data:
            return
        raise SchemaInvariantError(f"refusing to rewrite existing file with different content: {path.as_posix()}")

    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if before_replace_hook is not None:
            before_replace_hook()
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def atomic_write_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    before_replace_hook: Callable[[], None] | None = None,
) -> None:
    atomic_write_bytes(path, text.encode(encoding), before_replace_hook=before_replace_hook)


def atomic_append_snapshot_text(
    path: Path,
    text: str,
    *,
    encoding: str = "utf-8",
    before_replace_hook: Callable[[], None] | None = None,
) -> None:
    """Atomically replace a newline-terminated snapshot while preserving append-only history."""

    _require_parent(path)
    if path.exists():
        current = path.read_text(encoding=encoding)
        if current and not current.endswith("\n"):
            raise SchemaInvariantError(f"snapshot is not newline-terminated: {path.as_posix()}")
        if current == text:
            return
        if not text.startswith(current):
            raise SchemaInvariantError(f"snapshot rewrite would drop existing content: {path.as_posix()}")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            delete=False,
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        ) as handle:
            handle.write(text.encode(encoding))
            handle.flush()
            os.fsync(handle.fileno())
            temp_path = Path(handle.name)
        if before_replace_hook is not None:
            before_replace_hook()
        os.replace(temp_path, path)
        temp_path = None
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink(missing_ok=True)


def append_jsonl_record(
    path: Path,
    record: Mapping[str, Any],
) -> None:
    """Append a canonical JSONL row and fsync it immediately."""

    _require_parent(path)
    encoded = _stable_json_bytes(record) + b"\n"
    if path.exists():
        current = path.read_bytes()
        if current and not current.endswith(b"\n"):
            raise SchemaInvariantError(f"jsonl log is not newline-terminated: {path.as_posix()}")

    with path.open("ab") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def load_jsonl_records(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    raw = path.read_bytes()
    if raw and not raw.endswith(b"\n"):
        raise SchemaInvariantError(f"jsonl log is not newline-terminated: {path.as_posix()}")
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            raise SchemaInvariantError(f"blank jsonl row encountered in {path.as_posix()} at line {line_number}")
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:  # pragma: no cover - exercised by fault tests
            raise SchemaInvariantError(f"invalid jsonl row in {path.as_posix()} at line {line_number}") from exc
        if not isinstance(payload, dict):
            raise SchemaInvariantError(f"jsonl row must decode to an object in {path.as_posix()} at line {line_number}")
        records.append(payload)
    return tuple(records)


def render_csv(header: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> str:
    buffer = tempfile.SpooledTemporaryFile(mode="w+", newline="", max_size=4096)
    try:
        writer = csv.DictWriter(buffer, fieldnames=list(header), lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row[key] for key in header})
        buffer.seek(0)
        return buffer.read()
    finally:
        buffer.close()
