"""Reusable guardrails for the Phase 5 scaffold."""

from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Iterable, Sequence

try:  # pragma: no cover - optional dependency is validated in tests
    import yaml
except Exception:  # pragma: no cover
    yaml = None


REQUIRED_AGENTS_PATHS = (
    Path("AGENTS.md"),
    Path("phase5/AGENTS.md"),
    Path("phase5/runtime/AGENTS.md"),
    Path("phase5/kaggle/AGENTS.md"),
    Path("phase5/scripts/AGENTS.md"),
    Path("phase5/tests/AGENTS.md"),
    Path("phase5/implementation/AGENTS.md"),
)

IMMUTABLE_PREFIXES = (Path("phase4"), Path("phase4_5"))
EVIDENCE_ROOT_PREFIXES = (
    Path("AGENTS.md"),
    Path(".codex/skills"),
    Path(".github/workflows"),
    Path("phase5/implementation"),
)
_AWS_SECRET_NAME = "_".join(("aws", "secret", "access", "key"))
_AWS_ACCESS_NAME = "_".join(("aws", "access", "key", "id"))
SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{10,}\b"),
    re.compile(r"(?i)\bgh[pousr]_[A-Za-z0-9_]{20,}\b"),
    re.compile(rf"(?i)\b(?:{_AWS_SECRET_NAME}|{_AWS_ACCESS_NAME})\b"),
    re.compile(r"(?i)\bBEGIN (?:RSA|OPENSSH|PRIVATE) KEY\b"),
)
FORBIDDEN_ANALYSIS_PATTERNS = (
    re.compile(r"(?i)\boutcome distribution\b"),
    re.compile(r"(?i)\bmodel ranking\b"),
    re.compile(r"(?i)\bconfidence intervals?\b"),
    re.compile(r"(?i)\bp[- ]values?\b"),
    re.compile(r"(?i)\bASR\b"),
)


@dataclass(frozen=True)
class ScanFinding:
    path: Path
    pattern: str
    excerpt: str


def repo_root(start: Path | None = None) -> Path:
    """Return the repository root by walking upward until `.git` is found."""

    current = (start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    raise FileNotFoundError("Repository root could not be located.")


def _parts(pathlike: str | Path) -> tuple[str, ...]:
    return tuple(part.lower() for part in Path(pathlike).parts)


def _has_prefix(pathlike: str | Path, prefix: str | Path) -> bool:
    path_parts = _parts(pathlike)
    prefix_parts = _parts(prefix)
    if len(prefix_parts) > len(path_parts):
        return False
    for index in range(len(path_parts) - len(prefix_parts) + 1):
        if path_parts[index : index + len(prefix_parts)] == prefix_parts:
            return True
    return False


def ensure_required_agents_exist(base: Path | None = None) -> list[Path]:
    """Return the required AGENTS files that are missing."""

    root = base or repo_root()
    missing = [path for path in REQUIRED_AGENTS_PATHS if not (root / path).is_file()]
    return missing


def validate_agents_hierarchy(base: Path | None = None) -> list[str]:
    """Check the required AGENTS tree for the expected narrow scope markers."""

    root = base or repo_root()
    missing = ensure_required_agents_exist(root)
    if missing:
        return [f"missing:{item.as_posix()}" for item in missing]

    expectations = {
        "AGENTS.md": ["phase4", "phase4_5", "phase5/implementation/reports"],
        "phase5/AGENTS.md": ["phase5", "scaffold", "ci"],
        "phase5/runtime/AGENTS.md": ["runtime", "loopback"],
        "phase5/kaggle/AGENTS.md": ["kaggle", "nested docker"],
        "phase5/scripts/AGENTS.md": ["scripts", "fail closed"],
        "phase5/tests/AGENTS.md": ["tests", "positive", "negative", "fault"],
        "phase5/implementation/AGENTS.md": ["implementation", "reports", "tasks"],
    }
    findings: list[str] = []
    for relative_path, markers in expectations.items():
        text = (root / relative_path).read_text(encoding="utf-8").lower()
        for marker in markers:
            if marker.lower() not in text:
                findings.append(f"missing-marker:{relative_path}:{marker}")
    return findings


def reject_frozen_path_changes(changed_paths: Iterable[str | Path]) -> list[str]:
    """Return the changed paths that touch frozen Phase 4 or Phase 4.5 prefixes."""

    blocked: list[str] = []
    for item in changed_paths:
        if any(_has_prefix(item, prefix) for prefix in IMMUTABLE_PREFIXES):
            blocked.append(Path(item).as_posix())
    return blocked


def reject_evidence_source_staging(staged_paths: Iterable[str | Path]) -> list[str]:
    """Return staged paths that are not allowed in evidence-only commits."""

    rejected: list[str] = []
    for item in staged_paths:
        if not any(_has_prefix(item, prefix) for prefix in EVIDENCE_ROOT_PREFIXES):
            rejected.append(Path(item).as_posix())
    return rejected


def scan_text_for_patterns(text: str, patterns: Sequence[re.Pattern[str]]) -> list[str]:
    findings = []
    for pattern in patterns:
        if pattern.search(text):
            findings.append(pattern.pattern)
    return findings


def scan_text_for_secrets(text: str) -> list[str]:
    return scan_text_for_patterns(text, SECRET_PATTERNS)


def scan_text_for_forbidden_analysis(text: str) -> list[str]:
    return scan_text_for_patterns(text, FORBIDDEN_ANALYSIS_PATTERNS)


def scan_tree_for_patterns(
    root: Path,
    patterns: Sequence[re.Pattern[str]],
    suffixes: Sequence[str] = (".md", ".yml", ".yaml", ".json", ".py", ".txt"),
    exclude_prefixes: Sequence[str | Path] = (),
) -> list[ScanFinding]:
    findings: list[ScanFinding] = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in suffixes:
            continue
        if any(_has_prefix(path, prefix) for prefix in exclude_prefixes):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                findings.append(
                    ScanFinding(path=path, pattern=pattern.pattern, excerpt=text[max(0, match.start() - 20) : match.end() + 20])
                )
    return findings


def validate_workflow_yaml(path: Path) -> list[str]:
    if yaml is None:
        return ["pyyaml-missing"]
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    issues: list[str] = []
    if not isinstance(data, dict):
        issues.append("top-level-not-mapping")
        return issues
    if "jobs" not in data:
        issues.append("missing-jobs")
    if "name" not in data:
        issues.append("missing-name")
    return issues


def validate_report_json(path: Path, required_keys: Sequence[str]) -> list[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    missing = [key for key in required_keys if key not in data]
    return missing
