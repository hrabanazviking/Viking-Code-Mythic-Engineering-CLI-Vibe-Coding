"""TTS notifications (PH-07 slice 7.3).

Pure-stdlib orchestration over a typed :class:`TTSEngine`
Protocol. Real audio backends (`chatterbox`) are gated behind
try-import so the CLI surface and tests work without any audio
dep installed.

Default-disabled: ``MYTHIC_VOICE_TTS_ENABLED`` must be set to a
truthy value (``1`` / ``true`` / ``yes``) before the orchestrator
will dispatch to the real engine. The slice 7.3 ``voice say``
command surfaces ``--force`` to bypass the env gate for direct
testing.

Public surface:

- :class:`TTSRequest`, :class:`TTSResult` — typed payloads.
- :class:`TTSEngine` — Protocol every backend implements.
- :class:`StubTTSEngine` — logs to stderr; never plays audio. Used
  as the default + in tests.
- :class:`ChatterboxEngine` — try-imports ``chatterbox``; raises
  :class:`MissingExtraError` with a clean install hint when the
  package isn't available.
- :func:`make_tts_engine(name)` — factory.
- :func:`is_tts_enabled()` — env-var gate.
- :func:`say(text, *, engine, force, ...)` — orchestrator that
  honours :func:`is_tts_enabled` unless ``force=True``.
"""

from __future__ import annotations

import os
import sys
import tempfile
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .transcribe import MissingExtraError, _try_import_package


TTS_ENABLED_ENV = "MYTHIC_VOICE_TTS_ENABLED"
CHATTERBOX_ISLAND_ENV = "MYTHIC_ISLAND_CHATTERBOX_ENABLED"
DEFAULT_TTS_ENGINE = "stub"
KNOWN_TTS_ENGINES: tuple[str, ...] = ("stub", "chatterbox")
_TRUTHY = {"1", "true", "yes", "on"}


def is_tts_enabled() -> bool:
    """Read :data:`TTS_ENABLED_ENV`. Empty / unset / falsy values
    return ``False`` — TTS stays default-disabled until the
    operator explicitly opts in."""
    raw = os.environ.get(TTS_ENABLED_ENV, "").strip().lower()
    return raw in _TRUTHY


def is_chatterbox_island_enabled() -> bool:
    """PH-09 Slice 9.4 — per-island feature flag for Chatterbox.

    The chatterbox engine requires BOTH
    :data:`TTS_ENABLED_ENV` (the broader voice gate from PH-07)
    AND :data:`CHATTERBOX_ISLAND_ENV` (this island-specific flag)
    to actually emit audio. Either off → chatterbox falls back to
    a non-spoken result with a clear ``skipped_reason``.

    Stub engine behaviour is unchanged — it stays gated by the
    broader TTS flag only.
    """
    raw = os.environ.get(CHATTERBOX_ISLAND_ENV, "").strip().lower()
    return raw in _TRUTHY


@dataclass(frozen=True)
class TTSRequest:
    text: str
    engine: str = DEFAULT_TTS_ENGINE
    voice: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "engine": self.engine,
            "voice": self.voice,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TTSResult:
    """``spoken`` is True only when the engine actually emitted
    audio. Stub + gated paths set it to False so callers can
    distinguish "spoken aloud" from "logged but not played"."""

    text: str
    engine: str
    spoken: bool
    skipped_reason: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "engine": self.engine,
            "spoken": self.spoken,
            "skipped_reason": self.skipped_reason,
            "error": self.error,
            "metadata": dict(self.metadata),
        }


@runtime_checkable
class TTSEngine(Protocol):
    name: str

    def say(self, request: TTSRequest) -> TTSResult:
        ...


# ---- Stub engine -------------------------------------------------------


