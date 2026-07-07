from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.guards import reject_evidence_source_staging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--staged", nargs="*", default=[])
    args = parser.parse_args(argv)

    rejected = reject_evidence_source_staging(args.staged)
    if rejected:
        print("blocked evidence staging:")
        for item in rejected:
            print(item)
        return 1
    print("phase5 evidence staging guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
