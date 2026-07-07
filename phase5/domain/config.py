"""Immutable configuration loaders for frozen Phase 5 artifacts."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping

from ..guards import repo_root
from .errors import FrozenArtifactHashError, MissingFrozenSettingError, SchemaInvariantError


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _normalize_paths(value: Any) -> tuple[Path, ...]:
    if isinstance(value, str):
        return (Path(value),)
    if isinstance(value, list):
        return tuple(Path(item) for item in value)
    raise SchemaInvariantError(f"registry path specification must be a string or list of strings: {value!r}")


def _normalize_hashes(value: Any) -> tuple[str, ...]:
    if isinstance(value, str):
        return (value,)
    if isinstance(value, list):
        return tuple(value)
    raise SchemaInvariantError(f"registry hash specification must be a string or list of strings: {value!r}")


def _iter_entries(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, list):
        for item in node:
            yield from _iter_entries(item)
        return
    if not isinstance(node, dict):
        return

    if ("label" in node or "requested_label" in node) and ("path" in node or "actual_path" in node):
        yield node
        return

    for value in node.values():
        yield from _iter_entries(value)


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    label: str
    actual_paths: tuple[Path, ...]
    sha256: tuple[str, ...]
    status: str
    notes: str | None = None

    @property
    def verified(self) -> bool:
        return self.status == "FOUND_VERIFIED"


@dataclass(frozen=True, slots=True)
class ArtifactRegistry:
    registry_id: str
    registry_version: str | None
    generated_utc: str | None
    status: str
    source_path: Path
    sha256: str
    entries: tuple[RegistryEntry, ...]
    _index: Mapping[str, RegistryEntry]

    def labels(self) -> tuple[str, ...]:
        return tuple(self._index.keys())

    def require(self, label: str, *, verified_only: bool = True) -> RegistryEntry:
        try:
            entry = self._index[label]
        except KeyError as exc:
            raise MissingFrozenSettingError(f"required frozen registry label is missing: {label!r}") from exc
        if verified_only and not entry.verified:
            raise MissingFrozenSettingError(
                f"required frozen registry label is not verified: {label!r} ({entry.status})"
            )
        return entry

    def resolved_paths(self, label: str) -> tuple[Path, ...]:
        return self.require(label).actual_paths


def load_upstream_artifact_registry(
    path: Path | None = None,
    *,
    expected_sha256: str | None = None,
    verify_verified_entries: bool = True,
) -> ArtifactRegistry:
    root = repo_root()
    registry_path = path or (root / "phase5" / "configs" / "upstream_artifact_registry.json")
    if not registry_path.is_file():
        raise MissingFrozenSettingError(f"upstream artifact registry is missing: {registry_path}")

    raw_bytes = registry_path.read_bytes()
    actual_sha256 = _sha256_bytes(raw_bytes)
    if expected_sha256 is not None and actual_sha256.lower() != expected_sha256.lower():
        raise FrozenArtifactHashError(
            f"upstream artifact registry hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )

    data = json.loads(raw_bytes.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise SchemaInvariantError("upstream artifact registry must be a JSON object")
    if data.get("registry_id") != "P00":
        raise SchemaInvariantError("upstream artifact registry must preserve registry_id=P00")
    if data.get("status") != "COMPLETE":
        raise SchemaInvariantError("upstream artifact registry must be COMPLETE")

    required_items = data.get("required_items")
    if not isinstance(required_items, dict):
        raise MissingFrozenSettingError("upstream artifact registry is missing required_items")

    entries: list[RegistryEntry] = []
    index: dict[str, RegistryEntry] = {}
    for item in _iter_entries(required_items):
        label = item.get("label") or item.get("requested_label")
        if not isinstance(label, str) or not label:
            raise SchemaInvariantError(f"registry item is missing a label: {item!r}")
        actual_paths = _normalize_paths(item.get("path", item.get("actual_path")))
        sha256 = _normalize_hashes(item.get("sha256"))
        status = item.get("status")
        if not isinstance(status, str) or not status:
            raise SchemaInvariantError(f"registry item is missing a status: {label!r}")
        notes = item.get("notes")
        if notes is not None and not isinstance(notes, str):
            raise SchemaInvariantError(f"registry item notes must be a string or null: {label!r}")
        if len(actual_paths) != len(sha256):
            raise SchemaInvariantError(f"registry item path/hash arity mismatch: {label!r}")

        entry = RegistryEntry(label=label, actual_paths=actual_paths, sha256=sha256, status=status, notes=notes)
        if label in index:
            raise SchemaInvariantError(f"duplicate registry label encountered: {label!r}")
        index[label] = entry
        entries.append(entry)

    registry = ArtifactRegistry(
        registry_id=str(data["registry_id"]),
        registry_version=data.get("registry_version"),
        generated_utc=data.get("generated_utc"),
        status=str(data["status"]),
        source_path=registry_path,
        sha256=actual_sha256,
        entries=tuple(entries),
        _index=MappingProxyType(index),
    )

    if verify_verified_entries:
        for entry in registry.entries:
            if not entry.verified:
                continue
            for relative_path, expected_file_hash in zip(entry.actual_paths, entry.sha256, strict=True):
                resolved_path = root / relative_path
                if not resolved_path.is_file():
                    raise MissingFrozenSettingError(f"verified registry file is missing: {relative_path.as_posix()}")
                actual_file_hash = _sha256_file(resolved_path)
                if actual_file_hash.lower() != expected_file_hash.lower():
                    raise FrozenArtifactHashError(
                        f"verified registry file hash mismatch for {relative_path.as_posix()}: "
                        f"expected {expected_file_hash}, got {actual_file_hash}"
                    )

    return registry
