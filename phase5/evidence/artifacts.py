"""Content-addressed raw artifact primitives for Phase 5 evidence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ..domain.errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError
from ..domain.identifiers import ArtifactId
from .io import atomic_write_bytes, atomic_write_text


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_string(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SchemaInvariantError(f"{field} must be a non-empty string")
    return value


@dataclass(frozen=True, slots=True)
class RawArtifactRecord:
    artifact_id: ArtifactId
    artifact_type: str
    sha256: str
    byte_length: int
    relative_path: Path
    metadata_path: Path | None = None
    encoding: str | None = None
    line_ending: str | None = None

    def to_mapping(self) -> dict[str, Any]:
        return {
            "artifact_id": str(self.artifact_id),
            "artifact_type": self.artifact_type,
            "byte_length": self.byte_length,
            "encoding": self.encoding,
            "line_ending": self.line_ending,
            "metadata_path": None if self.metadata_path is None else self.metadata_path.as_posix(),
            "relative_path": self.relative_path.as_posix(),
            "sha256": self.sha256,
        }

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "RawArtifactRecord":
        try:
            artifact_id = ArtifactId.parse(_require_string(mapping["artifact_id"], "artifact_id"))
            metadata_path = mapping.get("metadata_path")
            relative_path = Path(_require_string(mapping["relative_path"], "relative_path"))
            byte_length = mapping["byte_length"]
            if not isinstance(byte_length, int) or byte_length < 0:
                raise SchemaInvariantError("byte_length must be a non-negative integer")
            return cls(
                artifact_id=artifact_id,
                artifact_type=_require_string(mapping["artifact_type"], "artifact_type"),
                sha256=_require_string(mapping["sha256"], "sha256"),
                byte_length=byte_length,
                relative_path=relative_path,
                metadata_path=None if metadata_path is None else Path(_require_string(metadata_path, "metadata_path")),
                encoding=mapping.get("encoding"),
                line_ending=mapping.get("line_ending"),
            )
        except KeyError as exc:
            raise SchemaInvariantError(f"missing artifact field: {exc.args[0]}") from exc


class ContentAddressedArtifactWriter:
    """Store raw bytes under a content-addressed, hash-derived artifact id."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def write_bytes(
        self,
        data: bytes,
        *,
        artifact_type: str,
        metadata: Mapping[str, Any] | None = None,
        encoding: str | None = None,
        line_ending: str | None = None,
    ) -> RawArtifactRecord:
        digest = _sha256_bytes(data)
        artifact_id = ArtifactId.build(digest[:16].upper(), artifact_type)
        relative_path = Path(artifact_id.value)
        path = self.root / relative_path
        atomic_write_bytes(path, data)

        metadata_path: Path | None = None
        if metadata is not None or encoding is not None or line_ending is not None:
            metadata_path = path.with_suffix(".json")
            payload = {
                "artifact_id": artifact_id.value,
                "artifact_type": artifact_type,
                "byte_length": len(data),
                "encoding": encoding,
                "line_ending": line_ending,
                "sha256": digest,
            }
            if metadata is not None:
                payload["metadata"] = dict(metadata)
            atomic_write_text(metadata_path, json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

        return RawArtifactRecord(
            artifact_id=artifact_id,
            artifact_type=artifact_type,
            sha256=digest,
            byte_length=len(data),
            relative_path=relative_path,
            metadata_path=metadata_path,
            encoding=encoding,
            line_ending=line_ending,
        )

    def write_text(
        self,
        text: str,
        *,
        artifact_type: str,
        encoding: str = "utf-8",
        line_ending: str | None = None,
        metadata: Mapping[str, Any] | None = None,
    ) -> RawArtifactRecord:
        return self.write_bytes(
            text.encode(encoding),
            artifact_type=artifact_type,
            metadata=metadata,
            encoding=encoding,
            line_ending=line_ending,
        )


def validate_raw_artifact(record: RawArtifactRecord, *, root: Path) -> None:
    path = root / record.relative_path
    if not path.exists():
        raise MissingFrozenSettingError(f"raw artifact is missing: {path.as_posix()}")
    data = path.read_bytes()
    actual_sha256 = _sha256_bytes(data)
    if actual_sha256 != record.sha256:
        raise FrozenArtifactHashError(
            f"raw artifact hash mismatch for {path.as_posix()}: expected {record.sha256}, got {actual_sha256}"
        )
    if len(data) != record.byte_length:
        raise SchemaInvariantError(
            f"raw artifact length mismatch for {path.as_posix()}: expected {record.byte_length}, got {len(data)}"
        )
