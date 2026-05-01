"""Phase-transition TTS hook (PH-07 follow-up).

Single ``notify_phase(phase, status, *, message=None)`` helper that
speaks a short status line on operator-success events: phase
captures (intent / constraints / architecture / plan / build),
verification runs, and handoff writes.

Default-disabled — relies on the slice 7.3 ``MYTHIC_VOICE_TTS_ENABLED``
env gate. When the gate is off, ``notify_phase`` is a clean no-op:
no audio, no engine construction, no exceptions. When the gate is
on, it dispatches through the same :func:`mythic_vibe_cli.voice.tts.say`
orchestrator the ``voice say`` CLI uses.

Crash-safety: every call is wrapped so a TTS misbehaviour can never
break the parent command. The hook returns the :class:`TTSResult`
for callers that want to surface it (none today; future TUI / JSON
payloads might).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .tts import TTSEngine, TTSResult, is_tts_enabled, say


PHASE_PRESETS: dict[str, dict[str, str]] = {
    "intent": {
        "captured": "Intent captured.",
    },
    "constraints": {
        "captured": "Constraints captured.",
    },
    "architecture": {
        "captured": "Architecture captured.",
    },
    "plan": {
        "captured": "Plan captured.",
    },
    "build": {
        "captured": "Build captured.",
    },
    "verify": {
        "pass": "Verification passed.",
        "fail": "Verification failed.",
        "blocked": "Verification blocked.",
    },
    "handoff": {
        "written": "Handoff written.",
    },
    "checkin": {
        "recorded": "Check-in recorded.",
    },
}


@dataclass(frozen=True)
class NotifyResult:
    """Wrapper distinguishing "TTS skipped because the gate was off"
    from "TTS dispatched but the engine logged only / errored".
    Tests assert on these fields; production callers usually drop
    the result on the floor."""

    fired: bool
    tts_result: TTSResult | None
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "fired": self.fired,
            "message": self.message,
            "tts": self.tts_result.to_dict() if self.tts_result else None,
        }


def compose_phase_message(
    phase: str,
    status: str,
    *,
    override: str | None = None,
) -> str:
    """Pick the short status line for a given (phase, status) pair.
    ``override`` short-circuits the lookup so callers can supply
    custom phrasing."""
    if override is not None:
        cleaned = override.strip()
        if cleaned:
            return cleaned
    presets = PHASE_PRESETS.get(phase, {})
    line = presets.get(status, "")
    if line:
        return line
    # Generic fallback so we always speak *something* recognisable
    # rather than going silent on a new phase / status combination.
    return f"{phase.capitalize()} {status}."


def notify_phase(
    phase: str,
    status: str,
    *,
    message: str | None = None,
    tts_engine: TTSEngine | None = None,
    force: bool = False,
) -> NotifyResult:
    """Speak a short status line for a phase transition.

    No-op when :func:`is_tts_enabled` is False and ``force`` is False
    — returns ``NotifyResult(fired=False, tts_result=None, message=…)``.

    When the gate fires, dispatches through :func:`say` (slice 7.3).
    Any exception inside the TTS layer is contained and surfaced via
    a populated ``tts_result.error``.
    """
    line = compose_phase_message(phase, status, override=message)
    if not force and not is_tts_enabled():
        return NotifyResult(fired=False, tts_result=None, message=line)
    try:
        result = say(line, tts_engine=tts_engine, force=force)
    except Exception as exc:  # noqa: BLE001 — never crash the parent command
        result = TTSResult(
            text=line,
            engine="unknown",
            spoken=False,
            error=str(exc) or type(exc).__name__,
        )
    return NotifyResult(fired=True, tts_result=result, message=line)


__all__ = [
    "NotifyResult",
    "PHASE_PRESETS",
    "compose_phase_message",
    "notify_phase",
]
