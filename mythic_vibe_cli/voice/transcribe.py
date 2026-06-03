"""Voice transcription (PH-07 slice 7.1).

Pure-stdlib orchestration over a typed :class:`Transcriber`
Protocol. Real audio backends (`whisper`) are gated behind
try-import so the CLI surface and tests work on any machine
without an audio dep.

Public surface:

- :class:`TranscriptionRequest` — frozen input payload.
- :class:`TranscriptionResult` — frozen output payload.
- :class:`Transcriber` — Protocol every backend implements.
- :class:`StubTranscriber` — always works; returns canned text or
  the source file's contents (when the file is text-shaped) /
  basename (when it isn't). Default in tests + when no audio
  dep is installed.
- :class:`WhisperTranscriber` — try-imports ``whisper`` from the
  ``openai-whisper`` package. Raises :class:`MissingExtraError`
  with a clear install hint when the package isn't importable.
- :func:`make_transcriber(name)` — factory that maps a string
  name to a configured :class:`Transcriber`.

Cross-platform: stdlib only on the must-work path.
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


DEFAULT_ENGINE = "stub"
DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "base"
KNOWN_ENGINES: tuple[str, ...] = ("stub", "whisper")

DEFAULT_MIC_SAMPLE_RATE = 16_000
DEFAULT_MIC_CHANNELS = 1
DEFAULT_MIC_DURATION = 5.0
_REPO_ROOT = Path(__file__).resolve().parents[2]


class MissingExtraError(RuntimeError):
    """Raised when a backend tries to import a package that isn't
    installed. The slice 7.1 CLI catches this and writes a clean
    message including the install hint."""

    def __init__(self, extra: str, install_hint: str) -> None:
        super().__init__(
            f"Optional dependency missing: {extra}. {install_hint}"
        )
        self.extra = extra
        self.install_hint = install_hint


def _module_is_from_dormant_repo_path(module: Any, package_name: str) -> bool:
    raw_path = getattr(module, "__file__", "") or ""
    if not raw_path:
        return False
    try:
        path = Path(raw_path).resolve()
        return path.is_relative_to(_REPO_ROOT / package_name)
    except (OSError, ValueError):
        return False


def _import_external_package(package_name: str) -> Any:
    existing = sys.modules.get(package_name)
    if existing is not None:
        if _module_is_from_dormant_repo_path(existing, package_name):
            raise ImportError(
                f"{package_name} resolves to dormant repo path, not an external package"
            )
        return existing

    spec = importlib.util.find_spec(package_name)
    if spec is None:
        raise ImportError(f"{package_name} package not found")
    origin = spec.origin or ""
    search_locations = list(spec.submodule_search_locations or [])
    candidate_paths = [origin, *search_locations]
    for raw_path in candidate_paths:
        if not raw_path:
            continue
        try:
            path = Path(raw_path).resolve()
        except (OSError, ValueError):
            continue
        if path == _REPO_ROOT / package_name or path.is_relative_to(
            _REPO_ROOT / package_name
        ):
            raise ImportError(
                f"{package_name} resolves to dormant repo path, not an external package"
            )
    return importlib.import_module(package_name)


@dataclass(frozen=True)
class TranscriptionRequest:
    """Input payload. ``source_path`` is the only required field —
    every backend (including the stub) needs *something* to
    transcribe. ``engine`` selects the backend; ``language`` and
    ``model`` are passed through to backends that honour them."""

    source_path: str
    engine: str = DEFAULT_ENGINE
    language: str = DEFAULT_LANGUAGE
    model: str = DEFAULT_MODEL
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_path": self.source_path,
            "engine": self.engine,
            "language": self.language,
            "model": self.model,
            "duration_seconds": self.duration_seconds,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TranscriptionResult:
    """Output payload. ``dry_run`` is set by stub / placeholder
    backends so callers can distinguish a real transcription from
    a synthetic one. ``error`` is non-empty when the backend
    failed but didn't raise."""

    text: str
    source_path: str
    engine: str
    model: str
    language: str
    dry_run: bool = False
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "source_path": self.source_path,
            "engine": self.engine,
            "model": self.model,
            "language": self.language,
            "dry_run": self.dry_run,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


@runtime_checkable
class Transcriber(Protocol):
    """Backend interface. Implementations may raise
    :class:`MissingExtraError` from their constructor or
    :meth:`transcribe` if a required package isn't installed.
    """

    name: str

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        ...


# ---- Stub backend ------------------------------------------------------


