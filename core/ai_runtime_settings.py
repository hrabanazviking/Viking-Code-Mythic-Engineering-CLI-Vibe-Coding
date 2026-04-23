"""Resilient AI runtime settings normalization.

This module guards all user-facing AI controls from malformed config values
and keeps defaults stable when config entries are missing.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, Tuple

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AIRuntimeSettings:
    """Normalized controls for AI sampling and behavior directives."""

    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    content_mode: str = "nsfw"
    language: str = "English"

    @staticmethod
    def _coerce_float(
        value: Any,
        default: float,
        min_value: float,
        max_value: float,
        setting_name: str,
    ) -> float:
        """Mimir tempers numeric chaos into bounded fate."""
        try:
            casted = float(value)
            if casted < min_value or casted > max_value:
                raise ValueError(f"out of range [{min_value}, {max_value}]")
            return casted
        except Exception as exc:
            logger.warning(
                "Invalid config for %s (%r): %s. Falling back to %s.",
                setting_name,
                value,
                exc,
                default,
            )
            return default

    @staticmethod
    def _coerce_int(
        value: Any,
        default: int,
        min_value: int,
        max_value: int,
        setting_name: str,
    ) -> int:
        """Thor's hammer enforces integer bounds for sampling controls."""
        try:
            casted = int(value)
            if casted < min_value or casted > max_value:
                raise ValueError(f"out of range [{min_value}, {max_value}]")
            return casted
        except Exception as exc:
            logger.warning(
                "Invalid config for %s (%r): %s. Falling back to %s.",
                setting_name,
                value,
                exc,
                default,
            )
            return default

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "AIRuntimeSettings":
        """Hydrate normalized settings from config with strict fallback logic."""
        openrouter_cfg = config.get("openrouter", {})
        if not isinstance(openrouter_cfg, dict):
            logger.warning("Config openrouter section is not a mapping; repairing.")
            openrouter_cfg = {}

        ai_behavior_cfg = config.get("ai_behavior", {})
        if not isinstance(ai_behavior_cfg, dict):
            logger.warning("Config ai_behavior section is not a mapping; repairing.")
            ai_behavior_cfg = {}

        raw_mode = str(ai_behavior_cfg.get("content_mode", "nsfw") or "nsfw").strip().lower()
        if raw_mode not in {"nsfw", "sfw"}:
            logger.warning("Invalid ai_behavior.content_mode=%r. Using nsfw.", raw_mode)
            raw_mode = "nsfw"

        raw_language = str(ai_behavior_cfg.get("language", "English") or "English").strip()
        if not raw_language:
            raw_language = "English"

        return cls(
            top_p=cls._coerce_float(
                openrouter_cfg.get("top_p", 1.0),
                default=1.0,
                min_value=0.0,
                max_value=1.0,
                setting_name="openrouter.top_p",
            ),
            top_k=cls._coerce_int(
                openrouter_cfg.get("top_k", 0),
                default=0,
                min_value=0,
                max_value=200,
                setting_name="openrouter.top_k",
            ),
            presence_penalty=cls._coerce_float(
                openrouter_cfg.get("presence_penalty", 0.0),
                default=0.0,
                min_value=-2.0,
                max_value=2.0,
                setting_name="openrouter.presence_penalty",
            ),
            frequency_penalty=cls._coerce_float(
                openrouter_cfg.get("frequency_penalty", 0.0),
                default=0.0,
                min_value=-2.0,
                max_value=2.0,
                setting_name="openrouter.frequency_penalty",
            ),
            content_mode=raw_mode,
            language=raw_language,
        )

    def apply_to_config(self, config: Dict[str, Any]) -> None:
        """Write repaired values back into config for downstream consistency."""
        openrouter_cfg = config.setdefault("openrouter", {})
        if not isinstance(openrouter_cfg, dict):
            config["openrouter"] = {}
            openrouter_cfg = config["openrouter"]

        ai_behavior_cfg = config.setdefault("ai_behavior", {})
        if not isinstance(ai_behavior_cfg, dict):
            config["ai_behavior"] = {}
            ai_behavior_cfg = config["ai_behavior"]

        openrouter_cfg["top_p"] = self.top_p
        openrouter_cfg["top_k"] = self.top_k
        openrouter_cfg["presence_penalty"] = self.presence_penalty
        openrouter_cfg["frequency_penalty"] = self.frequency_penalty
        ai_behavior_cfg["content_mode"] = self.content_mode
        ai_behavior_cfg["language"] = self.language

    def prompt_directives(self) -> Tuple[str, ...]:
        """Return runtime prompt directives for style/safety/language control."""
        directives = [
            (
                f"Primary response language: {self.language}. Keep narration and dialogue "
                f"in that language unless context requires otherwise."
            ),
            "Regardless of language, occasionally include a short Old Norse phrase in character dialogue.",
        ]
        if self.content_mode == "sfw":
            directives.append(
                "SFW mode is active: avoid explicit sexual content, explicit nudity, and graphic erotic description."
            )
        return tuple(directives)

