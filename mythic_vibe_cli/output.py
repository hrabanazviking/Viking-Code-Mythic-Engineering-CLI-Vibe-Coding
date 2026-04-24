from __future__ import annotations

import json
import sys
from typing import Any
from typing import TextIO


_QUIET = False
_VERBOSE = False


def configure_output(*, quiet: bool = False, verbose: bool = False) -> None:
    global _QUIET, _VERBOSE
    _QUIET = quiet
    _VERBOSE = verbose


def write_line(message: str = "", *, stream: TextIO | None = None, force: bool = False) -> None:
    target = stream or sys.stdout
    if target is sys.stdout and _QUIET and not force:
        return
    print(message, file=target)


def write_error(message: str) -> None:
    write_line(message, stream=sys.stderr, force=True)


def write_bullet(message: str, *, indent: int = 0) -> None:
    prefix = " " * indent + "- "
    write_line(f"{prefix}{message}")


def write_key_value(key: str, value: object, *, indent: int = 0) -> None:
    prefix = " " * indent + "- "
    write_line(f"{prefix}{key}: {value}")


def write_json(payload: dict[str, Any]) -> None:
    write_line(json.dumps(payload, indent=2, sort_keys=True), force=True)


def write_verbose(message: str) -> None:
    if _VERBOSE and not _QUIET:
        write_line(message)
