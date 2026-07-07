from __future__ import annotations

import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.guards import validate_agents_hierarchy


def main() -> int:
    root = Path.cwd()
    issues = validate_agents_hierarchy(root)
    if issues:
        for issue in issues:
            print(issue)
        return 1
    print("phase5 instruction hierarchy: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
