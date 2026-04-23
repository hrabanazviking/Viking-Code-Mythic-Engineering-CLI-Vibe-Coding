"""
AI-Enhanced Memory and Turn Summary System
===========================================

Replaces vague memory events like "Mystical event" with accurate,
AI-generated summaries of exactly what happened each turn.

Every turn summary includes:
- WHO: All characters involved
- WHAT: Specific actions taken
- WHEN: Turn number and time of day
- WHERE: Exact location
- WHY: Motivations and context
- HOW: Methods and outcomes

The AI generates these summaries, ensuring accuracy and detail.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# T3-B: lazy imports — only resolved on first use to avoid circular imports
_IdentityDriftChecker = None
_ElasticWindowCalculator = None
_infer_scene_type = None


def _load_hardening():
    global _IdentityDriftChecker, _ElasticWindowCalculator, _infer_scene_type
    if _IdentityDriftChecker is None:
        from systems.memory_hardening import (
            IdentityDriftChecker,
            ElasticWindowCalculator,
            infer_scene_type,
        )
        _IdentityDriftChecker = IdentityDriftChecker
        _ElasticWindowCalculator = ElasticWindowCalculator
        _infer_scene_type = infer_scene_type


# SRD conditions lazy import
_ConditionsSystem = None


def _get_conditions_system():
    global _ConditionsSystem
    if _ConditionsSystem is None:
        try:
            from systems.conditions_system import ConditionsSystem
            _ConditionsSystem = ConditionsSystem()
        except ImportError:
            pass
    return _ConditionsSystem


@dataclass
class TurnSummary:
    """A comprehensive summary of a single turn."""

    turn_number: int
    timestamp: str

    # The 5 W's + H
    who: List[str]  # Characters involved
    what: str  # What happened (main action)
    when: str  # Time of day and context
    where: str  # Location
    why: str  # Motivations/reasons
    how: str  # Methods and outcomes

    # Detailed breakdown
    player_action: str  # What the player did/said
    npc_reactions: List[str]  # How NPCs responded
    narrative_result: str  # The narrative outcome

    # Significance
    importance: int = 5  # 1-10 scale
    event_tags: List[str] = field(
        default_factory=list
    )  # combat, dialogue, discovery, etc.
    emotional_tone: str = "neutral"

    # Consequences
    state_changes: Dict[str, Any] = field(default_factory=dict)
    relationship_changes: List[Dict] = field(default_factory=list)
    items_gained: List[str] = field(default_factory=list)
    items_lost: List[str] = field(default_factory=list)

    # AI-generated prose summary
    prose_summary: str = ""

    def to_dict(self) -> Dict:
        return {
            "turn_number": self.turn_number,
            "timestamp": self.timestamp,
            "who": self.who,
            "what": self.what,
            "when": self.when,
            "where": self.where,
            "why": self.why,
            "how": self.how,
            "player_action": self.player_action,
            "npc_reactions": self.npc_reactions,
            "narrative_result": self.narrative_result,
            "importance": self.importance,
            "event_tags": self.event_tags,
            "emotional_tone": self.emotional_tone,
            "state_changes": self.state_changes,
            "relationship_changes": self.relationship_changes,
            "items_gained": self.items_gained,
            "items_lost": self.items_lost,
            "prose_summary": self.prose_summary,
        }

    def to_memory_text(self) -> str:
        """Convert to text suitable for AI memory context."""
        lines = [
            f"[Turn {self.turn_number}] {self.when} at {self.where}",
            f"  WHO: {', '.join(self.who)}",
            f"  WHAT: {self.what}",
            f"  HOW: {self.how}",
        ]
        if self.prose_summary:
            lines.append(f"  SUMMARY: {self.prose_summary}")
        return "\n".join(lines)


class AITurnSummarizer:
    """
    Uses AI to generate accurate, detailed turn summaries.

    No more vague "Mystical event" or "Quest-related event" summaries.
    Every turn gets a proper, specific summary of what actually happened.
    """

    # Prompt for AI to generate turn summary
    SUMMARY_PROMPT = """Analyze this turn and create a detailed summary.

TURN DATA:
Player Input: {player_input}
Narrative Result: {narrative}
Location: {location}
Time: {time_of_day}
Characters Present: {characters}
Turn Number: {turn_number}

