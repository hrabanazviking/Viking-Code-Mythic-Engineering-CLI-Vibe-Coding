"""Voice bridge for Whisper STT and Chatterbox TTS.

This module is intentionally defensive and crash-resistant:

- **Circuit breakers** with jittered exponential backoff prevent cascade
  failures from overwhelming the main game loop.
- **Auto-restart** of crashed voice servers via the local_servers module.
- **Input sanitization** strips control characters and caps TTS text length.
- **Defensive JSON parsing** never crashes on malformed server responses.
- **Safe cleanup** of temporary files even on unscheduled crashes.
- **Graceful degradation**: every public method is wrapped in a top-level
  try/except so a voice subsystem failure never kills the game.

Cross-platform auto-detection fills in recording and playback commands when
config values are blank, supporting Windows, macOS, Linux, Android (Termux),
and iOS (a-Shell / iSH).
"""

from __future__ import annotations

import logging
import os
import platform
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Maximum TTS text length to send to Chatterbox (prevent OOM on GPU)
_MAX_TTS_TEXT_LEN = 4000

# Maximum recording file size (100 MB) to prevent runaway recordings
_MAX_RECORDING_SIZE = 100 * 1024 * 1024


# ---------------------------------------------------------------------------
# Cross-platform detection helpers
# ---------------------------------------------------------------------------


def _check_command_exists(cmd: str) -> bool:
    """Return True if *cmd* is on PATH (uses shutil.which)."""
    try:
        return shutil.which(cmd) is not None
    except Exception:
        return False


def _detect_platform() -> str:
    """Return a canonical platform tag.

    Returns one of: 'windows', 'macos', 'linux', 'android', 'ios',
    'unknown'.
    """
    try:
        system = platform.system().lower()
    except Exception:
        return "unknown"

    if system == "linux" and (
        os.environ.get("PREFIX", "").startswith("/data/data/com.termux")
        or os.environ.get("TERMUX_VERSION")
    ):
        return "android"

    if system == "darwin":
        if os.environ.get("ISHROOT") or os.path.isdir("/var/mobile"):
            return "ios"
        return "macos"

    if system == "windows" or sys.platform.startswith("win"):
        return "windows"

    if system == "linux":
        return "linux"

    return "unknown"


def _auto_detect_recording_command() -> str:
    """Best-effort recording command for the current platform.

    Returns ``""`` when no recording method can be found.
    """
    plat = _detect_platform()

    if plat == "android":
        if _check_command_exists("termux-microphone-record"):
            return "termux-microphone-record -l 8 -f {output_file}"

    elif plat == "ios":
        if _check_command_exists("record"):
            return "record -d 8 {output_file}"

    elif plat == "macos":
        if _check_command_exists("ffmpeg"):
            return 'ffmpeg -y -f avfoundation -i ":0" -t 8 {output_file}'
        if _check_command_exists("sox"):
            return "sox -d -t wav {output_file} trim 0 8"

    elif plat == "windows":
        if _check_command_exists("ffmpeg"):
            return 'ffmpeg -y -f dshow -i audio="Microphone" -t 8 {output_file}'
        return (
            'powershell -NoProfile -Command "'
            "Add-Type -AssemblyName System.Speech;"
            "$r = New-Object "
            "System.Speech.Recognition."
            "SpeechRecognitionEngine;"
            "$r.SetInputToDefaultAudioDevice();"
            "Start-Sleep -Seconds 8;"
            '"'
        )

    else:  # linux / unknown
        if _check_command_exists("arecord"):
            return "arecord -f cd -d 8 {output_file}"
        if _check_command_exists("ffmpeg"):
            return "ffmpeg -y -f pulse -i default -t 8 {output_file}"
        if _check_command_exists("sox"):
            return "sox -d -t wav {output_file} trim 0 8"

    return ""


