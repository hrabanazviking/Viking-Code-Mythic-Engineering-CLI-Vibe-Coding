"""
Wyrd System - The Flow of Fate Through the Three Sacred Wells
=============================================================

In Norse cosmology, the Norns weave the threads of fate at the base of
Yggdrasil, where three sacred wells connect all things:

1. Urðarbrunnr (Well of Urd/Wyrd) - The Past
   - What has been, cannot be undone
   - Records all events, actions, choices
   - The foundation upon which fate is built

2. Mímisbrunnr (Mímir's Well) - The Present/Wisdom
   - Current state and knowledge
   - Active decisions and their weights
   - The place of seeing clearly

3. Hvergelmir (The Roaring Cauldron) - The Future/Potential
   - What might be, the threads not yet woven
   - Probability and possibility
   - Where chaos and order meet

All game events flow through these wells:
- Past actions are recorded in Urðarbrunnr
- Current state is reflected in Mímisbrunnr
- Future possibilities are calculated in Hvergelmir

The Norns (Urd, Verdandi, Skuld) process events and influence outcomes.
"""

import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from enum import Enum
import random

logger = logging.getLogger(__name__)


class WyrdType(Enum):
    """Types of wyrd (fate) threads."""

    ACTION = "action"  # Something done
    CHOICE = "choice"  # A decision made
    CONSEQUENCE = "consequence"  # Result of action/choice
    ENCOUNTER = "encounter"  # Meeting someone/something
    REVELATION = "revelation"  # Learning something
    OATH = "oath"  # A promise made (very significant)
    BETRAYAL = "betrayal"  # Breaking an oath (severe)
    DEATH = "death"  # Death of a character
    BIRTH = "birth"  # New character/entity
    BLESSING = "blessing"  # Divine favor
    CURSE = "curse"  # Divine disfavor


class NornDomain(Enum):
    """The three Norns and their domains."""

    URD = "urd"  # Past - What has been
    VERDANDI = "verdandi"  # Present - What is becoming
    SKULD = "skuld"  # Future - What shall be


@dataclass
class WyrdThread:
    """A single thread of fate/wyrd."""

    id: str
    thread_type: WyrdType
    content: str
    characters_involved: List[str]
    location: str
    turn_number: int
    timestamp: str

    # Weights and significance
    importance: int = 5  # 1-10 scale
    karma_shift: int = 0  # -10 to +10 (honor/dishonor)
    chaos_impact: int = 0  # Effect on chaos factor

    # Connected threads
    caused_by: Optional[str] = None  # ID of thread that led to this
    leads_to: List[str] = field(default_factory=list)  # IDs of resulting threads

    # Norn processing
    processed_by: Optional[NornDomain] = None
    norn_commentary: str = ""

    def to_dict(self) -> Dict:
        return {
            **asdict(self),
            "thread_type": self.thread_type.value,
            "processed_by": self.processed_by.value if self.processed_by else None,
        }


@dataclass
class WellState:
    """State of a sacred well."""

    name: str
    domain: NornDomain
    threads: List[str] = field(default_factory=list)  # Thread IDs
    total_karma: int = 0
    significant_events: List[str] = field(default_factory=list)
    last_updated: str = ""


