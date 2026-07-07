from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from phase5.guards import reject_frozen_path_changes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--changed", nargs="*", default=[])
    args = parser.parse_args(argv)

    blocked = reject_frozen_path_changes(args.changed)
    if blocked:
        print("blocked frozen paths:")
        for item in blocked:
            print(item)
        return 1
    print("phase5 frozen path guard: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
