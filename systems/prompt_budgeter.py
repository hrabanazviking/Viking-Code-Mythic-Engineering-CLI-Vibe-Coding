"""Prompt budget allocation utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)

_TIKTOKEN_ENCODER = None
_TIKTOKEN_AVAILABLE = None


def _ensure_tiktoken_encoder() -> None:
    """Initialize encoder once, but never fail on environment/network issues."""
    global _TIKTOKEN_AVAILABLE, _TIKTOKEN_ENCODER
    if _TIKTOKEN_AVAILABLE is not None:
        return

    try:
        import tiktoken

        _TIKTOKEN_ENCODER = tiktoken.get_encoding("cl100k_base")
        _TIKTOKEN_AVAILABLE = True
        logger.info(
            "prompt_budgeter: tiktoken available — using exact token counts "
            "(cl100k_base encoding)."
        )
    except ImportError:
        _TIKTOKEN_AVAILABLE = False
        logger.info(
            "prompt_budgeter: tiktoken not installed — falling back to "
            "character-count approximation (~4 chars/token). "
            "Install with: pip install tiktoken"
        )
    except Exception as exc:
        _TIKTOKEN_AVAILABLE = False
        logger.warning(
            "prompt_budgeter: tiktoken unavailable due to runtime error (%s); "
            "using character-count fallback.",
            exc,
        )


def count_tokens(text: str) -> int:
    """Return the token count for *text*.

    Uses tiktoken (cl100k_base) when available; falls back to the
    GPT-family approximation of ~4 characters per token.
    """
    _ensure_tiktoken_encoder()
    if _TIKTOKEN_AVAILABLE:
        return len(_TIKTOKEN_ENCODER.encode(text))
    # Fallback: ~4 chars per token (GPT-family approximation)
    return max(1, len(text) // 4)


class PromptBudgeter:
    """Allocates and enforces segment-level prompt budgets."""

    def __init__(self, data_path: str = "data", profile: str = "balanced") -> None:
        self.data_path = Path(data_path)
        self.profile_name = profile
        self.budgets = self._load_yaml("charts/prompt_budget_profiles.yaml", {})
        self.priority_weights = self._load_yaml("charts/context_priority_weights.yaml", {})

    def memory_char_budget(self) -> int:
        profiles = self.budgets.get("profiles", {}) if isinstance(self.budgets, dict) else {}
        profile = profiles.get(self.profile_name, profiles.get("balanced", {})) if isinstance(profiles, dict) else {}
        cap = int(profile.get("total_token_cap", 8000))
        memory_ratio = float(profile.get("high_salience_memory", 0.30))
        return int(cap * memory_ratio)

    def trim_memory_context(self, memory_context: str) -> str:
        """Muninn keeps only memory lines that fit budget."""
        text = (memory_context or "").strip()
        if not text:
            return text
        _ensure_tiktoken_encoder()
        budget = self.memory_char_budget()
        if count_tokens(text) <= budget:
            return text
        # Text exceeds token budget — truncate
        if _TIKTOKEN_AVAILABLE:
            tokens = _TIKTOKEN_ENCODER.encode(text)
            # Leave 1 token headroom for the "..." ellipsis
            truncated = _TIKTOKEN_ENCODER.decode(tokens[: max(1, budget - 1)])
            return truncated + "..."
        else:
            # Fallback: ~4 chars per token approximation
            char_limit = max(0, budget * 4 - 3)
            return text[:char_limit] + "..."

    def _load_yaml(self, relative_path: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
        path = self.data_path / relative_path
        if not path.exists():
            return fallback
        with path.open("r", encoding="utf-8") as handle:
            loaded = yaml.safe_load(handle) or fallback
        return loaded if isinstance(loaded, dict) else fallback