class UrdWell:
    """
    Urðarbrunnr - The Well of the Past

    Records everything that has happened.
    Cannot be changed, only added to.
    Forms the foundation of fate.
    """

    def __init__(self):
        self.state = WellState(
            name="Urðarbrunnr",
            domain=NornDomain.URD,
            last_updated=datetime.now().isoformat(),
        )
        self.threads: Dict[str, WyrdThread] = {}

    def record(self, thread: WyrdThread) -> str:
        """Record a thread of fate in the well of the past."""
        thread.processed_by = NornDomain.URD
        thread.norn_commentary = self._urd_commentary(thread)

        self.threads[thread.id] = thread
        self.state.threads.append(thread.id)
        self.state.total_karma += thread.karma_shift
        self.state.last_updated = datetime.now().isoformat()

        if thread.importance >= 7:
            self.state.significant_events.append(thread.id)

        logger.info(
            f"[URD] Recorded: {thread.thread_type.value} - {thread.content[:50]}..."
        )
        return thread.id

    def _urd_commentary(self, thread: WyrdThread) -> str:
        """Urd's commentary on what was."""
        commentaries = {
            WyrdType.ACTION: "What is done cannot be undone.",
            WyrdType.CHOICE: "The path chosen closes others.",
            WyrdType.OATH: "Words of binding echo through time.",
            WyrdType.BETRAYAL: "The broken oath poisons the well.",
            WyrdType.DEATH: "They have passed to other halls.",
            WyrdType.BLESSING: "The gods have smiled.",
            WyrdType.CURSE: "A shadow falls upon the thread.",
        }
        return commentaries.get(thread.thread_type, "It is woven.")

    def get_karma_history(self) -> List[Tuple[str, int]]:
        """Get karma changes over time."""
        return [
            (t.id, t.karma_shift) for t in self.threads.values() if t.karma_shift != 0
        ]

    def get_significant_past(self, limit: int = 10) -> List[WyrdThread]:
        """Get most significant past events."""
        significant = [
            self.threads[tid]
            for tid in self.state.significant_events
            if tid in self.threads
        ]
        return sorted(significant, key=lambda t: t.importance, reverse=True)[:limit]