def _auto_detect_playback_command() -> str:
    """Best-effort playback command for the current platform."""
    plat = _detect_platform()

    if plat == "android":
        if _check_command_exists("termux-media-player"):
            return "termux-media-player play {audio_file}"
        if _check_command_exists("play"):
            return "play {audio_file}"

    elif plat == "ios":
        if _check_command_exists("play"):
            return "play {audio_file}"

    elif plat == "macos":
        if _check_command_exists("afplay"):
            return "afplay {audio_file}"
        if _check_command_exists("ffplay"):
            return "ffplay -nodisp -autoexit {audio_file}"

    elif plat == "windows":
        return (
            "powershell -NoProfile -Command "
            '"(New-Object Media.SoundPlayer '
            "'{audio_file}').PlaySync();\""
        )

    else:  # linux / unknown
        if _check_command_exists("aplay"):
            return "aplay {audio_file}"
        if _check_command_exists("paplay"):
            return "paplay {audio_file}"
        if _check_command_exists("ffplay"):
            return "ffplay -nodisp -autoexit {audio_file}"
        if _check_command_exists("play"):
            return "play {audio_file}"

    return ""


# ---------------------------------------------------------------------------
# Input sanitization
# ---------------------------------------------------------------------------

_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _sanitize_tts_text(text: str) -> str:
    """Strip control chars, collapse whitespace, cap length."""
    if not isinstance(text, str):
        text = str(text)
    text = _CONTROL_CHARS.sub("", text)
    text = " ".join(text.split())
    if len(text) > _MAX_TTS_TEXT_LEN:
        # Truncate to the last sentence boundary
        truncated = text[:_MAX_TTS_TEXT_LEN]
        for sep in (". ", "! ", "? ", "\n"):
            idx = truncated.rfind(sep)
            if idx > _MAX_TTS_TEXT_LEN // 2:
                truncated = truncated[: idx + 1]
                break
        text = truncated
    return text.strip()


# ---------------------------------------------------------------------------
# Circuit breaker with jittered backoff
# ---------------------------------------------------------------------------


@dataclass
class VoiceCircuit:
    """Tracks failures and cooldown for self-healing retries."""

    failures: int = 0
    open_until: float = 0.0
    total_failures: int = 0  # lifetime counter for diagnostics

    def is_open(self) -> bool:
        if time.time() >= self.open_until and self.open_until > 0:
            # half-open: allow one probe through
            self.open_until = 0.0
        return time.time() < self.open_until

    def mark_success(self) -> None:
        self.failures = 0
        self.open_until = 0.0

    def mark_failure(
        self,
        base_cooldown: float = 1.5,
        max_cooldown: float = 60.0,
    ) -> None:
        self.failures += 1
        self.total_failures += 1
        # exponential backoff with ±25% jitter
        raw = base_cooldown * (2 ** min(self.failures - 1, 8))
        cooldown = min(max_cooldown, raw)
        jitter = cooldown * 0.25 * (random.random() * 2 - 1)
        self.open_until = time.time() + cooldown + jitter


# ---------------------------------------------------------------------------
# Safe HTTP helper
# ---------------------------------------------------------------------------


def _safe_http_post(
    url: str,
    *,
    data: Optional[Dict] = None,
    files: Optional[Dict] = None,
    json_body: Optional[Dict] = None,
    timeout: float = 60,
) -> Optional[Dict[str, Any]]:
    """POST with defensive JSON parsing. Never raises."""
    if httpx is None:
        logger.error("httpx not installed — voice HTTP calls unavailable")
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            if json_body is not None:
                resp = client.post(url, json=json_body)
            else:
                resp = client.post(url, data=data or {}, files=files or {})
        resp.raise_for_status()
        try:
            return resp.json()
        except Exception:
            # Non-JSON response — return raw bytes wrapper
            return {"_raw": resp.content}
    except Exception as exc:
        logger.debug("HTTP POST to %s failed: %s", url, exc)
        return None


