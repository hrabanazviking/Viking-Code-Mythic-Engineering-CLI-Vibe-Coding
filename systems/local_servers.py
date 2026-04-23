"""Local server launchers for Whisper STT and Chatterbox TTS.

Provides helpers that attempt to start Whisper and Chatterbox as
lightweight OpenAI-compatible HTTP servers in background processes.

Robustness features
-------------------
- **Auto-restart**: ``ensure_servers_healthy()`` checks if child
  processes have crashed and restarts them automatically.
- **Crash monitoring**: ``is_server_alive()`` checks both process
  status and HTTP health in a single call.
- **Graceful shutdown**: ``stop_servers()`` terminates, waits, then
  kills stubborn processes.  Registered with ``atexit``.
- **Port collision guard**: checks if a server is already listening
  before starting a new one.
- **All exceptions caught**: launcher functions never raise.
"""

from __future__ import annotations

import atexit
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Track child server processes for clean shutdown
_child_processes: List[Tuple[str, int, subprocess.Popen]] = []
# (label, port, process)

_MAX_RESTART_ATTEMPTS = 3
_RESTART_COOLDOWN = 5.0  # seconds between restart attempts


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _safe_http_check(url: str, timeout: float = 3) -> bool:
    """Return True if *url* responds with status < 500."""
    if httpx is None:
        return False
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
        return resp.status_code < 500
    except Exception:
        return False


def _wait_for_server(
    url: str,
    label: str,
    timeout: float = 45.0,
    poll_interval: float = 1.0,
) -> bool:
    """Poll *url* until it responds or *timeout* elapses."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        if _safe_http_check(url, timeout=3):
            logger.info("%s ready at %s", label, url)
            return True
        time.sleep(poll_interval)
    logger.warning(
        "%s not ready at %s within %.0fs",
        label,
        url,
        timeout,
    )
    return False


def _proc_is_alive(proc: subprocess.Popen) -> bool:
    """Return True if the subprocess is still running."""
    try:
        return proc.poll() is None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Server launchers
# ---------------------------------------------------------------------------


def start_whisper_server(
    port: int = 8000,
    model: str = "base",
    project_root: Optional[Path] = None,
) -> Optional[subprocess.Popen]:
    """Launch a Whisper-compatible transcription server.

    Never raises — returns None on any failure.
    """
    try:
        base_url = f"http://127.0.0.1:{port}"

        # Already running?
        if _safe_http_check(base_url):
            logger.info("Whisper already running on port %d", port)
            return None

        env = os.environ.copy()

        # Attempt 1: faster-whisper-server
        try:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "faster_whisper_server",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(port),
                ],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if _wait_for_server(base_url, "Whisper (faster-whisper-server)"):
                _child_processes.append(("whisper", port, proc))
                return proc
            _safe_terminate(proc)
        except Exception as exc:
            logger.debug("faster-whisper-server unavailable: %s", exc)

        # Attempt 2: built-in shim
        shim_code = _whisper_shim_code(port, model)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", shim_code],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if _wait_for_server(base_url, "Whisper (built-in shim)"):
                _child_processes.append(("whisper", port, proc))
                return proc
            _safe_terminate(proc)
        except Exception as exc:
            logger.warning("Whisper server start failed: %s", exc)

        return None
    except Exception as exc:
        logger.error("Whisper launcher crash: %s", exc)
        return None


def start_chatterbox_server(
    port: int = 8001,
    project_root: Optional[Path] = None,
) -> Optional[subprocess.Popen]:
    """Launch a Chatterbox TTS server. Never raises."""
    try:
        base_url = f"http://127.0.0.1:{port}"

        if _safe_http_check(base_url):
            logger.info("Chatterbox already running on port %d", port)
            return None

        env = os.environ.copy()
        shim_code = _chatterbox_shim_code(port)
        try:
            proc = subprocess.Popen(
                [sys.executable, "-c", shim_code],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if _wait_for_server(base_url, "Chatterbox TTS", timeout=60):
                _child_processes.append(("chatterbox", port, proc))
                return proc
            _safe_terminate(proc)
        except Exception as exc:
            logger.warning("Chatterbox server start failed: %s", exc)

        return None
    except Exception as exc:
        logger.error("Chatterbox launcher crash: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Auto-restart / health monitoring
# ---------------------------------------------------------------------------


def is_server_alive(label: str) -> bool:
    """Check if a named server is both running and healthy."""
    for name, port, proc in _child_processes:
        if name == label:
            if not _proc_is_alive(proc):
                return False
            url = f"http://127.0.0.1:{port}"
            return _safe_http_check(url, timeout=3)
    return False


def ensure_servers_healthy() -> Dict[str, str]:
    """Check all tracked servers, restart any that crashed.

    Returns a dict of ``{label: status_message}``.
    """
    results: Dict[str, str] = {}
    to_restart: List[Tuple[str, int]] = []

    for i, (label, port, proc) in enumerate(list(_child_processes)):
        url = f"http://127.0.0.1:{port}"
        if _proc_is_alive(proc) and _safe_http_check(url):
            results[label] = "healthy"
        else:
            results[label] = "dead — attempting restart"
            _safe_terminate(proc)
            to_restart.append((label, port))
            # Remove dead entry
            try:
                _child_processes.remove((label, port, proc))
            except ValueError:
                pass

    for label, port in to_restart:
        restarted = False
        for attempt in range(1, _MAX_RESTART_ATTEMPTS + 1):
            logger.info(
                "Restarting %s (attempt %d/%d)",
                label,
                attempt,
                _MAX_RESTART_ATTEMPTS,
            )
            proc = None
            if label == "whisper":
                proc = start_whisper_server(port=port)
            elif label == "chatterbox":
                proc = start_chatterbox_server(port=port)

            if proc is not None:
                results[label] = "restarted"
                restarted = True
                break
            time.sleep(_RESTART_COOLDOWN)

        if not restarted:
            url = f"http://127.0.0.1:{port}"
            if _safe_http_check(url):
                results[label] = "external server running"
            else:
                results[label] = "restart failed"
                logger.error(
                    "Could not restart %s after %d attempts",
                    label,
                    _MAX_RESTART_ATTEMPTS,
                )

    return results


# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------


def _safe_terminate(proc: subprocess.Popen) -> None:
    """Terminate a process, falling back to kill."""
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass


def stop_servers() -> None:
    """Terminate all child server processes. Never raises."""
    try:
        for label, port, proc in list(_child_processes):
            logger.debug("Stopping %s (port %d)", label, port)
            _safe_terminate(proc)
        _child_processes.clear()
        logger.info("Local voice servers stopped")
    except Exception as exc:
        logger.error("Error stopping servers: %s", exc)


# Ensure children are cleaned up on interpreter exit
atexit.register(stop_servers)


# ---------------------------------------------------------------------------
# Shim source code generators
# ---------------------------------------------------------------------------


def _whisper_shim_code(port: int, model: str) -> str:
    return f'''
import sys, json, tempfile, pathlib, traceback
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import whisper
    _model = whisper.load_model("{model}")

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                import cgi
                ctype, pdict = cgi.parse_header(
                    self.headers.get("Content-Type", "")
                )
                if "boundary" in pdict:
                    pdict["boundary"] = (
                        pdict["boundary"].encode()
                    )
                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={{"REQUEST_METHOD": "POST"}},
                )
                audio_item = form["file"]
                with tempfile.NamedTemporaryFile(
                    suffix=".wav", delete=False
                ) as tmp:
                    tmp.write(audio_item.file.read())
                    tmp_path = tmp.name
                result = _model.transcribe(tmp_path)
                pathlib.Path(tmp_path).unlink(
                    missing_ok=True
                )
                text = result.get("text", "") if result else ""
                body = json.dumps({{"text": text}})
                self.send_response(200)
                self.send_header(
                    "Content-Type", "application/json"
                )
                self.end_headers()
                self.wfile.write(body.encode())
            except Exception as e:
                try:
                    err = json.dumps(
                        {{"error": str(e)}}
                    ).encode()
                    self.send_response(500)
                    self.send_header(
                        "Content-Type", "application/json"
                    )
                    self.end_headers()
                    self.wfile.write(err)
                except Exception:
                    pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{{"status":"ok"}}')

        def log_message(self, *a):
            pass

    HTTPServer(("0.0.0.0", {port}), Handler).serve_forever()
except Exception as e:
    print(
        f"Whisper shim failed: {{e}}\\n"
        f"{{traceback.format_exc()}}",
        file=sys.stderr,
    )
    sys.exit(1)
'''


def _chatterbox_shim_code(port: int) -> str:
    return f"""