class MimirWell:
    """
    Mímisbrunnr - The Well of Wisdom/Present

    Reflects the current state of all things.
    Where knowledge and insight dwell.
    Odin gave an eye for a drink from this well.
    """

    def __init__(self):
        self.state = WellState(
            name="Mímisbrunnr",
            domain=NornDomain.VERDANDI,
            last_updated=datetime.now().isoformat(),
        )
        # Current active states
        self.active_conditions: Dict[str, Any] = {}
        self.character_states: Dict[str, Dict] = {}
        self.relationship_web: Dict[
            str, Dict[str, int]
        ] = {}  # char_id -> {other_id: relationship_score}
        self.active_oaths: List[Dict] = []
        self.active_quests: List[Dict] = []

    def _normalize_chaos_temperature(self, value: Any) -> int:
        """Normalize chaos factor to the 1-100 range for well omens."""
        try:
            return max(1, min(100, int(value)))
        except (TypeError, ValueError):
            logger.warning(
                "[MIMIR] Received non-numeric chaos_factor %r; using default 30.",
                value,
            )
            return 30

    def reflect(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Reflect the current state in the well.
        Returns wisdom about the present moment.
        """
        self.state.last_updated = datetime.now().isoformat()

        # Update character states
        if "player_character" in game_state:
            pc = game_state["player_character"]
            pc_id = game_state.get("player_character_id", "player")
            self.character_states[pc_id] = {
                "health": pc.get("stats", {}).get("current_hp", 0),
                "max_health": pc.get("stats", {}).get("max_hp", 0),
                "karma": self.state.total_karma,
                "location": game_state.get("current_location_id", "unknown"),
                "conditions": pc.get("conditions", []),
            }

        # Update NPCs present
        for npc in game_state.get("npcs_present", []):
            npc_id = npc.get("id", "")
            if npc_id:
                self.character_states[npc_id] = {
                    "present": True,
                    "location": game_state.get("current_location_id", ""),
                    "disposition": npc.get("loyalty", 50),
                }

        # Return wisdom
        return {
            "turn": game_state.get("turn_count", 0),
            "chaos_factor": game_state.get("chaos_factor", 30),
            "total_karma": self.state.total_karma,
            "active_oaths": len(self.active_oaths),
            "character_count": len(self.character_states),
            "verdandi_speaks": self._verdandi_wisdom(game_state),
        }

    def _verdandi_wisdom(self, game_state: Dict) -> str:
        """Verdandi speaks of what is becoming."""
        chaos = self._normalize_chaos_temperature(game_state.get("chaos_factor", 30))
        karma = self.state.total_karma

        if chaos >= 75:
            return "The threads tangle and twist. Chaos rises."
        elif chaos <= 25:
            return "The pattern is clear and orderly."
        elif karma > 20:
            return "Honor shines bright upon this thread."
        elif karma < -20:
            return "Shadows gather. The thread grows dark."
        else:
            return "The weaving continues as it must."

    def update_relationship(self, char1: str, char2: str, change: int):
        """Update relationship between two characters."""
        if char1 not in self.relationship_web:
            self.relationship_web[char1] = {}
        if char2 not in self.relationship_web:
            self.relationship_web[char2] = {}

        current1 = self.relationship_web[char1].get(char2, 0)
        current2 = self.relationship_web[char2].get(char1, 0)

        self.relationship_web[char1][char2] = current1 + change
        self.relationship_web[char2][char1] = current2 + change

    def add_oath(self, oath: Dict):
        """Record an oath made."""
        oath["sworn_at"] = datetime.now().isoformat()
        oath["fulfilled"] = False
        self.active_oaths.append(oath)
        logger.info(f"[MIMIR] Oath recorded: {oath.get('content', 'unknown oath')}")

    def speak_wisdom(self, game_state: Dict[str, Any]) -> str:
        """
        Speak wisdom about the present moment.
        Called by /wyrd command to display Mimir's wisdom.
        """
        return self._verdandi_wisdom(game_state)


class HvergelmiWell:
    """
    Hvergelmir - The Roaring Cauldron of Potential

    Where possibility churns.
    The source of all rivers (outcomes).
    Níðhöggr gnaws at the roots here.
    """

    def __init__(self):
        self.state = WellState(
            name="Hvergelmir",
            domain=NornDomain.SKULD,
            last_updated=datetime.now().isoformat(),
        )
        # Probability weights for different outcomes
        self.fate_weights: Dict[str, float] = {}
        # Pending possibilities
        self.pending_threads: List[Dict] = []
        # Prophecies and foreshadowing
        self.prophecies: List[Dict] = []

    def _normalize_chaos_temperature(self, value: Any) -> int:
        """Normalize chaos factor to the 1-100 range for future threads."""
        try:
            return max(1, min(100, int(value)))
        except (TypeError, ValueError):
            logger.warning(
                "[HVERGELMIR] Received non-numeric chaos_factor %r; using default 30.",
                value,
            )
            return 30

    def divine(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Divine the future possibilities.
        Returns probability-weighted outcomes.
        """
        self.state.last_updated = datetime.now().isoformat()

        chaos = self._normalize_chaos_temperature(context.get("chaos_factor", 30))
        karma = context.get("total_karma", 0)

        # Calculate base probabilities
        fortune_base = 50 + (karma // 5)  # Karma affects luck
        # Generate fate weights
        self.fate_weights = {
            "good_fortune": min(95, max(5, fortune_base + random.randint(-10, 10))),
            "random_event_chance": min(80, max(10, 20 + int(chaos / 4))),
            "encounter_hostility": min(
                90, max(10, 50 - (karma // 2) + random.randint(-10, 10))
            ),
            "divine_intervention": 5 if abs(karma) > 30 else 1,
            "chaos_spike_chance": int(max(5, chaos * 0.8)),
        }

        # Skuld speaks
        prophecy = self._skuld_prophecy(context)

        return {
            "fate_weights": self.fate_weights,
            "skuld_speaks": prophecy,
            "threads_pending": len(self.pending_threads),
            "active_prophecies": len(self.prophecies),
        }

    def _skuld_prophecy(self, context: Dict) -> str:
        """Skuld speaks of what shall be."""
        chaos = self._normalize_chaos_temperature(context.get("chaos_factor", 30))
        karma = context.get("total_karma", 0)

        prophecies = []

        if chaos >= 70:
            prophecies.append("I see a storm on the horizon.")
        if karma < -15:
            prophecies.append("The shadows lengthen before you.")
        if karma > 15:
            prophecies.append("Light follows your footsteps.")
        if context.get("active_oaths", 0) > 0:
            prophecies.append("Oaths bind the future to the past.")

        if not prophecies:
            prophecies = ["The threads are still being woven."]

        return " ".join(prophecies)

    def add_prophecy(self, content: str, conditions: Dict = None):
        """Add a prophecy that may come to pass."""
        self.prophecies.append(
            {
                "content": content,
                "conditions": conditions or {},
                "added": datetime.now().isoformat(),
                "fulfilled": False,
            }
        )

    def check_prophecies(self, current_state: Dict) -> List[Dict]:
        """Check if any prophecies should be fulfilled."""
        fulfilled = []
        for prophecy in self.prophecies:
            if prophecy["fulfilled"]:
                continue

            # Check conditions
            conditions_met = True
            for key, value in prophecy.get("conditions", {}).items():
                if current_state.get(key) != value:
                    conditions_met = False
                    break

            if conditions_met:
                prophecy["fulfilled"] = True
                fulfilled.append(prophecy)

        return fulfilled

    def speak_prophecy(self, context: Dict[str, Any]) -> str:
        """
        Speak prophecy about the future.
        Called by /wyrd command to display Skuld's prophecy.
        """
        return self._skuld_prophecy(context)


class WyrdSystem:
    """
    The complete Wyrd system integrating all three wells.

    All game events flow through this system:
    1. Events are recorded in Urðarbrunnr (past)
    2. Current state is reflected in Mímisbrunnr (present)
    3. Possibilities are calculated in Hvergelmir (future)
    """

    def __init__(self, data_path: str = None, dispatcher=None):
        self.data_path = Path(data_path) if data_path else Path("data")
        self.dispatcher = dispatcher
        self.engine = None

        if self.dispatcher:
            # We import here to avoid circular dependencies if needed
            from systems.event_dispatcher import EventType

            self.dispatcher.subscribe(
                EventType.PLAYER_ACTION.value, self._on_player_action
            )

        # The three wells
        self.urd = UrdWell()  # Past
        self.mimir = MimirWell()  # Present
        self.hvergelmir = HvergelmiWell()  # Future
        # Backward-compatible name used by /wyrd and older call sites
        self.skuld = self.hvergelmir

        # Thread counter for IDs
        self._thread_counter = 0

        # The Norns process all fate
        self.norn_active = True

        logger.info("Wyrd System initialized - The three wells await")

    def _normalize_chaos_temperature(self, value: Any) -> int:
        """Normalize chaos temperature to the modern 1-100 range."""
        try:
            return max(1, min(100, int(value)))
        except (TypeError, ValueError):
            logger.warning(
                "WyrdSystem received non-numeric chaos_factor %r; using default 30.",
                value,
            )
            return 30

    def _self_heal_wells(self) -> None:
        """
        Ensure all wells and aliases exist.

        This keeps the wyrd system resilient if stale save payloads,
        partial migrations, or runtime mutations remove expected attrs.
        """
        # Huginn scouts for broken branches in the world-tree memory.
        if not isinstance(getattr(self, "urd", None), UrdWell):
            logger.warning("[WYRD] Missing Urd well detected; recreating Urðarbrunnr.")
            self.urd = UrdWell()

        if not isinstance(getattr(self, "mimir", None), MimirWell):
            logger.warning("[WYRD] Missing Mimir well detected; recreating Mímisbrunnr.")
            self.mimir = MimirWell()

        if not isinstance(getattr(self, "hvergelmir", None), HvergelmiWell):
            logger.warning("[WYRD] Missing Hvergelmir detected; recreating future well.")
            self.hvergelmir = HvergelmiWell()

        # Keep both names live so Skuld invocations never fail.
        if getattr(self, "skuld", None) is not self.hvergelmir:
            logger.info("[WYRD] Rebinding Skuld alias to Hvergelmir.")
            self.skuld = self.hvergelmir

    def _build_fate_bridge(self) -> Dict[str, Any]:
        """Build cross-system fate context from engine systems when available."""
        fate_bridge: Dict[str, Any] = {
            "fate_threads": [],
            "world_will_focus": "",
            "emotional_weather": "",
        }

        if not self.engine:
            return fate_bridge

        try:
            engine_state = getattr(self.engine, "state", None)
            if engine_state:
                fate_bridge["fate_threads"] = list(
                    getattr(engine_state, "fate_threads", [])
                )[:5]

            world_will = getattr(getattr(self.engine, "mythic_engine", None), "will", None)
            if world_will:
                fate_bridge["world_will_focus"] = str(getattr(world_will, "focus", ""))

            emotional_states = getattr(self.engine, "_emotional_states", {})
            if isinstance(emotional_states, dict) and emotional_states:
                strongest = sorted(
                    emotional_states.items(),
                    key=lambda item: abs(float(item[1].get("value", 0.0))),
                    reverse=True,
                )[:2]
                mood = ", ".join(
                    f"{name}:{entry.get('value', 0):.2f}" for name, entry in strongest
                )
                fate_bridge["emotional_weather"] = mood
        except Exception as exc:
            logger.warning("[WYRD] Fate bridge degraded gracefully: %s", exc)

        return fate_bridge

    def process_event(
        self,
        event_type: WyrdType,
        content: str,
        characters: List[str],
        location: str,
        turn_number: int,
        importance: int = 5,
        karma_shift: int = 0,
        chaos_impact: int = 0,
        caused_by: str = None,
    ) -> WyrdThread:
        """
        Process an event through all three wells.

        This is the main entry point for the Wyrd system.
        Every significant game event should flow through here.
        """
        self._self_heal_wells()
        try:
            # Generate thread ID
            self._thread_counter += 1
            thread_id = f"wyrd_{turn_number}_{self._thread_counter}"

            # Create thread
            thread = WyrdThread(
                id=thread_id,
                thread_type=event_type,
                content=content,
                characters_involved=characters,
                location=location,
                turn_number=turn_number,
                timestamp=datetime.now().isoformat(),
                importance=importance,
                karma_shift=karma_shift,
                chaos_impact=chaos_impact,
                caused_by=caused_by,
            )

            # 1. Record in Urd (Past)
            self.urd.record(thread)

            # 2. Update Mimir (Present)
            self.mimir.state.total_karma += karma_shift
            if event_type == WyrdType.OATH:
                self.mimir.add_oath(
                    {
                        "thread_id": thread_id,
                        "content": content,
                        "characters": characters,
                    }
                )

            # 3. Update Hvergelmir weights (Future)
            # Significant events affect future probabilities
            if importance >= 7:
                self.hvergelmir.pending_threads.append(
                    {
                        "caused_by": thread_id,
                        "potential_type": "consequence",
                        "weight": importance * 0.1,
                    }
                )

            logger.info(
                f"[WYRD] Processed: {event_type.value} | Karma: {karma_shift:+d} | Chaos: {chaos_impact:+d}"
            )

            return thread
        except Exception as exc:
            logger.warning("[WYRD] Event processing degraded; creating fallback thread: %s", exc)
            fallback = WyrdThread(
                id=f"wyrd_fallback_{int(datetime.now().timestamp())}",
                thread_type=WyrdType.CONSEQUENCE,
                content="The weave shuddered, but the Norns recovered the thread.",
                characters_involved=characters or [],
                location=location or "unknown",
                turn_number=turn_number,
                timestamp=datetime.now().isoformat(),
                importance=3,
            )
            self.urd.record(fallback)
            return fallback

    def get_current_wyrd(self, game_state: Dict) -> Dict[str, Any]:
        """
        Get the complete wyrd state for AI processing.

        Returns a summary of past, present, and future threads
        that should inform AI decisions.
        """
        self._self_heal_wells()

        # Reflect present
        present = self.mimir.reflect(game_state)

        # Divine future
        future = self.hvergelmir.divine(
            {
                "chaos_factor": game_state.get("chaos_factor", 30),
                "total_karma": self.mimir.state.total_karma,
                "active_oaths": len(self.mimir.active_oaths),
            }
        )

        # Get significant past
        significant_past = self.urd.get_significant_past(5)

        return {
            "past": {
                "total_threads": len(self.urd.threads),
                "total_karma": self.mimir.state.total_karma,
                "significant_events": [t.content for t in significant_past],
                "urd_speaks": "What was, shapes what is.",
            },
            "present": present,
            "future": future,
            "norn_guidance": self._get_norn_guidance(game_state),
        }

    def _get_norn_guidance(self, game_state: Dict) -> str:
        """The three Norns speak together."""
        karma = self.mimir.state.total_karma
        chaos = self._normalize_chaos_temperature(game_state.get("chaos_factor", 30))

        if karma > 20 and chaos < 35:
            return "The Norns smile. Your thread gleams bright."
        elif karma < -20 and chaos > 65:
            return "The Norns are troubled. Dark threads tangle."
        elif len(self.mimir.active_oaths) > 0:
            return "Oaths bind your fate. The Norns watch closely."
        else:
            return "The weaving continues. Your thread is your own."

    def process_turn_summary(
        self,
        turn_number: int,
        player_action: str,
        narrative_result: str,
        characters_involved: List[str],
        location: str,
        significant_events: List[Dict] = None,
    ) -> List[WyrdThread]:
        """
        Process a complete turn through the Wyrd system.

        This should be called at the end of each turn to record
        everything that happened.
        """
        threads = []

        if not narrative_result:
            narrative_result = "The Norns weave a new thread."

        # Always record the player's action
        action_thread = self.process_event(
            event_type=WyrdType.ACTION,
            content=f"[TURN {turn_number}] {player_action}",
            characters=characters_involved,
            location=location,
            turn_number=turn_number,
            importance=5,
        )
        threads.append(action_thread)

        # Record any significant events
        if significant_events:
            for event in significant_events:
                try:
                    event_type = WyrdType(event.get("type", "action"))
                except (ValueError, TypeError):
                    logger.warning(
                        "Unknown wyrd event type %r; defaulting to ACTION.",
                        event.get("type"),
                    )
                    event_type = WyrdType.ACTION

                event_thread = self.process_event(
                    event_type=event_type,
                    content=event.get("content", "Unknown event"),
                    characters=event.get("characters", []),
                    location=location,
                    turn_number=turn_number,
                    importance=event.get("importance", 5),
                    karma_shift=event.get("karma", 0),
                    chaos_impact=event.get("chaos", 0),
                    caused_by=action_thread.id,
                )
                threads.append(event_thread)

        return threads

    def infer_significant_events(
        self,
        player_action: str,
        narrative_result: str,
        characters_involved: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Infer significant wyrd events from action+narrative text.

        This keeps fate threads flowing even when the AI response does not
        provide explicit structured event payloads.
        """
        action_text = str(player_action or "").lower()
        narrative_text = str(narrative_result or "").lower()
        combined = f"{action_text} {narrative_text}"
        involved = list(characters_involved or [])
        events: List[Dict[str, Any]] = []

        def _append_event(
            event_type: WyrdType,
            content: str,
            importance: int,
            karma: int,
            chaos: int,
        ) -> None:
            events.append(
                {
                    "type": event_type.value,
                    "content": content,
                    "characters": involved,
                    "importance": importance,
                    "karma": karma,
                    "chaos": chaos,
                }
            )

        if any(word in combined for word in ["oath", "swear", "vow", "pledge"]):
            _append_event(
                WyrdType.OATH,
                "An oath was spoken and bound to fate.",
                importance=8,
                karma=3,
                chaos=0,
            )

        if any(
            word in combined
            for word in ["betray", "treach", "break my oath", "oath broken"]
        ):
            _append_event(
                WyrdType.BETRAYAL,
                "A betrayal darkened the weave.",
                importance=9,
                karma=-5,
                chaos=1,
            )

        if any(word in combined for word in ["bless", "favor", "grace of"]):
            _append_event(
                WyrdType.BLESSING,
                "A blessing touched the thread.",
                importance=7,
                karma=2,
                chaos=0,
            )

        if any(word in combined for word in ["curse", "doom", "hex"]):
            _append_event(
                WyrdType.CURSE,
                "A curse was laid upon the thread.",
                importance=7,
                karma=-2,
                chaos=1,
            )

        if any(word in combined for word in ["kill", "slay", "execute"]):
            _append_event(
                WyrdType.DEATH,
                "Death took a place in the saga.",
                importance=9,
                karma=-1,
                chaos=2,
            )

        if any(word in combined for word in ["spare", "mercy", "forgive"]):
            _append_event(
                WyrdType.CONSEQUENCE,
                "Mercy reshaped a thread of consequence.",
                importance=6,
                karma=2,
                chaos=-1,
            )

        return events[:5]

    def _on_player_action(self, event_type: str, context: Dict[str, Any]):
        """Listen to player actions broadcast by the GameState / EventDispatcher.

        NOTE: The engine always calls process_turn_summary() explicitly after
        the AI response is ready (with the full narrative_result and inferred
        significant events). This handler is therefore a no-op — retaining the
        subscription for future cross-system hooks without double-recording.
        """

    def get_wyrd_summary_for_ai(self, max_past: int = 10) -> str:
        """
        Get a text summary of Wyrd for AI consumption.

        This should be included in AI prompts to inform behavior.
        """
        self._self_heal_wells()
        lines = []
        lines.append("=== THE WYRD (FATE) ===")

        # Past
        lines.append("\n[WHAT WAS - URD'S WELL]")
        significant = self.urd.get_significant_past(max_past)
        for thread in significant:
            lines.append(f"  • {thread.content[:100]}")

        # Present
        lines.append("\n[WHAT IS - MIMIR'S WELL]")
        lines.append(f"  Total Karma: {self.mimir.state.total_karma:+d}")
        lines.append(f"  Active Oaths: {len(self.mimir.active_oaths)}")

        # Future
        lines.append("\n[WHAT MAY BE - HVERGELMIR]")
        lines.append(f"  Pending threads: {len(self.hvergelmir.pending_threads)}")
        if self.hvergelmir.prophecies:
            for p in self.hvergelmir.prophecies[:3]:
                if not p["fulfilled"]:
                    lines.append(f"  Prophecy: {p['content']}")

        # Fate bridge from world-will + emotional tides.
        fate_bridge = self._build_fate_bridge()
        if fate_bridge["fate_threads"]:
            lines.append("\n[FATE THREAD PRESSURE]")
            for thread in fate_bridge["fate_threads"]:
                lines.append(f"  • {str(thread)[:100]}")
        if fate_bridge["world_will_focus"]:
            lines.append(
                f"\n[WORLD WILL]  {fate_bridge['world_will_focus'][:120]}"
            )
        if fate_bridge["emotional_weather"]:
            lines.append(
                f"\n[EMOTIONAL WEATHER]  {fate_bridge['emotional_weather']}"
            )

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Return the complete Wyrd state as a plain dict (no file I/O)."""
        return {
            "urd": {
                "threads": {tid: t.to_dict() for tid, t in self.urd.threads.items()},
                "state": asdict(self.urd.state),
            },
            "mimir": {
                "state": asdict(self.mimir.state),
                "active_oaths": self.mimir.active_oaths,
                "relationship_web": self.mimir.relationship_web,
            },
            "hvergelmir": {
                "state": asdict(self.hvergelmir.state),
                "prophecies": self.hvergelmir.prophecies,
                "pending_threads": self.hvergelmir.pending_threads,
            },
            "thread_counter": self._thread_counter,
            "saved_at": datetime.now().isoformat(),
        }

    def save_state(self, filepath: str = None):
        """Save the complete Wyrd state to disk."""
        if not filepath:
            filepath = self.data_path / "wyrd_state.json"

        state = self.to_dict()

        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, default=str)

        logger.info(f"Wyrd state saved to {filepath}")


# Factory function
def create_wyrd_system(data_path: str = None, dispatcher=None) -> WyrdSystem:
    """Create a Wyrd system instance."""
    return WyrdSystem(data_path, dispatcher=dispatcher)
