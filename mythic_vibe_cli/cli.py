"""Mythic Vibe CLI resilient process entry point.

This module is the console-script target for both ``mythic`` and
``mythic-vibe``. It intentionally keeps command parsing and dispatch in
``mythic_vibe_cli.app``, but it owns the outer crash boundary operators
hit first: import failures, keyboard interrupts, broken pipes, and
unexpected exceptions are converted into deterministic exit codes with
best-effort crash reports instead of raw tracebacks.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import platform
import sys
import traceback
from typing import Any

__all__ = ["COMMAND_HANDLERS", "build_parser", "main"]


def __getattr__(name: str) -> Any:
    if name in {"COMMAND_HANDLERS", "build_parser"}:
        from . import app

        return getattr(app, name)
    raise AttributeError(name)


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    max_restarts = _restart_budget(raw_argv)
    attempt = 0

    while True:
        try:
            from .app import main as app_main

            return _coerce_exit_code(app_main(raw_argv))
        except KeyboardInterrupt:
            _safe_stderr("Interrupted. No traceback needed.\n")
            return 130
        except BrokenPipeError:
            return 1
        except SystemExit as exc:
            return _coerce_exit_code(exc.code)
        except BaseException as exc:  # noqa: BLE001 - this is the process crash boundary
            report_path = _write_crash_report(exc, raw_argv, attempt)
            if attempt < max_restarts:
                attempt += 1
                _safe_stderr(
                    "Mythic Vibe startup failed; retrying once"
                    f" (crash report: {report_path or 'unavailable'}).\n"
                )
                continue
            _emit_crash_message(exc, raw_argv, report_path)
            return 1


def _restart_budget(argv: list[str]) -> int:
    raw = os.environ.get("MYTHIC_STARTUP_RESTARTS", "").strip()
    if raw:
        try:
            parsed = int(raw)
        except ValueError:
            parsed = 0
        return max(0, min(parsed, 5))
    return 1 if not argv else 0


def _coerce_exit_code(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return max(0, min(value, 255))
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return 1
    return max(0, min(parsed, 255))


def _emit_crash_message(exc: BaseException, argv: list[str], report_path: Path | None) -> None:
    message = {
        "error": type(exc).__name__,
        "message": str(exc) or type(exc).__name__,
        "crash_report": str(report_path) if report_path else "",
        "exit_code": 1,
    }
    if "--json" in argv:
        _safe_stdout(json.dumps(message, indent=2, sort_keys=True) + "\n")
        return
    _safe_stderr(
        "Mythic Vibe hit an unexpected startup/runtime error and shut down cleanly.\n"
    )
    _safe_stderr(f"Error: {message['error']}: {message['message']}\n")
    if report_path is not None:
        _safe_stderr(f"Crash report: {report_path}\n")
    _safe_stderr("Rerun with MYTHIC_STARTUP_RESTARTS=1 to allow one automatic retry.\n")


def _write_crash_report(
    exc: BaseException,
    argv: list[str],
    attempt: int,
) -> Path | None:
    try:
        root = _state_root()
        target_dir = root / "crash-reports"
        target_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        path = target_dir / f"startup-{timestamp}-{os.getpid()}-{attempt}.log"
        payload = [
            "Mythic Vibe CLI crash report",
            f"timestamp_utc: {datetime.now(timezone.utc).isoformat()}",
            f"pid: {os.getpid()}",
            f"cwd: {Path.cwd()}",
            f"argv: {argv!r}",
            f"python: {sys.executable}",
            f"python_version: {sys.version}",
            f"platform: {platform.platform()}",
            "",
            "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        ]
        path.write_text("\n".join(payload), encoding="utf-8", errors="replace")
        return path
    except Exception:  # noqa: BLE001 - crash reporting must never crash startup
        return None


def _state_root() -> Path:
    raw = os.environ.get("MYTHIC_STATE_HOME", "").strip()
    if raw:
        return Path(raw).expanduser()
    xdg_state = os.environ.get("XDG_STATE_HOME", "").strip()
    if xdg_state:
        return Path(xdg_state).expanduser() / "mythic-vibe"
    local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
    if local_appdata:
        return Path(local_appdata).expanduser() / "MythicVibeCLI"
    return Path.home() / ".local" / "state" / "mythic-vibe"


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


if __name__ == "__main__":
    raise SystemExit(main())
