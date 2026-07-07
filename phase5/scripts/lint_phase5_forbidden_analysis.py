from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.guards import (
    FORBIDDEN_ANALYSIS_PATTERNS,
    scan_text_for_forbidden_analysis,
    scan_tree_for_patterns,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("phase5"))
    parser.add_argument("--text", default="")
    args = parser.parse_args(argv)

    if args.text:
        findings = scan_text_for_forbidden_analysis(args.text)
        if findings:
            print("forbidden analysis text found:")
            for item in findings:
                print(item)
            return 1
        print("phase5 forbidden analysis lint: PASS")
        return 0

    findings = scan_tree_for_patterns(
        args.root,
        patterns=FORBIDDEN_ANALYSIS_PATTERNS,
        exclude_prefixes=(Path("phase5/tests"),),
    )
    if findings:
        for finding in findings:
            print(f"{finding.path.as_posix()}: {finding.pattern}")
        return 1
    print("phase5 forbidden analysis lint: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