Generate a JSON response with EXACTLY these fields:
{{
    "what": "One sentence describing the main action/event",
    "why": "The motivation or reason for this action",
    "how": "How it was accomplished and the outcome",
    "importance": 1-10 scale of significance,
    "event_tags": ["list", "of", "tags"] (choose from: combat, dialogue,
                   discovery, travel, trade, ritual, romance, conflict,
                   resolution, mystery, death, celebration),
    "emotional_tone": "one word tone" (neutral, tense, joyful, sad, angry,
                       fearful, hopeful, ominous),
    "action_log": "A strictly factual, single-sentence audit log of what "
                  "occurred. NO adjectives, NO flowery language.",
    "prose_summary": "A 1-2 sentence narrative summary of the turn, written in "
                     "saga style (past tense, vivid but concise)."
}}

Be STRICTLY FACTUAL. Do not use vague terms like "mystical event".
You are a data logger, do not write prose."""

    def __init__(
        self, llm_callable: Callable[[str], str] = None, data_path: Path = None
    ):
        self.llm = llm_callable
        self.summaries: Dict[int, TurnSummary] = {}
        self.data_path = data_path or Path("data")
        self.system_prompt = self.SUMMARY_PROMPT
        self._load_prompts()

    def _load_prompts(self):
        try:
            prompt_file = self.data_path / "charts" / "ai_prompts.yaml"
            if prompt_file.exists():
                import yaml

                with open(prompt_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if (
                        data
                        and "memory_summarizer" in data
                        and "instructions" in data["memory_summarizer"]
                    ):
                        self.system_prompt = data["memory_summarizer"][
                            "instructions"
                        ].strip()
                        logger.info(
                            "Loaded memory_summarizer prompt from ai_prompts.yaml"
                        )
        except Exception as e:
            logger.warning(f"Could not load memory summarizer prompt from config: {e}")

    def summarize_turn(
        self,
        turn_number: int,
        player_input: str,
        narrative: str,
        location: str,
        time_of_day: str,
        characters_present: List[str],
        state_changes: Dict[str, Any] = None,
        character_data: Dict[str, Dict] = None,
    ) -> TurnSummary:
        """
        Generate a comprehensive turn summary using AI.
        """
        # Start with basic data
        summary = TurnSummary(
            turn_number=turn_number,
            timestamp=datetime.now().isoformat(),
            who=characters_present,
            what="",
            when=f"Turn {turn_number}, {time_of_day}",
            where=location,
            why="",
            how="",
            player_action=player_input,
            npc_reactions=[],
            narrative_result=narrative,
            state_changes=state_changes or {},
        )

        # Use AI to generate detailed summary
        if self.llm:
            try:
                prompt = self.system_prompt.format(
                    player_input=player_input[:500],
                    narrative=narrative[:1000],
                    location=location,
                    time_of_day=time_of_day,
                    characters=", ".join(characters_present[:10]),
                    turn_number=turn_number,
                )

                response = self.llm(prompt)

                # Parse JSON from response
                ai_summary = self._parse_ai_response(response)

                if ai_summary:
                    summary.what = ai_summary.get("what", summary.what)
                    summary.why = ai_summary.get("why", "")
                    summary.how = ai_summary.get("how", "")
                    summary.importance = ai_summary.get("importance", 5)
                    summary.event_tags = ai_summary.get("event_tags", [])
                    summary.emotional_tone = ai_summary.get("emotional_tone", "neutral")
                    summary.prose_summary = ai_summary.get("prose_summary", "")

                    logger.info(f"[TURN {turn_number}] AI Summary: {summary.what}")

            except Exception as e:
                logger.error(f"AI summarization failed: {e}")
                # Fall back to basic extraction
                summary = self._basic_summary(summary, player_input, narrative)
        else:
            # No AI available, use basic extraction
            summary = self._basic_summary(summary, player_input, narrative)

        # Store for later reference
        self.summaries[turn_number] = summary

        return summary

    def _parse_ai_response(self, response: str) -> Optional[Dict]:
        """Parse JSON from AI response."""
        try:
            # Find JSON in response
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        return None

    def _basic_summary(
        self, summary: TurnSummary, player_input: str, narrative: str
    ) -> TurnSummary:
        """Generate basic summary without AI."""
        # Detect action type from keywords
        action_lower = player_input.lower()

        if any(w in action_lower for w in ["attack", "fight", "strike", "kill"]):
            summary.what = f"Combat action: {player_input[:100]}"
            summary.event_tags = ["combat"]
            summary.emotional_tone = "tense"
        elif any(w in action_lower for w in ["talk", "speak", "ask", "say", "tell"]):
            summary.what = f"Dialogue: {player_input[:100]}"
            summary.event_tags = ["dialogue"]
        elif any(
            w in action_lower for w in ["look", "examine", "search", "investigate"]
        ):
            summary.what = f"Investigation: {player_input[:100]}"
            summary.event_tags = ["discovery"]
        elif any(w in action_lower for w in ["go", "walk", "travel", "move", "enter"]):
            summary.what = f"Movement: {player_input[:100]}"
            summary.event_tags = ["travel"]
        else:
            summary.what = f"Action: {player_input[:100]}"

        # Create basic prose summary
        summary.prose_summary = f"The player {player_input[:50]}. {narrative[:100]}..."

        return summary

    def get_recent_summaries(self, count: int = 5) -> List[TurnSummary]:
        """Get the most recent turn summaries."""
        turn_numbers = sorted(self.summaries.keys(), reverse=True)[:count]
        return [self.summaries[t] for t in turn_numbers]

    def get_summaries_for_ai(self, count: int = 10) -> str:
        """Get formatted summaries for AI context."""
        recent = self.get_recent_summaries(count)

        if not recent:
            return "[No previous turns recorded]"

        lines = ["=== RECENT EVENTS ==="]
        for summary in reversed(recent):  # Chronological order
            lines.append(summary.to_memory_text())
            lines.append("")

        return "\n".join(lines)

    def get_summary_by_tag(self, tag: str) -> List[TurnSummary]:
        """Get all summaries with a specific tag."""
        return [s for s in self.summaries.values() if tag in s.event_tags]


class EnhancedMemoryManager:
    """
    Enhanced memory manager that uses AI for accurate event tracking.

    Replaces the old vague event system with proper turn summaries.
    """

    def __init__(
        self, llm_callable: Callable[[str], str] = None, data_path: str = None
    ):
        self.llm = llm_callable
        self.data_path = Path(data_path) if data_path else Path("data")

        self.summarizer = AITurnSummarizer(llm_callable, self.data_path)

        # Memory categories
        self.character_memories: Dict[str, List[Dict]] = {}
        self.location_memories: Dict[str, List[Dict]] = {}
        self.relationship_memories: Dict[str, Dict[str, List[Dict]]] = {}

        # Session tracking
        self.session_id: Optional[str] = None
        self.player_character_id: Optional[str] = None
        self.short_term_limit = 25
        self.medium_term_limit = 120
        self.event_signal_limit = 220
        self.event_signals: List[Dict[str, Any]] = []

        # Medium-term context cache — rebuilt only when memories change.
        # Key: (max_items,) — invalidated by any add_character_memory / add_location_memory call.
        self._medium_term_cache: Optional[str] = None
        self._medium_term_cache_key: Optional[int] = None  # max_items used for cached build

        logger.info("Enhanced Memory Manager initialized")

    def start_session(
        self, session_id: str, player_character: Dict, starting_location: str
    ):
        """Start a new memory session."""
        self.session_id = session_id
        self.player_character_id = player_character.get("id", "player")

        # Initialize player character memories
        pc_name = player_character.get("identity", {}).get("name", "Unknown")
        self.add_character_memory(
            self.player_character_id,
            "session_start",
            f"{pc_name} began their journey at {starting_location}",
            importance=7,
        )

    def process_turn(
        self,
        turn_number: int,
        player_input: str,
        narrative: str,
        game_state: Dict[str, Any],
    ) -> TurnSummary:
        """
        Process a complete turn and generate memories.

        This is the main entry point for turn processing.
        """
        location = game_state.get("current_location_id", "unknown")
        time_of_day = game_state.get("time_of_day", "day")

        # Get characters present
        characters = []
        for npc in game_state.get("npcs_present", []):
            name = npc.get("identity", {}).get("name", npc.get("id", "unknown"))
            characters.append(name)

        # Add player character
        pc = game_state.get("player_character", {})
        pc_name = pc.get("identity", {}).get("name", "Player")
        characters.insert(0, pc_name)

        # Get character data for context
        character_data = {}
        for npc in game_state.get("npcs_present", []):
            npc_id = npc.get("id", "")
            if npc_id:
                character_data[npc_id] = npc

        # Generate AI summary
        summary = self.summarizer.summarize_turn(
            turn_number=turn_number,
            player_input=player_input,
            narrative=narrative,
            location=location,
            time_of_day=time_of_day,
            characters_present=characters,
            character_data=character_data,
        )

        # Create memories from summary
        self._create_memories_from_summary(summary)
        self._compact_memory_tiers()

        # Huginn scouts concrete event fragments so prompts stay anchored.
        signals = self.collect_event_signals(
            turn_number=turn_number,
            player_input=player_input,
            narrative=narrative,
            game_state=game_state,
            summary=summary,
        )
        if signals:
            self.event_signals.extend(signals)
            self.event_signals = self.event_signals[-self.event_signal_limit :]

        return summary

    def _compact_memory_tiers(self) -> None:
        """Keep short-term hot and medium-term deep without overflowing prompt budgets."""
        try:
            for char_id, memories in list(self.character_memories.items()):
                memories.sort(
                    key=lambda m: (int(m.get("importance", 0)) if str(m.get("importance", 0)).isdigit() else 0, m.get("timestamp", "")),
                    reverse=True,
                )
                self.character_memories[char_id] = memories[: self.medium_term_limit]

            for location_id, memories in list(self.location_memories.items()):
                memories.sort(
                    key=lambda m: (int(m.get("importance", 0)) if str(m.get("importance", 0)).isdigit() else 0, m.get("timestamp", "")),
                    reverse=True,
                )
                self.location_memories[location_id] = memories[: self.medium_term_limit]
        except Exception:
            logger.warning("Enhanced memory compaction skipped.", exc_info=True)

    def collect_event_signals(
        self,
        turn_number: int,
        player_input: str,
        narrative: str,
        game_state: Dict[str, Any],
        summary: Optional[TurnSummary] = None,
    ) -> List[Dict[str, Any]]:
        """Extract compact event signals for short/medium-term prompt reinforcement."""
        try:
            text = f"{player_input} {narrative}".lower()
            cues = {
                "oath": ["oath", "swear", "vow", "pledge"],
                "betrayal": ["betray", "treach", "deceive"],
                "combat": ["strike", "attack", "battle", "wound", "blood"],
                "travel": ["travel", "ride", "journey", "sail"],
                "trade": ["trade", "coin", "silver", "buy", "sell"],
                "revelation": ["learn", "reveal", "secret", "truth", "discover"],
                "romance": ["kiss", "embrace", "desire", "romance"],
                "ritual": ["rune", "ritual", "blot", "omen", "seidr"],
            }
            tags: List[str] = []
            for tag, needles in cues.items():
                if any(needle in text for needle in needles):
                    tags.append(tag)

            if summary and summary.event_tags:
                tags.extend(
                    [str(tag) for tag in summary.event_tags if isinstance(tag, str)]
                )

            # Add condition-derived tags from player character state
            try:
                pc = game_state.get("player_character") or {}
                if isinstance(pc, dict):
                    pc_dnd5e = pc.get("dnd5e", {}) if isinstance(pc.get("dnd5e"), dict) else {}
                    pc_status = pc.get("status", {}) if isinstance(pc.get("status"), dict) else {}
                    pc_conds = pc_status.get("conditions") or pc_dnd5e.get("conditions") or []
                    if isinstance(pc_conds, str):
                        pc_conds = [pc_conds]
                    cs = _get_conditions_system()
                    if cs is not None and pc_conds:
                        normalized = cs.normalize_conditions(pc_conds)
                        if normalized:
                            tags.append("condition_event")
                        severe = {"unconscious", "paralyzed", "petrified", "dying"}
                        if any(c in severe for c in normalized):
                            tags.append("near_death")
                        if "frightened" in normalized or "charmed" in normalized:
                            tags.append("emotional_event")
                        exhaustion = int(pc_dnd5e.get("exhaustion", 0) or 0)
                        if exhaustion >= 3:
                            tags.append("exhaustion_critical")
            except Exception as _exc:
                logger.debug("collect_event_signals condition detection failed: %s", _exc)

            tags = sorted(set(tags))[:8]
            if not tags:
                return []

            location = str(
                game_state.get("current_sub_location_id")
                or game_state.get("current_location_id")
                or "unknown"
            )
            npc_names: List[str] = []
            for npc in game_state.get("npcs_present", [])[:6]:
                if not isinstance(npc, dict):
                    continue
                identity = (
                    npc.get("identity", {})
                    if isinstance(npc.get("identity", {}), dict)
                    else {}
                )
                npc_names.append(
                    str(identity.get("name") or npc.get("id") or "unknown")
                )

            return [
                {
                    "turn": int(turn_number or 0),
                    "tags": tags,
                    "location": location,
                    "npcs": npc_names,
                    "signal": (summary.what if summary else player_input)[:220],
                    "tone": (summary.emotional_tone if summary else "neutral"),
                }
            ]
        except Exception:
            logger.warning("Event signal extraction failed.", exc_info=True)
            return []

    def get_event_signal_context(self, max_items: int = 20) -> str:
        """Render harvested event signals so the AI keeps the present conflict in focus."""
        try:
            if not self.event_signals:
                return ""
            lines = ["=== TURN EVENT SIGNALS (IMMEDIATE PRESSURE) ==="]
            for item in self.event_signals[-max(1, int(max_items)) :]:
                lines.append(
                    f"- T{item.get('turn', 0)} @ {item.get('location', 'unknown')}: "
                    f"{item.get('signal', '')} | tags={', '.join(item.get('tags', [])[:6])} | tone={item.get('tone', 'neutral')}"
                )
            lines.append(
                "Anchor narration to these signals before introducing new tangents."
            )
            return "\n".join(lines)
        except Exception:
            logger.warning("Event signal context build failed.", exc_info=True)
            return ""

    def _create_memories_from_summary(self, summary: TurnSummary):
        """Create persistent memories from a turn summary."""
        # Add to location memory
        self.add_location_memory(
            summary.where,
            summary.what,
            summary.prose_summary,
            importance=summary.importance,
        )

        # Add to character memories for each involved character
        for character in summary.who:
            self.add_character_memory(
                character,
                summary.what,
                summary.prose_summary,
                importance=summary.importance,
            )

        # Process relationship changes
        for change in summary.relationship_changes:
            self.add_relationship_memory(
                change.get("character1", ""),
                change.get("character2", ""),
                change.get("change_type", "interaction"),
                change.get("description", ""),
            )

    def add_character_memory(
        self, character_id: str, event_type: str, description: str, importance: int = 5
    ):
        """Add a memory related to a character."""
        self._medium_term_cache = None  # invalidate cached context string
        if character_id not in self.character_memories:
            self.character_memories[character_id] = []

        self.character_memories[character_id].append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "description": description,
                "importance": importance,
            }
        )

        # Keep only most recent/important memories
        if len(self.character_memories[character_id]) > 50:
            # Sort by importance and recency
            self.character_memories[character_id].sort(
                key=lambda m: (m["importance"], m["timestamp"]), reverse=True
            )
            self.character_memories[character_id] = self.character_memories[
                character_id
            ][:50]

    def add_condition_event_memory(
        self,
        character_id: str,
        conditions: List[str],
        turn: int,
        location_id: str = "",
        exhaustion_level: int = 0,
    ) -> None:
        """Store a memory node for an SRD condition event affecting a character.

        Tags the memory with 'condition_event' and the individual condition names
        so Huginn/Muninn can retrieve condition history during scene analysis.
        """
        try:
            cs = _get_conditions_system()
            normalized: List[str] = []
            if cs is not None and conditions:
                normalized = cs.normalize_conditions(conditions)
            else:
                normalized = [str(c).lower().strip() for c in (conditions or [])]

            if not normalized and not exhaustion_level:
                return

            cond_str = ", ".join(normalized) if normalized else "none"
            exh_str = f" (exhaustion {exhaustion_level})" if exhaustion_level else ""
            description = (
                f"Turn {turn}: {character_id} affected by {cond_str}{exh_str}. "
                f"SRD mechanical effects active."
            )
            severe = {"unconscious", "paralyzed", "petrified", "dying"}
            importance = 8 if any(c in severe for c in normalized) else 5

            self.add_character_memory(
                character_id=character_id,
                event_type="condition_event",
                description=description,
                importance=importance,
            )
            if location_id:
                self.add_location_memory(
                    location_id=location_id,
                    event_type="condition_event",
                    description=description,
                    importance=importance,
                )
        except Exception as exc:
            logger.warning("add_condition_event_memory failed: %s", exc)

    def add_location_memory(
        self, location_id: str, event_type: str, description: str, importance: int = 5
    ):
        """Add a memory related to a location."""
        self._medium_term_cache = None  # invalidate cached context string
        if location_id not in self.location_memories:
            self.location_memories[location_id] = []

        self.location_memories[location_id].append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": event_type,
                "description": description,
                "importance": importance,
            }
        )

    def add_relationship_memory(
        self, character1: str, character2: str, change_type: str, description: str
    ):
        """Add a memory about relationship between characters."""
        if character1 not in self.relationship_memories:
            self.relationship_memories[character1] = {}
        if character2 not in self.relationship_memories[character1]:
            self.relationship_memories[character1][character2] = []

        self.relationship_memories[character1][character2].append(
            {
                "timestamp": datetime.now().isoformat(),
                "type": change_type,
                "description": description,
            }
        )

    def get_character_context(self, character_id: str, max_memories: int = 10) -> str:
        """Get memory context for a character."""
        memories = self.character_memories.get(character_id, [])

        if not memories:
            return f"[No recorded memories about {character_id}]"

        # Get most important recent memories
        recent = sorted(
            memories, key=lambda m: (m["importance"], m["timestamp"]), reverse=True
        )[:max_memories]

        lines = [f"=== MEMORIES: {character_id} ==="]
        for mem in recent:
            lines.append(f"  • {mem['description'][:200]}")

        return "\n".join(lines)

    # ── T3-B: Identity Drift helpers ──────────────────────────────────────────

    def get_recent_events_for_character(
        self, character_id: str, count: int = 30
    ) -> List[Dict]:
        """Return the last *count* character memory events, newest first."""
        events = self.character_memories.get(character_id, [])
        return list(reversed(events[-count:]))

    def check_identity_drift(
        self,
        character_id: str,
        current_turn: int,
        base_traits: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Called from the engine turn loop to detect identity drift.

        Returns a DriftVector if significant drift is found, else None.
        Lazily initialises IdentityDriftChecker on first call.
        """
        _load_hardening()
        if not hasattr(self, "_drift_checker"):
            self._drift_checker = _IdentityDriftChecker(self, config=config)
        return self._drift_checker.evaluate_character(
            character_id, current_turn, base_traits
        )

    def get_drift_history(self, character_id: str) -> List:
        """Return all recorded DriftVectors for character_id (may be empty)."""
        if hasattr(self, "_drift_checker"):
            return self._drift_checker.get_drift_history(character_id)
        return []

    # ── T3-B: Elastic memory window helper ───────────────────────────────────

    def _elastic_window(
        self,
        game_state: Optional[Dict[str, Any]],
        caller_max: int,
        scene_type: Optional[str] = None,
    ) -> int:
        """
        Compute an elastic retrieval window size and return the larger of that
        and the caller-specified max (so callers can always request more).
        """
        _load_hardening()
        if not hasattr(self, "_elastic_calc"):
            self._elastic_calc = _ElasticWindowCalculator()

        if game_state is None:
            return caller_max

        if scene_type is None:
            last_summary = (
                self.summarizer.get_recent_summaries(1) if self.summarizer else []
            )
            last_text = getattr(last_summary[0], "narrative_result", None) or getattr(last_summary[0], "narrative", "") if last_summary else ""
            scene_type = _infer_scene_type(last_text)

        chaos = int(game_state.get("chaos_factor", 5))
        emotion_intensity = float(game_state.get("dominant_emotion_intensity", 0.0))
        dynamic = self._elastic_calc.compute(
            chaos_factor=chaos,
            dominant_emotion_intensity=emotion_intensity,
            scene_type=scene_type,
        )
        return max(caller_max, dynamic)

    def get_location_context(self, location_id: str, max_memories: int = 10) -> str:
        """Get memory context for a location."""
        memories = self.location_memories.get(location_id, [])

        if not memories:
            return f"[No recorded memories at {location_id}]"

        recent = sorted(memories, key=lambda m: m["timestamp"], reverse=True)[
            :max_memories
        ]

        lines = [f"=== EVENTS AT {location_id} ==="]
        for mem in recent:
            lines.append(f"  • {mem['description'][:200]}")

        return "\n".join(lines)

    def get_full_context_for_ai(
        self,
        game_state: Dict,
        max_items: int = 15,
        scene_type: Optional[str] = None,
    ) -> str:
        """Get complete memory context for AI processing."""
        # T3-B: expand window based on scene intensity
        effective_max = self._elastic_window(game_state, max_items, scene_type)

        lines = []

        # Recent turn summaries
        lines.append(self.summarizer.get_summaries_for_ai(effective_max))
        lines.append("")

        # Current location memories
        location = game_state.get("current_location_id", "")
        if location:
            lines.append(self.get_location_context(location, 5))
            lines.append("")

        # Player character memories
        if self.player_character_id:
            lines.append(self.get_character_context(self.player_character_id, 5))

        short_term = self.get_short_term_context_for_ai(max_items=min(12, effective_max))
        if short_term:
            lines.extend(["", short_term])

        medium_term = self.get_medium_term_context_for_ai(
            max_items=min(18, effective_max + 3)
        )
        if medium_term:
            lines.extend(["", medium_term])

        event_signal_context = self.get_event_signal_context(
            max_items=min(20, effective_max + 8)
        )
        if event_signal_context:
            lines.extend(["", event_signal_context])

        return "\n".join(lines)

    def get_short_term_context_for_ai(self, max_items: int = 12) -> str:
        """High-priority events from the most recent turns."""
        try:
            recent = self.summarizer.get_recent_summaries(max_items)
            if not recent:
                return ""

            lines = ["=== SHORT-TERM MEMORY (IMMEDIATE CONTINUITY) ==="]
            for summary in recent:
                lines.append(
                    f"- T{summary.turn_number} at {summary.where}: {summary.what} "
                    f"[tone={summary.emotional_tone}, importance={summary.importance}]"
                )
                if summary.prose_summary:
                    lines.append(f"  consequence: {summary.prose_summary[:220]}")
            lines.append(
                "Use these as hard continuity anchors for the current scene and unresolved stakes. Resolve or escalate these before introducing unrelated developments."
            )
            return "\n".join(lines)
        except Exception:
            logger.warning("Short-term memory context build failed.", exc_info=True)
            return ""

    def get_medium_term_context_for_ai(self, max_items: int = 18) -> str:
        """Broader memory arcs (relationships, places, repeating consequences)."""
        if self._medium_term_cache is not None and self._medium_term_cache_key == max_items:
            return self._medium_term_cache
        try:
            combined: List[Dict[str, Any]] = []
            for char_id, memories in self.character_memories.items():
                for memory in memories[:8]:
                    combined.append({"scope": f"character:{char_id}", **memory})
            for loc_id, memories in self.location_memories.items():
                for memory in memories[:6]:
                    combined.append({"scope": f"location:{loc_id}", **memory})

            combined.sort(
                key=lambda m: (int(m.get("importance", 0)) if str(m.get("importance", 0)).isdigit() else 0, m.get("timestamp", "")),
                reverse=True,
            )
            combined = combined[:max_items]
            if not combined:
                return ""

            lines = ["=== MEDIUM-TERM MEMORY (SAGA TRAJECTORY) ==="]
            for item in combined:
                lines.append(
                    f"- {item.get('scope', 'unknown')} :: {item.get('type', 'event')} :: "
                    f"{str(item.get('description', ''))[:220]}"
                )
            lines.append(
                "Preserve these arcs so the story remains coherent across many turns."
            )
            result = "\n".join(lines)
            self._medium_term_cache = result
            self._medium_term_cache_key = max_items
            return result
        except Exception:
            logger.warning("Medium-term memory context build failed.", exc_info=True)
            return ""


# Factory function
def create_enhanced_memory_manager(
    llm_callable: Callable[[str], str] = None, data_path: str = None
) -> EnhancedMemoryManager:
    """Create an enhanced memory manager."""
    return EnhancedMemoryManager(llm_callable, data_path)
