from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import traceback
from typing import Any

from .paths import script_crash_reports_root, state_root


def guarded_main(
    func: Callable[[], object],
    *,
    script_name: str,
    json_mode: bool = False,
) -> int:
    """Run a standalone script behind a process-level crash boundary."""
    try:
        return _coerce_exit_code(func())
    except KeyboardInterrupt:
        _safe_stderr(f"{script_name}: interrupted\n")
        return 130
    except BrokenPipeError:
        return 1
    except SystemExit as exc:
        return _coerce_exit_code(exc.code)
    except BaseException as exc:  # noqa: BLE001 - standalone script crash boundary
        report = write_crash_report(exc, script_name=script_name)
        if json_mode:
            _safe_stdout(
                json.dumps(
                    {
                        "script": script_name,
                        "error": type(exc).__name__,
                        "message": str(exc) or type(exc).__name__,
                        "crash_report": str(report) if report else "",
                        "exit_code": 1,
                    },
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        else:
            _safe_stderr(
                f"{script_name}: unexpected error: "
                f"{type(exc).__name__}: {exc or type(exc).__name__}\n"
            )
            if report is not None:
                _safe_stderr(f"{script_name}: crash report: {report}\n")
        return 1


def write_crash_report(exc: BaseException, *, script_name: str) -> Path | None:
    try:
        root = script_crash_reports_root()
        root.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        safe_name = "".join(
            char if char.isalnum() or char in {"-", "_", "."} else "-"
            for char in script_name
        ).strip("-") or "script"
        path = root / f"{safe_name}-{timestamp}-{os.getpid()}.log"
        lines = [
            "Mythic Vibe standalone script crash report",
            f"script: {script_name}",
            f"timestamp_utc: {datetime.now(timezone.utc).isoformat()}",
            f"pid: {os.getpid()}",
            f"cwd: {Path.cwd()}",
            f"argv: {sys.argv!r}",
            f"python: {sys.executable}",
            f"python_version: {sys.version}",
            f"platform: {platform.platform()}",
            "",
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        ]
        path.write_text("\n".join(lines), encoding="utf-8", errors="replace")
        return path
    except Exception:  # noqa: BLE001 - reporting must never crash the guard
        return None


def _state_root() -> Path:
    return state_root()


def _coerce_exit_code(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, min(value, 255))
    try:
        return max(0, min(int(str(value)), 255))
    except (TypeError, ValueError):
        return 1


def _safe_stdout(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except Exception:  # noqa: BLE001 - best-effort final reporting
        pass


def _safe_stderr(text: str) -> None:
    try:
        sys.stderr.write(text)
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - best-effort final reporting
        pass


__all__ = ["guarded_main", "write_crash_report"]
