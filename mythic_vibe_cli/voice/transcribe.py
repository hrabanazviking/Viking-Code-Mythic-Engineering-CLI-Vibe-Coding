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

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


DEFAULT_ENGINE = "stub"
DEFAULT_LANGUAGE = "en"
DEFAULT_MODEL = "base"
KNOWN_ENGINES: tuple[str, ...] = ("stub", "whisper")


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
            import whisper  # type: ignore[import-not-found]
        except ImportError as exc:
            raise MissingExtraError(
                "openai-whisper",
                "Install with `pip install openai-whisper`. "
                "Note: whisper requires ffmpeg on PATH for audio decoding.",
            ) from exc
        self._module = whisper

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


__all__ = [
    "DEFAULT_ENGINE",
    "DEFAULT_LANGUAGE",
    "DEFAULT_MODEL",
    "KNOWN_ENGINES",
    "MissingExtraError",
    "StubTranscriber",
    "Transcriber",
    "TranscriptionRequest",
    "TranscriptionResult",
    "WhisperTranscriber",
    "make_transcriber",
    "transcribe",
]