def _safe_http_get(url: str, timeout: float = 5) -> Optional[int]:
    """GET and return status code, or None on failure."""
    if httpx is None:
        return None
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url)
        return resp.status_code
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Voice bridge
# ---------------------------------------------------------------------------


@dataclass
class VoiceBridge:
    """Coordinates mic capture, Whisper transcription, Chatterbox TTS.

    Every public method is wrapped in a top-level try/except so a
    voice subsystem crash never propagates to the game loop.
    """

    config: Dict[str, Any]
    stt_circuit: VoiceCircuit = field(default_factory=VoiceCircuit)
    tts_circuit: VoiceCircuit = field(default_factory=VoiceCircuit)
    tts_enabled: bool = False
    detected_platform: str = ""
    detected_recording_cmd: str = ""
    detected_playback_cmd: str = ""
    _temp_files: list = field(default_factory=list)

    # ---- construction -----------------------------------------------------

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "VoiceBridge":
        try:
            voice_cfg = config.get("voice", {}) if isinstance(config, dict) else {}
        except Exception:
            voice_cfg = {}

        bridge = cls(config=voice_cfg)
        bridge.tts_enabled = bool(voice_cfg.get("auto_tts", False))
        bridge.detected_platform = _detect_platform()

        # recording command
        rec_cfg = voice_cfg.get("recording", {})
        configured_rec = ""
        if isinstance(rec_cfg, dict):
            configured_rec = str(rec_cfg.get("command", "")).strip()
        if configured_rec:
            bridge.detected_recording_cmd = configured_rec
        else:
            bridge.detected_recording_cmd = _auto_detect_recording_command()
            if bridge.detected_recording_cmd:
                logger.info(
                    "Auto-detected recording cmd (%s): %s",
                    bridge.detected_platform,
                    bridge.detected_recording_cmd,
                )
            else:
                logger.warning(
                    "No recording command for '%s'. Set voice.recording.command.",
                    bridge.detected_platform,
                )

        # playback command
        play_cfg = voice_cfg.get("playback", {})
        configured_play = ""
        if isinstance(play_cfg, dict):
            configured_play = str(play_cfg.get("command", "")).strip()
        if configured_play:
            bridge.detected_playback_cmd = configured_play
        else:
            bridge.detected_playback_cmd = _auto_detect_playback_command()
            if bridge.detected_playback_cmd:
                logger.info(
                    "Auto-detected playback cmd (%s): %s",
                    bridge.detected_platform,
                    bridge.detected_playback_cmd,
                )
            else:
                logger.warning(
                    "No playback command for '%s'. Set voice.playback.command.",
                    bridge.detected_platform,
                )

        return bridge

    # ---- public API (crash-proof) -----------------------------------------

    def is_enabled(self) -> bool:
        try:
            return bool(self.config.get("enabled", False))
        except Exception:
            return False

    def get_status(self) -> Dict[str, Any]:
        try:
            stt_cfg = self.config.get("stt", {})
            tts_cfg = self.config.get("tts", {})
            return {
                "enabled": self.is_enabled(),
                "auto_tts": self.tts_enabled,
                "platform": self.detected_platform,
                "recording_cmd": (self.detected_recording_cmd or "(none)"),
                "playback_cmd": (self.detected_playback_cmd or "(none)"),
                "whisper_url": str(
                    stt_cfg.get(
                        "whisper_url",
                        "http://127.0.0.1:8000/v1/audio/transcriptions",
                    )
                ),
                "chatterbox_url": str(
                    tts_cfg.get(
                        "chatterbox_url",
                        "http://127.0.0.1:8001/v1/audio/speech",
                    )
                ),
                "stt_circuit_open": self.stt_circuit.is_open(),
                "tts_circuit_open": self.tts_circuit.is_open(),
                "stt_failures": self.stt_circuit.failures,
                "stt_total_failures": (self.stt_circuit.total_failures),
                "tts_failures": self.tts_circuit.failures,
                "tts_total_failures": (self.tts_circuit.total_failures),
            }
        except Exception:
            return {"enabled": False, "error": "status failed"}

    def toggle_tts(self, enabled: bool) -> None:
        self.tts_enabled = bool(enabled)

    def check_health(self) -> Dict[str, bool]:
        """Ping Whisper and Chatterbox endpoints."""
        results: Dict[str, bool] = {
            "whisper": False,
            "chatterbox": False,
        }
        try:
            stt_cfg = self.config.get("stt", {})
            whisper_url = str(
                stt_cfg.get(
                    "whisper_url",
                    "http://127.0.0.1:8000/v1/audio/transcriptions",
                )
            )
            base = whisper_url.rsplit("/v1", 1)[0]
            code = _safe_http_get(base, timeout=5)
            results["whisper"] = code is not None and code < 500
        except Exception:
            pass

        try:
            tts_cfg = self.config.get("tts", {})
            cb_url = str(
                tts_cfg.get(
                    "chatterbox_url",
                    "http://127.0.0.1:8001/v1/audio/speech",
                )
            )
            base = cb_url.rsplit("/v1", 1)[0]
            code = _safe_http_get(base, timeout=5)
            results["chatterbox"] = code is not None and code < 500
        except Exception:
            pass

        return results

    # ---- STT (crash-proof) ------------------------------------------------

    def capture_and_transcribe(self) -> Optional[str]:
        """Capture audio and transcribe. Never raises."""
        try:
            if not self.is_enabled():
                return None
            if self.stt_circuit.is_open():
                logger.debug("STT circuit open — skipping capture")
                return None

            audio_file = self._record_audio_to_tempfile()
            if not audio_file:
                self._mark_stt_failure("mic capture failed")
                return None

            try:
                transcript = self._transcribe_audio(audio_file)
                if transcript:
                    self.stt_circuit.mark_success()
                else:
                    self._mark_stt_failure("empty transcript")
                return transcript
            finally:
                self._safe_delete(audio_file)
        except Exception as exc:
            logger.error(
                "STT crash (game continues): %s\n%s",
                exc,
                traceback.format_exc(),
            )
            self._mark_stt_failure(f"crash: {exc}")
            return None

    # ---- TTS (crash-proof) ------------------------------------------------

    def speak(self, text: str) -> bool:
        """Synthesize speech and play. Never raises."""
        try:
            if not self.is_enabled():
                return False
            if not self.tts_enabled:
                return False
            if self.tts_circuit.is_open():
                logger.debug("TTS circuit open — skipping speech")
                return False

            text = _sanitize_tts_text(text)
            if not text:
                return False

            tts_cfg = self.config.get("tts", {})
            retries = max(1, int(tts_cfg.get("max_retries", 3)))
            delay = float(
                self.config.get("recovery", {}).get("retry_delay_seconds", 0.8)
            )

            for attempt in range(1, retries + 1):
                try:
                    audio = self._synthesize_chatterbox(text)
                    if not audio:
                        logger.debug(
                            "TTS attempt %d/%d: no audio",
                            attempt,
                            retries,
                        )
                        time.sleep(delay * attempt)
                        continue
                    self._play_audio(audio)
                    self._safe_delete(audio)
                    self.tts_circuit.mark_success()
                    return True
                except Exception as exc:
                    logger.warning(
                        "TTS attempt %d/%d failed: %s",
                        attempt,
                        retries,
                        exc,
                    )
                    time.sleep(delay * attempt)

            self._mark_tts_failure("all TTS attempts failed")
            return False
        except Exception as exc:
            logger.error(
                "TTS crash (game continues): %s\n%s",
                exc,
                traceback.format_exc(),
            )
            self._mark_tts_failure(f"crash: {exc}")
            return False

    # ---- internals --------------------------------------------------------

    def _record_audio_to_tempfile(self) -> Optional[Path]:
        cmd_template = self.detected_recording_cmd
        if not cmd_template:
            logger.warning("No recording command configured")
            return None

        output_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                output_path = Path(handle.name)
            self._temp_files.append(output_path)

            # Split template and replace placeholder safely
            cmd_list = shlex.split(cmd_template)
            cmd_list = [
                arg.replace("{output_file}", str(output_path)) for arg in cmd_list
            ]

            rec_cfg = self.config.get("recording", {})
            timeout = 30
            if isinstance(rec_cfg, dict):
                timeout = int(rec_cfg.get("timeout_seconds", 30))

            result = subprocess.run(
                cmd_list,
                shell=False,
                timeout=timeout,
                capture_output=True,
            )
            if result.returncode != 0:
                stderr = (
                    result.stderr.decode(errors="replace")[:200]
                    if result.stderr
                    else ""
                )
                logger.warning(
                    "Recording cmd exited %d: %s",
                    result.returncode,
                    stderr,
                )
                # Still check if a file was produced
                if not (output_path.exists() and output_path.stat().st_size > 512):
                    self._safe_delete(output_path)
                    return None

            if not output_path.exists():
                return None
            fsize = output_path.stat().st_size
            if fsize < 512:
                logger.warning("Recording too small (%d bytes)", fsize)
                self._safe_delete(output_path)
                return None
            if fsize > _MAX_RECORDING_SIZE:
                logger.warning(
                    "Recording too large (%d bytes), discarding",
                    fsize,
                )
                self._safe_delete(output_path)
                return None
            return output_path
        except subprocess.TimeoutExpired:
            logger.warning("Recording timed out")
            self._safe_delete(output_path)
            return None
        except Exception as exc:
            logger.warning("Recording failed: %s", exc)
            self._safe_delete(output_path)
            return None

    def _transcribe_audio(self, audio_file: Path) -> Optional[str]:
        stt_cfg = self.config.get("stt", {})
        if not isinstance(stt_cfg, dict):
            stt_cfg = {}
        whisper_url = str(
            stt_cfg.get(
                "whisper_url",
                "http://127.0.0.1:8000/v1/audio/transcriptions",
            )
        )
        model = str(stt_cfg.get("model", "whisper-1"))
        timeout = int(stt_cfg.get("timeout_seconds", 60))
        retries = max(1, int(stt_cfg.get("max_retries", 3)))
        delay = float(self.config.get("recovery", {}).get("retry_delay_seconds", 0.8))

        for attempt in range(1, retries + 1):
            try:
                if not audio_file.exists():
                    logger.warning("Audio file vanished")
                    return None
                with audio_file.open("rb") as stream:
                    files = {
                        "file": (
                            audio_file.name,
                            stream,
                            "audio/wav",
                        )
                    }
                    data = {"model": model}
                    payload = _safe_http_post(
                        whisper_url,
                        data=data,
                        files=files,
                        timeout=timeout,
                    )
                if payload is None:
                    logger.warning(
                        "Whisper attempt %d/%d: no response",
                        attempt,
                        retries,
                    )
                    time.sleep(delay * attempt)
                    continue
                text = ""
                if isinstance(payload, dict):
                    text = str(payload.get("text", "")).strip()
                if text:
                    return self._correct_transcript(text)
                logger.debug(
                    "Whisper returned empty text on attempt %d",
                    attempt,
                )
                time.sleep(delay * attempt)
            except Exception as exc:
                logger.warning(
                    "Whisper attempt %d/%d error: %s",
                    attempt,
                    retries,
                    exc,
                )
                time.sleep(delay * attempt)
        return None

    def _correct_transcript(self, text: str) -> str:
        if not text:
            return ""
        try:
            corrections = self.config.get("stt", {}).get("corrections", {})
            if isinstance(corrections, dict):
                for wrong, fixed in corrections.items():
                    text = text.replace(str(wrong), str(fixed))
        except Exception:
            pass
        return " ".join(text.split())

    def _synthesize_chatterbox(self, text: str) -> Optional[Path]:
        tts_cfg = self.config.get("tts", {})
        if not isinstance(tts_cfg, dict):
            tts_cfg = {}
        url = str(
            tts_cfg.get(
                "chatterbox_url",
                "http://127.0.0.1:8001/v1/audio/speech",
            )
        )
        model = str(tts_cfg.get("model", "chatterbox"))
        voice = str(tts_cfg.get("voice", "default"))
        timeout = int(tts_cfg.get("timeout_seconds", 90))

        body = {
            "model": model,
            "voice": voice,
            "input": text,
        }
        result = _safe_http_post(url, json_body=body, timeout=timeout)
        if result is None:
            return None

        # Extract audio bytes
        audio_bytes = result.get("_raw", b"")
        if not audio_bytes:
            logger.warning("Chatterbox returned no audio data")
            return None
        if len(audio_bytes) < 128:
            logger.warning(
                "Chatterbox audio too small (%d bytes)",
                len(audio_bytes),
            )
            return None

        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as handle:
                audio_file = Path(handle.name)
                handle.write(audio_bytes)
            self._temp_files.append(audio_file)
            return audio_file
        except Exception as exc:
            logger.warning("Could not write TTS audio to temp: %s", exc)
            return None

    def _play_audio(self, audio_file: Path) -> None:
        cmd_template = self.detected_playback_cmd
        if not cmd_template:
            logger.warning("No playback command — skip TTS")
            return
        if not audio_file.exists():
            logger.warning("Audio file missing for playback")
            return

        # Split template and replace placeholder safely
        cmd_list = shlex.split(cmd_template)
        cmd_list = [arg.replace("{audio_file}", str(audio_file)) for arg in cmd_list]

        play_cfg = self.config.get("playback", {})
        timeout = 120
        if isinstance(play_cfg, dict):
            timeout = int(play_cfg.get("timeout_seconds", 120))

        try:
            result = subprocess.run(
                cmd_list,
                shell=False,
                timeout=timeout,
                capture_output=True,
            )
            if result.returncode != 0:
                stderr = (
                    result.stderr.decode(errors="replace")[:200]
                    if result.stderr
                    else ""
                )
                logger.warning(
                    "Playback exited %d: %s",
                    result.returncode,
                    stderr,
                )
        except subprocess.TimeoutExpired:
            logger.warning("Playback timed out after %ds", timeout)
        except Exception as exc:
            logger.warning("Playback failed: %s", exc)

    def _mark_stt_failure(self, reason: str) -> None:
        logger.warning("STT failure: %s", reason)
        try:
            recovery = self.config.get("recovery", {})
            if not isinstance(recovery, dict):
                recovery = {}
            self.stt_circuit.mark_failure(
                base_cooldown=float(recovery.get("base_cooldown_seconds", 1.5)),
                max_cooldown=float(recovery.get("max_cooldown_seconds", 60.0)),
            )
        except Exception:
            self.stt_circuit.failures += 1

    def _mark_tts_failure(self, reason: str) -> None:
        logger.warning("TTS failure: %s", reason)
        try:
            recovery = self.config.get("recovery", {})
            if not isinstance(recovery, dict):
                recovery = {}
            self.tts_circuit.mark_failure(
                base_cooldown=float(recovery.get("base_cooldown_seconds", 1.5)),
                max_cooldown=float(recovery.get("max_cooldown_seconds", 60.0)),
            )
        except Exception:
            self.tts_circuit.failures += 1

    def _safe_delete(self, path: Optional[Path]) -> None:
        """Delete a temp file, ignoring all errors."""
        if path is None:
            return
        try:
            if path in self._temp_files:
                self._temp_files.remove(path)
            path.unlink(missing_ok=True)
        except Exception:
            pass

    def cleanup(self) -> None:
        """Delete all tracked temporary files."""
        for path in list(self._temp_files):
            self._safe_delete(path)
