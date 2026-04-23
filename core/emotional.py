import logging
import time
from typing import Any, Dict, List, Sequence
from yggdrasil_core import tree

logger = logging.getLogger(__name__)


class EmotionService:
    """Core emotional engine service for Norse Saga Engine"""

    def __init__(self, config: dict = None, dispatcher=None):
        self.config = config or {}
        self.dispatcher = dispatcher
        self.channel_weights = self.config.get(
            "channel_weights", {"combat": 1.2, "dialogue": 0.9, "exploration": 1.0}
        )
        self.emotion_states: Dict[str, Dict[str, float]] = {}
        self.emotion_runes: Dict[str, str] = {}
        # VAD → rune cache to avoid one oracle call per NPC per turn.
        self._vad_rune_cache: Dict[tuple, str] = {}

        # Subscribe to actions if we have a dispatcher
        if self.dispatcher:
            from systems.event_dispatcher import EventType

            self.dispatcher.subscribe(
                EventType.PLAYER_ACTION.value, self._on_player_action
            )

    def compute_impact(self, stimulus: str, strength: float, channel: str) -> float:
        """Calculate emotional impact of stimulus"""
        raw = strength * self.channel_weights.get(channel, 1.0)
        return raw

    def _get_or_create_state(self, character_id: str) -> Dict[str, float]:
        if character_id not in self.emotion_states:
            self.emotion_states[character_id] = {
                "anger": 0.0,
                "fear": 0.0,
                "joy": 0.0,
                "sadness": 0.0,
                "surprise": 0.0,
            }
        return self.emotion_states[character_id]

    def update_state(self, emotion: str, impact: float, character_id: str = "player"):
        """Update emotional state with decay and tag with rune"""
        state = self._get_or_create_state(character_id)
        current = state.get(emotion, 0.0)
        state[emotion] = max(0.0, min(1.0, current + impact))

        # Convert to VAD vector and tag with rune
        vad_vector = self.get_vad_vector(character_id)
        self.emotion_runes[character_id] = self.tag_emotion_state(vad_vector)

        if self.dispatcher:
            from systems.event_dispatcher import EventType

            self.dispatcher.dispatch(
                EventType.EMOTION_SPIKED.value,
                {
                    "character_id": character_id,
                    "emotion": emotion,
                    "impact": impact,
                    "new_state": state[emotion],
                },
            )

    def get_state(self, character_id: str = "player") -> Dict[str, float]:
        """Return current emotional state"""
        return self._get_or_create_state(character_id)

    def get_rune(self, character_id: str = "player") -> str:
        """Return current emotional rune tag"""
        return self.emotion_runes.get(character_id, "ᚠ")

    def get_vad_vector(self, character_id: str = "player") -> List[float]:
        """Convert discrete emotions to Valence-Arousal-Dominance vector"""
        # Simple mapping from discrete emotions to VAD space
        emotion_mapping = {
            "anger": [0.1, 0.9, 0.8],  # Low valence, high arousal, high dominance
            "fear": [0.1, 0.9, 0.1],  # Low valence, high arousal, low dominance
            "joy": [0.9, 0.8, 0.7],  # High valence, high arousal, medium dominance
            "sadness": [0.1, 0.1, 0.1],  # Low valence, low arousal, low dominance
            "surprise": [
                0.7,
                0.9,
                0.5,
            ],  # Medium valence, high arousal, medium dominance
        }

        # Weighted average of emotion vectors
        total_vector = [0.0, 0.0, 0.0]
        total_weight = 0.0

        for emotion, intensity in self._get_or_create_state(character_id).items():
            if emotion in emotion_mapping:
                mapped = emotion_mapping[emotion]
                total_vector[0] += mapped[0] * intensity
                total_vector[1] += mapped[1] * intensity
                total_vector[2] += mapped[2] * intensity
                total_weight += intensity

        if total_weight > 0:
            return [component / total_weight for component in total_vector]
        return [0.5, 0.5, 0.5]  # Neutral state

    def tag_emotion_state(self, vad_vector: Sequence[float]) -> str:
        """Tag emotional state with rune using AI (result cached by VAD key)."""
        vector = (
            vad_vector.tolist() if hasattr(vad_vector, "tolist") else list(vad_vector)
        )
        # Cache key: VAD rounded to 2 dp to avoid redundant oracle calls per turn.
        cache_key = tuple(round(v, 2) for v in vector)
        if cache_key in self._vad_rune_cache:
            return self._vad_rune_cache[cache_key]
        prompt = f"Convert this VAD vector to a Norse rune: {vector}"
        try:
            rune = tree.call_oracle(
                prompt,
                system_msg="You are an expert in Norse runes and emotional states.",
            )
        except Exception as e:
            logger.warning("Error calling oracle for emotion tagging: %s", e)
            rune = "ᚠ"  # Default rune Fehu
        self._vad_rune_cache[cache_key] = rune
        return rune

    def apply_chronotype_mod(self, time_of_day: str, chronotype: str) -> float:
        """Apply chronotype modifier to emotional responses"""
        if chronotype == "nocturnal" and time_of_day in ["night", "midnight"]:
            return 1.1
        elif chronotype == "diurnal" and time_of_day == "day":
            return 1.05
        return 1.0

    def broadcast_pulse(self, matrix, character_id: str = "player"):
        """Broadcast emotional pulse through communication matrix"""
        # Get current emotional state
        vad_vector = self.get_vad_vector(character_id)

        # Create pulse message
        pulse = {
            "rune": self.get_rune(character_id),
            "vector": vad_vector.tolist()
            if hasattr(vad_vector, "tolist")
            else list(vad_vector),
            "timestamp": time.time(),
            "character_id": character_id,
        }

        try:
            # Broadcast through all pathways
            for pathway in getattr(matrix, "pathways", []):
                message_type = getattr(pathway, "EMOTIONAL_PULSE", "EMOTIONAL_PULSE")
                if message_type in getattr(pathway, "message_types", []):
                    pathway.send_message(message_type, pulse)
            logger.debug(
                "[EMOTION] Broadcast pulse: %s for %s", pulse["rune"], character_id
            )
        except Exception as e:
            logger.warning("Failed broadcasting emotional pulse: %s", e)

    def _on_player_action(self, event_type: str, context: Dict[str, Any]):
        """Listen to player actions and subtly shift emotional traits of NPCs present"""
        action = context.get("action", "").lower()
        engine = context.get("engine")
        if not action or not engine:
            return

        npcs = context.get("characters_involved", [])
        for npc_id in npcs:
            if not npc_id:
                continue

            # Very basic NLP rules to emotionally tag the action for NPCs
            if any(w in action for w in ["kill", "attack", "threat", "strike"]):
                self.update_state("fear", 0.1, npc_id)
                self.update_state("anger", 0.1, npc_id)
            elif any(w in action for w in ["help", "heal", "give", "smile", "greet"]):
                self.update_state("joy", 0.1, npc_id)
            elif any(w in action for w in ["insult", "spit", "mock"]):
                self.update_state("anger", 0.2, npc_id)

            # Sync back to the WorldState so it can be saved/loaded
            if (
                hasattr(engine, "state")
                and getattr(engine.state, "emotional_states", None) is not None
            ):
                engine.state.emotional_states[npc_id] = self.get_state(npc_id)

        # Also sync player emotional state to WorldState
        if (
            hasattr(engine, "state")
            and getattr(engine.state, "emotional_states", None) is not None
        ):
            engine.state.emotional_states["player"] = self.get_state("player")
