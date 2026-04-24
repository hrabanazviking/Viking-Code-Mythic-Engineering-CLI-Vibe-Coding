from __future__ import annotations

from dataclasses import dataclass

from .exit_codes import OPERATIONAL_FAILURE


@dataclass(frozen=True)
class CliError:
    message: str
    exit_code: int = OPERATIONAL_FAILURE
    hint: str | None = None


def format_error(error: CliError) -> str:
    if error.hint:
        return f"{error.message}\nHint: {error.hint}"
    return error.message