import sys, json, tempfile, pathlib, io, traceback
try:
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import torch, torchaudio
    from chatterbox.tts import ChatterboxTTS

    _device = "cuda" if torch.cuda.is_available() else (
        "mps" if torch.backends.mps.is_available() else "cpu"
    )
    _model = ChatterboxTTS.from_pretrained(device=_device)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            try:
                length = int(
                    self.headers.get("Content-Length", 0)
                )
                body = json.loads(self.rfile.read(length))
                text = body.get("input", "")
                if not text.strip():
                    self.send_response(400)
                    self.end_headers()
                    return
                # Cap text length for safety
                text = text[:4000]
                wav = _model.generate(text)
                buf = io.BytesIO()
                torchaudio.save(
                    buf, wav, _model.sr, format="wav"
                )
                audio_bytes = buf.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", "audio/wav")
                self.send_header(
                    "Content-Length", str(len(audio_bytes))
                )
                self.end_headers()
                self.wfile.write(audio_bytes)
            except Exception as e:
                try:
                    err = json.dumps(
                        {{"error": str(e)}}
                    ).encode()
                    self.send_response(500)
                    self.send_header(
                        "Content-Type", "application/json"
                    )
                    self.end_headers()
                    self.wfile.write(err)
                except Exception:
                    pass

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{{"status":"ok"}}')

        def log_message(self, *a):
            pass

    HTTPServer(("0.0.0.0", {port}), Handler).serve_forever()
except Exception as e:
    print(
        f"Chatterbox shim failed: {{e}}\\n"
        f"{{traceback.format_exc()}}",
        file=sys.stderr,
    )
    sys.exit(1)
"""
