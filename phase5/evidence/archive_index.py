"""Archive index helpers for Phase 5 finalization."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError
from .io import atomic_write_text


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


def _require_int(value: Any, field: str) -> int:
    if not isinstance(value, int) or value < 0:
        raise SchemaInvariantError(f"{field} must be a non-negative integer")
    return value


def _require_hex_hash(value: str, field: str) -> str:
    if len(value) != 64 or any(char not in "0123456789abcdefABCDEF" for char in value):
        raise SchemaInvariantError(f"{field} must be a 64-character hexadecimal SHA-256 digest")
    return value


@dataclass(frozen=True, slots=True)
class ArchiveIndexEntry:
    uri: str
    size_bytes: int
    sha256: str
    included_attempt_ids: tuple[str, ...]
    retrieval_status: str

    def __post_init__(self) -> None:
        _require_string(self.uri, "uri")
        _require_int(self.size_bytes, "size_bytes")
        _require_hex_hash(self.sha256, "sha256")
        _require_string(self.retrieval_status, "retrieval_status")
        if not self.included_attempt_ids:
            raise MissingFrozenSettingError("archive index entries must include at least one attempt id")
        if len(set(self.included_attempt_ids)) != len(self.included_attempt_ids):
            raise SchemaInvariantError("archive index entries cannot repeat attempt ids")

    def to_dict(self) -> dict[str, Any]:
        return {
            "included_attempt_ids": list(self.included_attempt_ids),
            "retrieval_status": self.retrieval_status,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "uri": self.uri,
        }

    @classmethod
    def from_mapping(cls, mapping: dict[str, Any]) -> "ArchiveIndexEntry":
        included_attempt_ids = mapping.get("included_attempt_ids")
        if not isinstance(included_attempt_ids, list) or not included_attempt_ids:
            raise MissingFrozenSettingError("archive index entry must include attempt ids")
        return cls(
            uri=_require_string(mapping["uri"], "uri"),
            size_bytes=_require_int(mapping["size_bytes"], "size_bytes"),
            sha256=_require_hex_hash(_require_string(mapping["sha256"], "sha256"), "sha256"),
            included_attempt_ids=tuple(_require_string(item, "included_attempt_id") for item in included_attempt_ids),
            retrieval_status=_require_string(mapping["retrieval_status"], "retrieval_status"),
        )


@dataclass(frozen=True, slots=True)
class ArchiveIndex:
    generated_utc: str
    status: str
    entries: tuple[ArchiveIndexEntry, ...]
    archive_index_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "archive_index_sha256": self.archive_index_sha256,
            "entries": [entry.to_dict() for entry in self.entries],
            "generated_utc": self.generated_utc,
            "status": self.status,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True)

    def to_markdown(self) -> str:
        lines = [
            "# P12 External Archive Index",
            "",
            "## Verdict",
            "",
            f"- Status: `{self.status}`",
            f"- Generated UTC: `{self.generated_utc}`",
            f"- Archive index hash: `{self.archive_index_sha256}`",
            "",
            "## Entries",
        ]
        for entry in self.entries:
            lines.append(
                f"- `{entry.uri}`: size={entry.size_bytes}, sha256=`{entry.sha256}`, "
                f"attempts={', '.join(entry.included_attempt_ids)}, retrieval={entry.retrieval_status}"
            )
        return "\n".join(lines) + "\n"

    def write(self, json_path: Path, markdown_path: Path | None = None) -> None:
        atomic_write_text(json_path, self.to_json() + "\n")
        if markdown_path is not None:
            atomic_write_text(markdown_path, self.to_markdown())


def build_archive_index(
    entries: Sequence[ArchiveIndexEntry | dict[str, Any]],
    *,
    generated_utc: str,
    status: str = "FINALIZED_NOT_SYNCED",
) -> ArchiveIndex:
    normalized: list[ArchiveIndexEntry] = []
    seen_uris: set[str] = set()
    seen_attempt_ids: set[str] = set()
    for item in entries:
        entry = item if isinstance(item, ArchiveIndexEntry) else ArchiveIndexEntry.from_mapping(item)
        if entry.uri in seen_uris:
            raise SchemaInvariantError(f"duplicate archive uri detected: {entry.uri}")
        overlap = sorted(set(entry.included_attempt_ids) & seen_attempt_ids)
        if overlap:
            raise SchemaInvariantError(
                f"duplicate attempt ids detected across archive entries: {', '.join(overlap)}"
            )
        seen_uris.add(entry.uri)
        seen_attempt_ids.update(entry.included_attempt_ids)
        normalized.append(entry)
    normalized.sort(key=lambda entry: (entry.uri, entry.sha256, entry.size_bytes))

    canonical = {
        "entries": [entry.to_dict() for entry in normalized],
        "generated_utc": generated_utc,
        "status": status,
    }
    archive_index_sha256 = _sha256_bytes(_canonical_json(canonical).encode("utf-8"))
    return ArchiveIndex(
        generated_utc=generated_utc,
        status=status,
        entries=tuple(normalized),
        archive_index_sha256=archive_index_sha256,
    )
