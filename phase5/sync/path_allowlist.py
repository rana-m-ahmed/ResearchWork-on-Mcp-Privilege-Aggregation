"""Allowlist validation for safe Phase 5 sync staging."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

try:  # pragma: no cover - optional dependency is validated in tests
    import yaml
except Exception:  # pragma: no cover
    yaml = None

from ..domain.errors import MissingFrozenSettingError, SchemaInvariantError


def _normalize_prefix(value: str | Path) -> str:
    prefix = Path(value).as_posix().strip()
    if not prefix:
        raise SchemaInvariantError("sync allowlist prefixes must be non-empty")
    return prefix.rstrip("/") + "/"


@dataclass(frozen=True, slots=True)
class SyncAllowlist:
    allowed_staged_prefixes: tuple[str, ...]

    def allows(self, path: str | Path) -> bool:
        candidate = Path(path).as_posix()
        return any(candidate == prefix.rstrip("/") or candidate.startswith(prefix) for prefix in self.allowed_staged_prefixes)

    def rejected_paths(self, paths: Iterable[str | Path]) -> list[str]:
        rejected: list[str] = []
        for item in paths:
            if not self.allows(item):
                rejected.append(Path(item).as_posix())
        return rejected


def load_sync_allowlist(path: Path) -> SyncAllowlist:
    if yaml is None:
        raise SchemaInvariantError("pyyaml is required to load the sync allowlist")
    if not path.is_file():
        raise MissingFrozenSettingError(f"sync allowlist is missing: {path.as_posix()}")

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchemaInvariantError("sync allowlist must be a mapping")

    prefixes = data.get("allowed_staged_prefixes")
    if not isinstance(prefixes, list) or not prefixes:
        raise MissingFrozenSettingError("sync allowlist requires allowed_staged_prefixes")

    normalized = tuple(_normalize_prefix(item) for item in prefixes)
    if len(set(normalized)) != len(normalized):
        raise SchemaInvariantError("sync allowlist contains duplicate prefixes")
    return SyncAllowlist(allowed_staged_prefixes=normalized)


def validate_staged_paths(paths: Sequence[str | Path], allowlist: SyncAllowlist) -> list[str]:
    return allowlist.rejected_paths(paths)
