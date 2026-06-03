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
from typing import Literal, Sequence


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


# Phase 19.0 / BS-3 (2026-05-02 audit remediation): default upper
# bound on subprocess wall-clock time when callers don't pass an
# explicit ``timeout``. 300 seconds (5 min) is generous for any
# legitimate git / pytest / ruff / mypy invocation — long enough
# that legitimate work completes, short enough that a hang
# (SSH-passphrase prompt, NFS stall, dead network mount) surfaces
# rather than blocking the CLI indefinitely. Callers who genuinely
# need a longer / shorter bound pass it explicitly.
DEFAULT_EXEC_TIMEOUT_SECONDS = 300.0

StdinMode = Literal["devnull", "pipe", "inherit"]
OutputMode = Literal["pipe", "inherit", "discard"]


def _stdin_target(mode: StdinMode) -> int | None:
    if mode == "devnull":
        return subprocess.DEVNULL
    if mode == "pipe":
        return subprocess.PIPE
    return None


def _output_target(mode: OutputMode) -> int | None:
    if mode == "pipe":
        return subprocess.PIPE
    if mode == "discard":
        return subprocess.DEVNULL
    return None


def spawn_process(
    argv: Sequence[str],
    cwd: str | os.PathLike[str] | None = None,
    *,
    stdin: StdinMode = "devnull",
    stdout: OutputMode = "pipe",
    stderr: OutputMode = "pipe",
    text: bool = True,
    bufsize: int = -1,
) -> subprocess.Popen:
    """Spawn a live subprocess through the canonical process boundary.

    Use this when callers need an interactive/live handle rather than the
    blocking :func:`exec_command` result. The same hard rules apply:
    ``shell=False`` and caller-supplied argv tokens only.
    """
    if not argv:
        raise ValueError("argv must contain at least the executable")
    return subprocess.Popen(
        list(argv),
        cwd=str(cwd) if cwd is not None else None,
        shell=False,
        stdin=_stdin_target(stdin),
        stdout=_output_target(stdout),
        stderr=_output_target(stderr),
        text=text,
        bufsize=bufsize,
    )


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