@dataclass
class StubTranscriber:
    """Default backend. Behaviours:

    - When ``request.source_path`` points to a small text file
      (extension ``.txt``, ``.md``, or no extension), returns the
      file contents verbatim. This matches the slice 7.4 test
      harness convention of using text fixtures as canned
      transcripts.
    - When the file is missing or is some other binary shape,
      returns ``"[stub transcript of <basename>]"``.

    Always returns ``dry_run=True`` so the recording surface in
    PH-15 doesn't treat the result as a real provider response.
    """

    name: str = "stub"

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        path = Path(request.source_path) if request.source_path else None
        text = ""
        if path is not None and path.is_file():
            suffix = path.suffix.lower()
            if suffix in {"", ".txt", ".md"}:
                try:
                    text = path.read_text(encoding="utf-8").strip()
                except OSError:
                    text = ""
        if not text and path is not None:
            text = f"[stub transcript of {path.name or request.source_path}]"
        elif not text:
            text = "[stub transcript: no source]"
        return TranscriptionResult(
            text=text,
            source_path=request.source_path,
            engine=self.name,
            model=request.model,
            language=request.language,
            dry_run=True,
            metadata={"source": "stub"},
        )


# ---- Whisper backend ---------------------------------------------------


@dataclass
class WhisperTranscriber:
    """Optional backend backed by the ``openai-whisper`` package
    (MIT license, local inference). Loads the model lazily so
    importing the module doesn't drag in torch.

    The constructor try-imports ``whisper`` and raises
    :class:`MissingExtraError` with a clean install hint when the
    package isn't available. Slice 7.1's CLI handler catches that
    and surfaces a helpful error.
    """

    name: str = "whisper"
    _module: Any = None

    def __post_init__(self) -> None:
        try:
            self._module = _import_external_package("whisper")
        except ImportError as exc:
            raise MissingExtraError(
                "openai-whisper",
                "Install with `pip install openai-whisper`. "
                "Note: whisper requires ffmpeg on PATH for audio decoding.",
            ) from exc

    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if self._module is None:  # pragma: no cover — __post_init__ guards
            raise MissingExtraError(
                "openai-whisper",
                "Install with `pip install openai-whisper`.",
            )
        path = Path(request.source_path)
        if not path.is_file():
            return TranscriptionResult(
                text="",
                source_path=request.source_path,
                engine=self.name,
                model=request.model,
                language=request.language,
                dry_run=False,
                error=f"Source file not found: {request.source_path}",
            )
        try:
            model = self._module.load_model(request.model)
            result = model.transcribe(str(path), language=request.language or None)
        except Exception as exc:  # noqa: BLE001 — whisper failures shouldn't crash callers
            return TranscriptionResult(
                text="",
                source_path=request.source_path,
                engine=self.name,
                model=request.model,
                language=request.language,
                dry_run=False,
                error=str(exc) or type(exc).__name__,
            )
        text = ""
        if isinstance(result, dict):
            raw = result.get("text", "")
            if isinstance(raw, str):
                text = raw.strip()
        return TranscriptionResult(
            text=text,
            source_path=request.source_path,
            engine=self.name,
            model=request.model,
            language=request.language,
            dry_run=False,
            metadata={"source": "whisper"},
        )


# ---- Factory + orchestrator -------------------------------------------


def make_transcriber(name: str) -> Transcriber:
    """Map a string engine name to a configured backend. Unknown
    names raise :class:`ValueError` with the list of supported
    engines so the CLI can surface a clean error."""
    cleaned = (name or "").strip().lower()
    if cleaned in {"", "stub"}:
        return StubTranscriber()
    if cleaned == "whisper":
        return WhisperTranscriber()
    raise ValueError(
        f"Unknown transcribe engine {name!r}. "
        f"Supported: {', '.join(KNOWN_ENGINES)}."
    )


def transcribe(
    request: TranscriptionRequest,
    *,
    transcriber: Transcriber | None = None,
) -> TranscriptionResult:
    """Convenience wrapper. Uses :func:`make_transcriber` when no
    ``transcriber`` is supplied. Catches
    :class:`MissingExtraError` and returns a structured error
    result rather than re-raising — keeps the CLI's exception
    surface narrow."""
    if transcriber is None:
        try:
            transcriber = make_transcriber(request.engine)
        except MissingExtraError as exc:
            return TranscriptionResult(
                text="",
                source_path=request.source_path,
                engine=request.engine,
                model=request.model,
                language=request.language,
                dry_run=False,
                error=str(exc),
                metadata={"missing_extra": exc.extra},
            )
        except ValueError as exc:
            return TranscriptionResult(
                text="",
                source_path=request.source_path,
                engine=request.engine,
                model=request.model,
                language=request.language,
                dry_run=False,
                error=str(exc),
            )
    return transcriber.transcribe(request)


