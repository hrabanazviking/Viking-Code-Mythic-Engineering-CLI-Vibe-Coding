# Portions adapted from badlogic/pi-mono (packages/coding-agent/src/core/exec.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# Adapted by Volmarr / RuneForgeAI, 2026.
# This file is licensed under the Apache License, Version 2.0; the upstream
# MIT permission notice is preserved in THIRD_PARTY_NOTICES.md at the repo root.
"""Subprocess execution primitive.

Pi's ``execCommand`` wraps Node's ``child_process.spawn`` with timeout, an
``AbortSignal``, and a graceful SIGTERM → SIGKILL fallback. The Python port
mirrors that contract using :mod:`subprocess` and :mod:`threading`:

- ``timeout`` (seconds, float) — fire-and-forget kill via ``threading.Timer``.
- ``cancel_event`` (``threading.Event``) — caller-driven cancellation; the
  Python equivalent of pi's ``AbortSignal``. A small watcher thread polls the
  event and kills the process if it transitions to set during execution.
- Graceful kill: ``proc.terminate()`` first, then escalate to ``proc.kill()``
  if the process doesn't exit within five seconds.
- Pi's ``waitForChildProcess`` Node-stdio quirk handler is **not needed** —
  Python's ``Popen.communicate()`` already drains stdout/stderr cleanly on
  Windows without the inherited-pipe-handle hang pi works around.

The result type is a frozen dataclass mirroring pi's ``ExecResult``.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import threading
from typing import Sequence


@dataclass(frozen=True)
class ExecResult:
    stdout: str
    stderr: str
    code: int
    killed: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "code": self.code,
            "killed": self.killed,
        }


def exec_command(
    command: str,
    args: Sequence[str],
    cwd: str | os.PathLike[str],
    *,
    timeout: float | None = None,
    cancel_event: threading.Event | None = None,
) -> ExecResult:
    """Run ``command`` with ``args`` in ``cwd`` and capture stdout/stderr.

    ``shell=False`` is hard-coded — callers must split arguments themselves,
    matching pi's stance against shell-injection-prone command construction.

    Returns an :class:`ExecResult`. Missing commands return ``code=127`` and
    populate ``stderr`` with the underlying error message rather than raising,
    matching pi's "always resolve, never throw" contract.
    """
    try:
        proc = subprocess.Popen(
            [command, *args],
            cwd=str(cwd),
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError as exc:
        return ExecResult(stdout="", stderr=str(exc), code=127, killed=False)

    killed = False
    kill_lock = threading.Lock()

    def kill_proc() -> None:
        nonlocal killed
        with kill_lock:
            if killed:
                return
            killed = True
        try:
            proc.terminate()
        except (ProcessLookupError, OSError):
            return
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except (ProcessLookupError, OSError):
                return

    cancel_stop = threading.Event()
    cancel_watcher: threading.Thread | None = None
    if cancel_event is not None:
        if cancel_event.is_set():
            kill_proc()
        else:
            def watch() -> None:
                while not cancel_stop.is_set():
                    if cancel_event.is_set():
                        kill_proc()
                        return
                    cancel_stop.wait(0.05)

            cancel_watcher = threading.Thread(target=watch, daemon=True)
            cancel_watcher.start()

    timer: threading.Timer | None = None
    if timeout is not None and timeout > 0:
        timer = threading.Timer(timeout, kill_proc)
        timer.daemon = True
        timer.start()

    try:
        stdout, stderr = proc.communicate()
    finally:
        if timer is not None:
            timer.cancel()
        cancel_stop.set()
        if cancel_watcher is not None:
            cancel_watcher.join(timeout=1.0)

    code = proc.returncode if proc.returncode is not None else 0
    return ExecResult(
        stdout=stdout or "",
        stderr=stderr or "",
        code=code,
        killed=killed,
    )
