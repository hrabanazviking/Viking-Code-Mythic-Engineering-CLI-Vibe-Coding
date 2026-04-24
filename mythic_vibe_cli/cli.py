from __future__ import annotations

from .app import COMMAND_HANDLERS, build_parser, main

__all__ = ["COMMAND_HANDLERS", "build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
