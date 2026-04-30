"""Voice & multimodal surfaces (PH-07).

Optional voice-to-intent input (Whisper) and TTS notification
output (Chatterbox), behind feature flags. Strictly local-first;
no cloud speech services in any default path.

The orchestration layer is pure-stdlib. Real audio backends are
gated behind try-import so the CLI surface ships and works without
any heavyweight audio dep installed.
"""

from __future__ import annotations

__all__: list[str] = []