# ---- Microphone capture (PH-07 follow-up) -----------------------------


@runtime_checkable
class MicRecorder(Protocol):
    """Backend interface for microphone capture. ``record`` returns
    raw int16 PCM bytes for ``duration`` seconds at the recorder's
    configured sample rate / channel count. Tests inject fakes;
    production uses :class:`SoundDeviceRecorder`."""

    sample_rate: int
    channels: int

    def record(self, duration: float) -> bytes:
        ...


@dataclass
class SoundDeviceRecorder:
    """Real microphone backend. Try-imports ``sounddevice`` (and the
    numpy it depends on) at construction time so the CLI fails loudly
    with a clean install hint when the package isn't available.

    Cross-platform: sounddevice wraps PortAudio (Linux ALSA / macOS
    CoreAudio / Windows WASAPI / DirectSound)."""

    sample_rate: int = DEFAULT_MIC_SAMPLE_RATE
    channels: int = DEFAULT_MIC_CHANNELS
    _module: Any = None
    _numpy: Any = None

    def __post_init__(self) -> None:
        try:
            import sounddevice  # type: ignore[import-not-found]
            import numpy  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MissingExtraError(
                "sounddevice",
                "Install with `pip install sounddevice numpy` for "
                "microphone capture (cross-platform via PortAudio).",
            ) from exc
        self._module = sounddevice
        self._numpy = numpy

    def record(self, duration: float) -> bytes:
        if self._module is None or self._numpy is None:  # pragma: no cover — guarded by __post_init__
            raise MissingExtraError(
                "sounddevice",
                "Install with `pip install sounddevice numpy`.",
            )
        if duration <= 0:
            raise ValueError(f"duration must be > 0 seconds, got {duration!r}")
        frames = int(round(duration * self.sample_rate))
        buf = self._module.rec(
            frames,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype="int16",
        )
        self._module.wait()
        # numpy int16 array → little-endian PCM bytes.
        return buf.tobytes()


def _write_wav_temp(
    pcm_bytes: bytes,
    *,
    sample_rate: int,
    channels: int,
    sample_width: int = 2,
) -> str:
    """Write raw PCM bytes to a temp WAV file. Returns the path.
    The caller owns the file's lifecycle — the typical pattern is
    try / finally + ``Path(p).unlink(missing_ok=True)``."""
    fd, path = tempfile.mkstemp(prefix="mythic-mic-", suffix=".wav")
    os.close(fd)
    try:
        with wave.open(path, "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(sample_width)
            wav.setframerate(sample_rate)
            wav.writeframes(pcm_bytes)
    except Exception:  # noqa: BLE001 — clean up partial file on any failure
        Path(path).unlink(missing_ok=True)
        raise
    return path


def record_to_temp_wav(
    duration: float,
    *,
    sample_rate: int = DEFAULT_MIC_SAMPLE_RATE,
    channels: int = DEFAULT_MIC_CHANNELS,
    recorder: MicRecorder | None = None,
) -> str:
    """Record ``duration`` seconds of microphone audio and write it
    to a temp WAV. Returns the path.

    If ``recorder`` is supplied, uses it verbatim — tests inject a
    deterministic fake. Otherwise constructs a
    :class:`SoundDeviceRecorder` (which try-imports sounddevice and
    raises :class:`MissingExtraError` cleanly when the dep is
    missing).
    """
    if recorder is None:
        recorder = SoundDeviceRecorder(sample_rate=sample_rate, channels=channels)
    pcm = recorder.record(duration)
    return _write_wav_temp(
        pcm,
        sample_rate=recorder.sample_rate,
        channels=recorder.channels,
    )


__all__ = [
    "DEFAULT_ENGINE",
    "DEFAULT_LANGUAGE",
    "DEFAULT_MIC_CHANNELS",
    "DEFAULT_MIC_DURATION",
    "DEFAULT_MIC_SAMPLE_RATE",
    "DEFAULT_MODEL",
    "KNOWN_ENGINES",
    "MicRecorder",
    "MissingExtraError",
    "SoundDeviceRecorder",
    "StubTranscriber",
    "Transcriber",
    "TranscriptionRequest",
    "TranscriptionResult",
    "WhisperTranscriber",
    "make_transcriber",
    "record_to_temp_wav",
    "transcribe",
]