@dataclass
class StubTTSEngine:
    """Default engine. Logs the text to stderr (so test capture
    layers see it) but never plays audio. ``spoken`` is always
    False — the operator gets a faithful "we did not actually
    speak" signal."""

    name: str = "stub"
    stream: Any = None

    def say(self, request: TTSRequest) -> TTSResult:
        target = self.stream if self.stream is not None else sys.stderr
        try:
            target.write(f"[voice-stub] {request.text}\n")
            target.flush()
        except Exception:  # noqa: BLE001 — stderr write shouldn't crash callers
            pass
        return TTSResult(
            text=request.text,
            engine=self.name,
            spoken=False,
            skipped_reason="stub engine — no audio emitted",
            metadata={"source": "stub"},
        )


# ---- Chatterbox engine ------------------------------------------------


@dataclass
class ChatterboxEngine:
    """Optional backend backed by the open-source ``chatterbox``
    package. Try-imports at construction time so the missing-extra
    case fails loudly with a clean install hint.
    """

    name: str = "chatterbox"
    voice: str = ""
    _module: Any = None
    # Additive 2026-05-02 (Phase A.1 of audit remediation): optional
    # fields used by the modern Chatterbox API path. ``output_path``
    # picks the .wav target for the generated waveform; empty means
    # a temp file is allocated. ``device`` is "auto" by default and
    # auto-detects cuda/mps/cpu via torch when available.
    output_path: str = ""
    device: str = "auto"

    def __post_init__(self) -> None:
        try:
            self._module = _try_import_package("chatterbox")
        except ImportError as exc:
            raise MissingExtraError(
                "chatterbox",
                "Install with `pip install chatterbox` (open-source TTS).",
            ) from exc

    # ---- Additive 2026-05-02: Modern Chatterbox API adapter ------------
    #
    # The pseudo-code audit (AUDIT_PSEUDOCODE_DEEP_2026-05-02.md, finding
    # #1) showed that the real chatterbox package exposes
    # ``ChatterboxTTS`` / ``ChatterboxMultilingualTTS`` (each with a
    # ``from_pretrained(device=...)`` classmethod and a ``generate(text)``
    # instance method that returns a torch waveform tensor). Saving the
    # waveform requires ``torchaudio.save(path, wav, sr)``. The legacy
    # probe for a top-level ``speak()`` function is kept below as a
    # fallback per the additive-only rule — but the modern path is
    # tried first.
    #
    # Helpers below are deliberately small and individually testable:
    # ``_resolve_modern_tts_cls`` for class detection (mockable),
    # ``_detect_device`` for hardware auto-pick, ``_resolve_output_path``
    # for filesystem target, and ``_say_via_modern`` for the actual
    # render+save pipeline.
    # -------------------------------------------------------------------

    _MODERN_CLASS_CANDIDATES: tuple[tuple[str, str], ...] = (
        ("chatterbox.tts", "ChatterboxTTS"),
        ("chatterbox", "ChatterboxTTS"),
        ("chatterbox.mtl_tts", "ChatterboxMultilingualTTS"),
        ("chatterbox", "ChatterboxMultilingualTTS"),
    )

    def _resolve_modern_tts_cls(self) -> tuple[Any, str] | None:
        """Locate a usable Chatterbox TTS class. Returns ``(cls, label)``
        for the first candidate whose ``from_pretrained`` is callable,
        or ``None`` if none of the modern import shapes resolves."""
        for module_name, class_name in self._MODERN_CLASS_CANDIDATES:
            try:
                mod = __import__(module_name, fromlist=[class_name])
            except ImportError:
                continue
            cls = getattr(mod, class_name, None)
            if cls is None:
                continue
            if not callable(getattr(cls, "from_pretrained", None)):
                continue
            return cls, f"{module_name}.{class_name}"
        return None

    def _detect_device(self) -> str:
        """Resolve the torch device. Honours an explicit ``self.device``
        override; otherwise auto-detects (cuda → mps → cpu)."""
        cleaned = (self.device or "auto").strip().lower()
        if cleaned and cleaned != "auto":
            return cleaned
        try:
            import torch  # type: ignore[import-not-found]
        except ImportError:
            return "cpu"
        try:
            if torch.cuda.is_available():
                return "cuda"
        except Exception:  # noqa: BLE001 — defensive against torch internals
            pass
        backends = getattr(torch, "backends", None)
        mps = getattr(backends, "mps", None) if backends is not None else None
        try:
            if mps is not None and mps.is_available():
                return "mps"
        except Exception:  # noqa: BLE001
            pass
        return "cpu"

    def _resolve_output_path(self, request: TTSRequest) -> str:
        """Pick the target .wav path for the generated waveform.

        Order of precedence: ``self.output_path`` (engine-level config)
        → ``request.metadata['output_path']`` → temp-dir slug derived
        from the first ~30 chars of the request text. The slug fallback
        keeps the same engine usable across many calls without forcing
        the operator to manage paths.
        """
        if self.output_path:
            return self.output_path
        meta_path = (request.metadata or {}).get("output_path", "")
        if meta_path:
            return str(meta_path)
        snippet = (request.text or "")[:30]
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in snippet).strip("-")
        slug = slug or "speech"
        return os.path.join(tempfile.gettempdir(), f"mythic_chatterbox_{slug}.wav")

    def _say_via_modern(
        self, request: TTSRequest, cls: Any, label: str
    ) -> TTSResult:
        """Render ``request.text`` via ``cls.from_pretrained().generate()``
        and save the resulting waveform via torchaudio. Returns
        ``spoken=True`` on a successful end-to-end save, or
        ``spoken=False`` with a clean error message if any stage fails.
        Never raises — TTS failures are reported, not propagated.
        """
        try:
            import torchaudio  # type: ignore[import-not-found]
        except ImportError as exc:
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=(
                    "torchaudio is required to save chatterbox output; "
                    f"install with `pip install torchaudio` ({exc})"
                ),
                metadata={"source": "chatterbox-modern", "engine_class": label},
            )

        device = self._detect_device()
        try:
            model = cls.from_pretrained(device=device)
        except Exception as exc:  # noqa: BLE001 — model load may fail many ways
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=f"{label}.from_pretrained failed: {exc}",
                metadata={
                    "source": "chatterbox-modern",
                    "engine_class": label,
                    "device": device,
                },
            )

        try:
            wav = model.generate(request.text)
        except Exception as exc:  # noqa: BLE001 — generation may fail
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=f"{label}.generate failed: {exc}",
                metadata={
                    "source": "chatterbox-modern",
                    "engine_class": label,
                    "device": device,
                },
            )

        sr = getattr(model, "sr", None)
        if sr is None:
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=f"{label} did not expose `.sr` (sample rate)",
                metadata={
                    "source": "chatterbox-modern",
                    "engine_class": label,
                    "device": device,
                },
            )

        output_path = self._resolve_output_path(request)
        try:
            torchaudio.save(output_path, wav, sr)
        except Exception as exc:  # noqa: BLE001 — save may fail on perms, codec, etc.
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=f"torchaudio.save failed: {exc}",
                metadata={
                    "source": "chatterbox-modern",
                    "engine_class": label,
                    "device": device,
                    "output_path": output_path,
                },
            )

        return TTSResult(
            text=request.text,
            engine=self.name,
            spoken=True,
            metadata={
                "source": "chatterbox-modern",
                "engine_class": label,
                "device": device,
                "output_path": output_path,
                "sample_rate": sr,
            },
        )

    def say(self, request: TTSRequest) -> TTSResult:
        if self._module is None:  # pragma: no cover — __post_init__ guards
            raise MissingExtraError(
                "chatterbox",
                "Install with `pip install chatterbox`.",
            )

        # Additive 2026-05-02: prefer the modern Chatterbox API
        # (ChatterboxTTS / ChatterboxMultilingualTTS) when reachable.
        # The legacy speak()-probe block below remains as a fallback
        # so any future / older / fork variant exposing a top-level
        # speak() still works without code change.
        modern = self._resolve_modern_tts_cls()
        if modern is not None:
            cls, label = modern
            return self._say_via_modern(request, cls, label)

        try:
            # Legacy probe path — preserved verbatim from the pre-2026-05-02
            # implementation. Only fires when no modern Chatterbox class
            # is reachable.
            speak = getattr(self._module, "speak", None)
            if callable(speak):
                speak(request.text, voice=(request.voice or self.voice or None))
                return TTSResult(
                    text=request.text,
                    engine=self.name,
                    spoken=True,
                    metadata={"source": "chatterbox"},
                )
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error="chatterbox.speak not callable in installed version",
            )
        except Exception as exc:  # noqa: BLE001 — never crash callers on TTS errors
            return TTSResult(
                text=request.text,
                engine=self.name,
                spoken=False,
                error=str(exc) or type(exc).__name__,
            )


