"""
Context Optimizer (T7 — MEMO)
==============================

Prepends a compact "State of the Game" (SOTG) block to every AI prompt so
the LLM always has the physical scene anchor at the very top of context,
regardless of how much memory, lore, and emotional data follows.

Based on arXiv:2603.09022 — MEMO: Memory-Augmented Model Context Optimization.

Architecture:
  SceneAnchor    — dataclass snapshot of the current physical scene
  ContextOptimizer — builds and prepends the SOTG block each turn

Integration point:
  YggdrasilAIRouter.route_call() calls prepend_sotg() after prompts are
  assembled and before the LLM call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SceneAnchor:
    """Compact physical-scene snapshot injected at prompt top."""

    location_id: str
    location_name: str
    time_of_day: str
    weather: Optional[str]
    npcs_present: List[str]           # display names
    player_name: str
    turn_number: int
    chaos_factor: int
    active_quest_titles: List[str] = field(default_factory=list)
    ambient_notes: Optional[str] = None

    def render(self, max_npcs: int = 6, include_weather: bool = True,
               include_quests: bool = True) -> str:
        npc_names = self.npcs_present[:max_npcs]
        npc_line = ", ".join(npc_names) if npc_names else "none"
        if len(self.npcs_present) > max_npcs:
            npc_line += f" (+{len(self.npcs_present) - max_npcs} more)"

        parts = [
            "=== STATE OF THE GAME ===",
            f"Turn {self.turn_number} | Chaos {self.chaos_factor}/10",
            f"Location: {self.location_name} ({self.location_id})",
            f"Time: {self.time_of_day}",
        ]

        if include_weather and self.weather:
            parts.append(f"Weather: {self.weather}")

        if self.ambient_notes:
            parts.append(f"Ambient: {self.ambient_notes}")

        parts.append(f"Present: {self.player_name} + {npc_line}")

        if include_quests and self.active_quest_titles:
            quests = "; ".join(self.active_quest_titles[:3])
            parts.append(f"Active quests: {quests}")

        parts.append("=== END SOTG ===")
        return "\n".join(parts)


class ContextOptimizer:
    """
    Builds a SceneAnchor each turn and prepends its rendered block to the
    assembled prompt. Safe to call even if game_state is incomplete — all
    field access uses getattr with defaults.

    Never raises — on any exception the original prompt is returned unchanged.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        cfg = (config or {}).get("context_optimizer", {})
        self._enabled = cfg.get("enabled", True)
        self._max_npcs = cfg.get("sotg_max_npcs", 6)
        self._include_weather = cfg.get("sotg_include_weather", True)
        self._include_quests = cfg.get("sotg_include_quests", True)
        self._last_anchor: Optional[SceneAnchor] = None
        # Per-turn SOTG cache: (turn_number, rendered_sotg_block)
        self._sotg_cache: Optional[tuple] = None

    def build_anchor(self, game_state: Any) -> SceneAnchor:
        """
        Construct a SceneAnchor from a GameState (dataclass or dict).
        Accepts both attribute-style (GameState dataclass) and dict access.
        """
        def _get(obj: Any, key: str, default: Any = "") -> Any:
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        # NPC display names
        npcs_raw = _get(game_state, "npcs_present", []) or []
        npc_names: List[str] = []
        for npc in npcs_raw:
            if isinstance(npc, dict):
                name = (
                    npc.get("identity", {}).get("name")
                    or npc.get("name")
                    or npc.get("id", "Unknown")
                )
            else:
                name = str(npc)
            npc_names.append(name)

        # Active quest titles
        quest_titles: List[str] = []
        quest_data = _get(game_state, "quest_data", {}) or {}
        for quest_id, quest in quest_data.items():
            if isinstance(quest, dict) and quest.get("status") == "active":
                quest_titles.append(quest.get("title") or quest_id)
        # Also check active_quests list
        for quest_id in (_get(game_state, "active_quests", []) or []):
            if isinstance(quest_id, str) and quest_id not in quest_titles:
                quest_titles.append(quest_id)

        # Player name
        pc = _get(game_state, "player_character", {}) or {}
        if isinstance(pc, dict):
            player_name = (
                pc.get("identity", {}).get("name")
                or pc.get("name")
                or "Player"
            )
        else:
            player_name = "Player"

        # Location name — try sub-location first for specificity
        location_id = _get(game_state, "current_sub_location_id", "") or \
                      _get(game_state, "current_location_id", "unknown")
        location_name = _get(game_state, "current_location_name", "") or \
                        location_id.replace("_", " ").title()

        anchor = SceneAnchor(
            location_id=str(location_id),
            location_name=str(location_name),
            time_of_day=str(_get(game_state, "time_of_day", "unknown")),
            weather=_get(game_state, "current_weather", None) or None,
            npcs_present=npc_names,
            player_name=player_name,
            turn_number=int(_get(game_state, "turn_count", 0)),
            chaos_factor=int(_get(game_state, "chaos_factor", 5)),
            active_quest_titles=quest_titles,
            ambient_notes=_get(game_state, "ambient_scene_notes", None) or None,
        )
        self._last_anchor = anchor
        return anchor

    def prepend_sotg(self, prompt: str, game_state: Any) -> str:
        """
        Build SceneAnchor and prepend its rendered block to prompt.
        Returns prompt unchanged on any exception.

        The rendered SOTG block is cached for the current turn: multiple
        route_call() invocations within the same turn hit the cache and skip
        the anchor-build + render work entirely.
        """
        if not self._enabled:
            return prompt
        try:
            turn = int(getattr(game_state, "turn_count", None)
                       or (game_state.get("turn_count", 0) if isinstance(game_state, dict) else 0))
            if self._sotg_cache is not None and self._sotg_cache[0] == turn:
                return self._sotg_cache[1] + "\n\n" + prompt
            anchor = self.build_anchor(game_state)
            sotg = anchor.render(
                max_npcs=self._max_npcs,
                include_weather=self._include_weather,
                include_quests=self._include_quests,
            )
            self._sotg_cache = (turn, sotg)
            return sotg + "\n\n" + prompt
        except Exception as exc:
            logger.warning("ContextOptimizer.prepend_sotg failed: %s", exc)
            return prompt

    def get_last_anchor(self) -> Optional[SceneAnchor]:
        return self._last_anchor
