"""Lint Phase 4.5 markdown outputs for forbidden claims."""

from __future__ import annotations

import argparse
from pathlib import Path

from _phase45_utils import PHASE45_ROOT, VALIDATION_DIR


FORBIDDEN_PHRASES = [
    "final ASR",
    "vulnerability confirmed",
    "robustness confirmed",
    "defense effective",
    "MCP is vulnerable",
    "attack success rate is",
    "official adversarial result",
    "publication conclusion",
]

ALLOW_CONTEXT_TOKENS = ("forbidden", "example", "examples", "must not", "do not", "not report", "not claimed")


def line_is_allowed(line: str) -> bool:
    lowered = line.lower()
    return any(token in lowered for token in ALLOW_CONTEXT_TOKENS)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lint Phase 4.5 markdown for forbidden claims")
    parser.add_argument("--report", default=str(VALIDATION_DIR / "phase45_forbidden_claims_report.md"))
    args = parser.parse_args()

    violations: list[str] = []
    scanned_files = 0
    for path in PHASE45_ROOT.rglob("*.md"):
        if path.name == "phase45_forbidden_claims_report.md":
            continue
        scanned_files += 1
        text = path.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            lowered = line.lower()
            for phrase in FORBIDDEN_PHRASES:
                if phrase.lower() in lowered and not line_is_allowed(line):
                    violations.append(f"{path.relative_to(PHASE45_ROOT)}:{lineno}: {phrase}")

    status = "FORBIDDEN_CLAIMS_LINT_PASS" if not violations else "REVISE_PHASE45"
    lines = [
        "# Phase 4.5 Forbidden Claims Report",
        "",
        f"- Internal status: `{status}`",
        f"- Scanned markdown files: `{scanned_files}`",
        "",
        "## Forbidden Phrases Checked",
    ]
    lines.extend(f"- `{phrase}`" for phrase in FORBIDDEN_PHRASES)
    lines.extend(
        [
            "",
            "## Violations",
        ]
    )
    if violations:
        lines.extend(f"- {item}" for item in violations)
    else:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Verdict",
            f"- `{status}`",
        ]
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if not violations else 1


if __name__ == "__main__":
    raise SystemExit(main())