# ---- Factory + orchestrator -------------------------------------------


def make_tts_engine(name: str) -> TTSEngine:
    cleaned = (name or "").strip().lower()
    if cleaned in {"", "stub"}:
        return StubTTSEngine()
    if cleaned == "chatterbox":
        return ChatterboxEngine()
    raise ValueError(
        f"Unknown TTS engine {name!r}. "
        f"Supported: {', '.join(KNOWN_TTS_ENGINES)}."
    )


def say(
    text: str,
    *,
    engine: str = DEFAULT_TTS_ENGINE,
    voice: str = "",
    force: bool = False,
    tts_engine: TTSEngine | None = None,
) -> TTSResult:
    """Orchestrator. When :func:`is_tts_enabled` is False and
    ``force`` isn't set, returns a non-spoken
    :class:`TTSResult` with a clean ``skipped_reason``. Real
    speech only happens when the env gate is on (or ``force=True``)
    AND the chosen backend successfully emits audio."""
    request = TTSRequest(text=text, engine=engine, voice=voice)

    if not force and not is_tts_enabled():
        return TTSResult(
            text=text,
            engine=engine,
            spoken=False,
            skipped_reason=(
                f"TTS disabled — set {TTS_ENABLED_ENV}=1 to enable, "
                "or pass --force to override for this call"
            ),
        )

    # PH-09 Slice 9.4: per-island gate on chatterbox specifically.
    # Stub engine is unaffected — it stays gated by the broader
    # TTS flag only.
    if (
        not force
        and (engine or "").strip().lower() == "chatterbox"
        and not is_chatterbox_island_enabled()
    ):
        return TTSResult(
            text=text,
            engine=engine,
            spoken=False,
            skipped_reason=(
                f"Chatterbox island disabled — set "
                f"{CHATTERBOX_ISLAND_ENV}=1 to enable (in addition to "
                f"{TTS_ENABLED_ENV}=1), or pass --force to override"
            ),
        )

    if tts_engine is None:
        try:
            tts_engine = make_tts_engine(engine)
        except MissingExtraError as exc:
            return TTSResult(
                text=text,
                engine=engine,
                spoken=False,
                error=str(exc),
                metadata={"missing_extra": exc.extra},
            )
        except ValueError as exc:
            return TTSResult(
                text=text, engine=engine, spoken=False, error=str(exc)
            )
    return tts_engine.say(request)


__all__ = [
    "CHATTERBOX_ISLAND_ENV",
    "DEFAULT_TTS_ENGINE",
    "KNOWN_TTS_ENGINES",
    "TTS_ENABLED_ENV",
    "ChatterboxEngine",
    "StubTTSEngine",
    "TTSEngine",
    "TTSRequest",
    "TTSResult",
    "is_chatterbox_island_enabled",
    "is_tts_enabled",
    "make_tts_engine",
    "say",
]
