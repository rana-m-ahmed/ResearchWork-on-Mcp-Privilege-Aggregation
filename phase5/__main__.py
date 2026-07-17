"""Module entry point for ``python -m phase5``."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        import traceback, sys
        with open("crash.log", "w") as f:
            f.write("=== FATAL EXCEPTION ===\n")
            traceback.print_exc(file=f)
            f.write("=======================\n")
        print("\n\n=== FATAL EXCEPTION ===", file=sys.stderr)
        traceback.print_exc()
        print("=======================\n\n", file=sys.stderr)
        sys.exit(1)
