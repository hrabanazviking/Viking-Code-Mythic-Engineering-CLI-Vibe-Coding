"""
Enhanced Yggdrasil AI Router with prompt_builder Integration
=============================================================

This enhanced router integrates the prompt_builder system with Yggdrasil
to provide comprehensive AI call routing with full chart data integration.

Key Features:
1. Uses prompt_builder for all prompt construction
2. Integrates Yggdrasil cognitive context
3. Supports all AI call types with enhanced context
4. Maintains backward compatibility with existing router
"""

import logging
import time
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

import yaml

logger = logging.getLogger(__name__)


class AICallType(Enum):
    """Types of AI calls that can be routed."""

    DIALOGUE = "dialogue"  # NPC speech
    NARRATION = "narration"  # Scene descriptions
    COMBAT = "combat"  # Combat narration
    PLANNING = "planning"  # Strategic decisions
    MEMORY = "memory"  # Memory formation
    ANALYSIS = "analysis"  # Situation analysis
    CREATION = "creation"  # NPC/item/location generation
    REACTION = "reaction"  # NPC reactions
    SUMMARY = "summary"  # Turn summaries
    PROPHECY = "prophecy"  # Divine/mystical content
    CHARACTER_VOICE = "character_voice"  # Character-specific dialogue


@dataclass
class CharacterDataFeed:
    """
    Complete character data prepared for AI consumption.

    This ensures AI ALWAYS has full character information.
    """

    character_id: str
    name: str

    # Identity
    gender: str = ""
    age: int = 0
    role: str = ""
    culture: str = "norse"
    social_class: str = ""

    # Stats (D&D 5E)
    level: int = 1
    hit_points: int = 0
    max_hp: int = 0
    armor_class: int = 10
    ability_scores: Dict[str, int] = field(default_factory=dict)
    skills: List[str] = field(default_factory=list)

    # Appearance
    appearance_summary: str = ""
    notable_features: List[str] = field(default_factory=list)

    # Personality
    personality_traits: List[str] = field(default_factory=list)
    ideals: List[str] = field(default_factory=list)
    bonds: List[str] = field(default_factory=list)
    flaws: List[str] = field(default_factory=list)

    # Background
    backstory_summary: str = ""
    motivation: str = ""
    secrets: List[str] = field(default_factory=list)

    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)

    # Current state
    current_location: str = ""
    current_activity: str = ""
    mood: str = "neutral"
    conditions: List[str] = field(default_factory=list)

    # Equipment
    equipped_weapon: str = ""
    equipped_armor: str = ""
    notable_items: List[str] = field(default_factory=list)

    # Attire / nudity state
    attire: str = ""

    def to_ai_text(self) -> str:
        """Convert to text for AI prompt."""
        lines = [
            f"=== {self.name} ({self.role}) ===",
            f"Gender: {self.gender} | Age: {self.age} | Class: {self.social_class}",
        ]

        if self.ability_scores:
            scores = ", ".join(
                f"{k[:3].upper()}: {v}" for k, v in self.ability_scores.items()
            )
            lines.append(f"Stats: {scores}")

        if self.appearance_summary:
            lines.append(f"Appearance: {self.appearance_summary}")

        if self.attire:
            lines.append(f"Attire: {self.attire}")

        if self.personality_traits:
            lines.append(f"Personality: {', '.join(str(t) for t in self.personality_traits)}")

        if self.backstory_summary:
            lines.append(f"Background: {self.backstory_summary[:200]}")

        if self.motivation:
            lines.append(f"Motivation: {self.motivation}")

        if self.mood != "neutral":
            lines.append(f"Current Mood: {self.mood}")

        if self.current_activity:
            lines.append(f"Currently: {self.current_activity}")

        return "\n".join(lines)

    @staticmethod
    def _resolve_attire(char: Dict, identity: Dict) -> str:
        """
        Determine the character's current attire from YAML fields.

        Priority:
        1. Bondmaid / thrall / slave role → always naked with restraints.
        2. Top-level ``nude`` boolean flag.
        3. ``clothing.serving_attire`` / ``clothing.default`` / ``clothing.daily``.
        4. ``appearance.clothing_style``.
        Falls back to empty string (attire line omitted from prompt).
        """
        role_str = str(identity.get("role", "")).lower()
        social_str = str(identity.get("social_class", "")).lower()
        enslaved_tokens = ("bondmaid", "thrall", "slave", "enslaved", "owned")
        if any(t in role_str or t in social_str for t in enslaved_tokens):
            return "naked — metal collar, bondage wrist cuffs, bondage ankle cuffs"

        if char.get("nude", False):
            return "naked"

        clothing = char.get("clothing", {})
        if isinstance(clothing, dict):
            for key in ("serving_attire", "default", "daily"):
                val = clothing.get(key, "")
                if val:
                    return str(val)
        elif isinstance(clothing, str) and clothing:
            return clothing

        return str(char.get("appearance", {}).get("clothing_style", ""))

    @classmethod
    def from_character_dict(cls, char: Dict) -> "CharacterDataFeed":
        """Create from a character dictionary."""
        identity = char.get("identity", {})
        stats = char.get("stats", {})
        appearance = char.get("appearance", {})
        personality = char.get("personality", {})
        backstory = char.get("backstory", {})

        return cls(
            character_id=char.get("id", ""),
            name=identity.get("name", "Unknown"),
            gender=identity.get("gender", ""),
            age=identity.get("age", 0),
            role=identity.get("role", ""),
            culture=identity.get("culture", "norse"),
            social_class=identity.get("social_class", ""),
            level=stats.get("level", 1),
            hit_points=stats.get("current_hp", stats.get("hit_points", 0)),
            max_hp=stats.get("max_hp", 0),
            armor_class=stats.get("armor_class", 10),
            ability_scores=stats.get("ability_scores", {}),
            skills=stats.get("proficiencies", {}).get("skills", []),
            appearance_summary=appearance.get("summary", ""),
            notable_features=appearance.get("notable_features", []),
            personality_traits=personality.get("traits", []),
            ideals=personality.get("ideals", []),
            bonds=personality.get("bonds", []),
            flaws=personality.get("flaws", []),
            backstory_summary=backstory.get("summary", ""),
            motivation=backstory.get("motivation", ""),
            secrets=backstory.get("secrets", []),
            relationships=char.get("relationships", {}),
            current_location=char.get("current_location", ""),
            current_activity=char.get("current_activity", ""),
            mood=char.get("mood", "neutral"),
            conditions=char.get("conditions", []),
            equipped_weapon=char.get("equipment", {}).get("main_hand", ""),
            equipped_armor=char.get("equipment", {}).get("armor", ""),
            notable_items=char.get("equipment", {}).get("notable", []),
            attire=cls._resolve_attire(char, identity),
        )


@dataclass
class AICallContext:
    """
    Complete context for an AI call.

    Everything the AI needs to know is packaged here.
    """

    call_type: AICallType
    turn_number: int
    timestamp: str

    # Characters
    player_character: Optional[CharacterDataFeed] = None
    involved_characters: List[CharacterDataFeed] = field(default_factory=list)

    # Location
    location_id: str = ""
    location_name: str = ""
    location_description: str = ""

    # Game state
    chaos_factor: int = 1
    time_of_day: str = "day"
    weather: str = "clear"

    # Social context
    social_protocols: Dict[str, Any] = field(default_factory=dict)

    # Memory context
    recent_events: List[str] = field(default_factory=list)
    relevant_memories: List[str] = field(default_factory=list)

    # Wyrd
    wyrd_summary: str = ""
    karma: int = 0

    # Dice results (if applicable)
    dice_results: List[Dict] = field(default_factory=list)

    # Prompt builder context
    game_context: Optional[Any] = None  # GameContext from prompt_builder
    include_yggdrasil: bool = False

    def to_prompt_context(self) -> str:
        """Generate context text for AI prompt."""
        sections = []

        # Player character
        if self.player_character:
            sections.append("=== PLAYER CHARACTER ===")
            sections.append(self.player_character.to_ai_text())

        # Involved NPCs
        if self.involved_characters:
            sections.append("\n=== CHARACTERS PRESENT ===")
            for char in self.involved_characters:
                sections.append(char.to_ai_text())
                sections.append("")

        # Location
        sections.append(f"\n=== LOCATION: {self.location_name} ===")
        if self.location_description:
            sections.append(self.location_description[:500])

        # Game state
        sections.append("\n=== CURRENT STATE ===")
        sections.append(
            f"Turn: {self.turn_number} | Time: {self.time_of_day} | Weather: {self.weather}"
        )
        sections.append(f"Chaos Factor: {self.chaos_factor}/9 | Karma: {self.karma:+d}")

        # Recent events
        if self.recent_events:
            sections.append("\n=== RECENT EVENTS ===")
            for event in self.recent_events[-5:]:
                sections.append(f"  • {event}")

        # Dice results
        if self.dice_results:
            sections.append("\n=== DICE RESULTS ===")
            for result in self.dice_results:
                sections.append(f"  {result.get('description', str(result))}")

        # Wyrd
        if self.wyrd_summary:
            sections.append(f"\n{self.wyrd_summary}")

        return "\n".join(sections)


class EnhancedYggdrasilAIRouter:
    """
    Enhanced AI router with prompt_builder integration.

    This router:
    1. Uses prompt_builder for all prompt construction
    2. Integrates Yggdrasil cognitive context
    3. Supports all AI call types with enhanced context
    4. Maintains backward compatibility with existing router
    """

    def __init__(
        self,
        llm_callable: Callable[[str, str], str],
        prompt_builder: Any,  # PromptBuilder instance
        data_path: str = None,
        comprehensive_logger=None,
        wyrd_system=None,
        enhanced_memory=None,
        yggdrasil_cognition=None,
    ):
        self.llm = llm_callable
        self.prompt_builder = prompt_builder
        self.data_path = Path(data_path) if data_path else Path("data")
        self.comp_logger = comprehensive_logger
        self.wyrd = wyrd_system
        self.memory = enhanced_memory
        self.yggdrasil = yggdrasil_cognition

        # Connect prompt_builder to Yggdrasil if available
        if self.yggdrasil and hasattr(self.prompt_builder, "connect_yggdrasil"):
            self.prompt_builder.connect_yggdrasil(self.yggdrasil, self)

        # Load social protocols
        self.social_protocols = self._load_social_protocols()

        # Call tracking
        self.call_count = 0
        self.total_time = 0.0

        logger.info(
            "EnhancedYggdrasilAIRouter initialized with prompt_builder integration"
        )

    def _load_social_protocols(self) -> Dict[str, Any]:
        """Load Viking social protocols from charts."""
        protocols = {}

        chart_files = [
            "viking_social_protocols.yaml",
            "viking_and_norse_pagan_social_protocols.yaml",
            "viking_cultural_practices.yaml",
            "viking_values.yaml",
        ]

        for chart_file in chart_files:
            chart_path = self.data_path / "charts" / chart_file
            if chart_path.exists():
                try:
                    with open(chart_path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict):
                            protocols.update(data)
                except Exception as e:
                    logger.warning(f"Could not load protocol chart {chart_file}: {e}")

        return protocols

    def prepare_context(
        self,
        call_type: AICallType,
        game_state: Dict,
        involved_npcs: List[Dict] = None,
        additional_context: Dict = None,
    ) -> AICallContext:
        """Prepare complete context for an AI call."""
        # Convert game state to context
        turn_number = game_state.get("turn_number", 1)
        chaos_factor = game_state.get("chaos_factor", 30)

        # Prepare character data
        player_char = None
        if game_state.get("player_character"):
            player_char = CharacterDataFeed.from_character_dict(
                game_state["player_character"]
            )

        involved_chars = []
        if involved_npcs:
            for npc in involved_npcs:
                involved_chars.append(CharacterDataFeed.from_character_dict(npc))

        # Create GameContext for prompt_builder if needed
        game_context = None
        try:
            from ai.prompt_builder import GameContext as _GameContext
            game_context = _GameContext(
                player_character=game_state.get("player_character"),
                current_location=game_state.get("current_location", ""),
                location_description=game_state.get("location_description", ""),
                location_type=game_state.get("location_type", "settlement"),
                time_of_day=game_state.get("time_of_day", "day"),
                npcs_present=involved_npcs or [],
                chaos_factor=chaos_factor,
            )
        except Exception as e:
            logger.warning("Could not create GameContext: %s", e)

        return AICallContext(
            call_type=call_type,
            turn_number=turn_number,
            timestamp=datetime.now().isoformat(),
            player_character=player_char,
            involved_characters=involved_chars,
            location_name=game_state.get("current_location", "Unknown"),
            location_description=game_state.get("location_description", ""),
            chaos_factor=chaos_factor,
            time_of_day=game_state.get("time_of_day", "day"),
            weather=game_state.get("weather", "clear"),
            recent_events=game_state.get("recent_events", []),
            wyrd_summary=game_state.get("wyrd_summary", ""),
            karma=game_state.get("karma", 0),
            dice_results=additional_context.get("dice_results", [])
            if additional_context
            else [],
            game_context=game_context,
            include_yggdrasil=self.yggdrasil is not None,
        )

    def _sanitize_text(self, text: str, max_chars: int = 8000) -> str:
        """Bound text size for stability in downstream LLM calls."""
        safe_text = text if isinstance(text, str) else str(text)
        return safe_text[:max_chars]

    def route_call(
        self,
        call_type: AICallType,
        prompt: str,
        game_state: Dict,
        involved_npcs: List[Dict] = None,
        additional_context: Dict = None,
        system_prompt: str = None,
        use_prompt_builder: bool = True,
    ) -> str:
        """
        Route an AI call through enhanced Yggdrasil.

        This method can use prompt_builder for enhanced prompt construction.
        """
        start_time = time.time()
        self.call_count += 1
        prompt = self._sanitize_text(prompt)
        # Prepare full context
        context = self.prepare_context(
            call_type=call_type,
            game_state=game_state,
            involved_npcs=involved_npcs,
            additional_context=additional_context,
        )

        # Build prompts
        if use_prompt_builder and context.game_context:
            full_system, full_prompt = self._build_with_prompt_builder(
                call_type, context, prompt, system_prompt
            )
        else:
            full_system = self._build_system_prompt(call_type, context, system_prompt)
            full_prompt = self._build_full_prompt(prompt, context)

        full_system = self._sanitize_text(full_system, max_chars=12000)
        full_prompt = self._sanitize_text(full_prompt, max_chars=24000)

        # Log the call
        if self.comp_logger:
            self.comp_logger.log_ai_call(
                realm=f"yggdrasil_{call_type.value}",
                call_type=call_type.value,
                prompt=full_prompt,
                response="[pending]",
                context={"type": call_type.value, "turn": context.turn_number},
                characters=[c.name for c in context.involved_characters],
                data_sources=[
                    "character_sheets",
                    "social_protocols",
                    "wyrd",
                    "memory",
                    "prompt_builder",
                ],
                data_path=["EnhancedYggdrasilRouter", call_type.value],
            )

        # Make the LLM call
        try:
            response = self.llm(full_system, full_prompt)

            elapsed = time.time() - start_time
            self.total_time += elapsed

            # Log successful response
            if self.comp_logger:
                self.comp_logger.log_ai_call(
                    realm=f"yggdrasil_{call_type.value}",
                    call_type=call_type.value,
                    prompt=full_prompt,
                    response=response,
                    processing_time=elapsed,
                    success=True,
                    data_path=["EnhancedYggdrasilRouter", call_type.value, "complete"],
                )

            logger.info(
                f"[AI:{call_type.value}] Completed in {elapsed:.2f}s (prompt_builder: {use_prompt_builder})"
            )

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"AI call failed: {e}")

            if self.comp_logger:
                self.comp_logger.log_error(
                    e, f"EnhancedYggdrasilRouter.{call_type.value}"
                )

            return "The Norns cloud the path; I could not weave a response this turn. Please try again."

    def _resolve_companion_context(
        self,
        game_context,
        character_name: str,
        character_id: str,
    ) -> Dict[str, Any]:
        """Huginn matches scene actors to companion continuity packets."""
        try:
            ygg = getattr(game_context, "yggdrasil_context", {})
            companions = ygg.get("npc_companions", []) if isinstance(ygg, dict) else []
            if not isinstance(companions, list):
                return {}
            cid = str(character_id or "").strip().lower()
            cname = str(character_name or "").strip().lower()
            for item in companions:
                if not isinstance(item, dict):
                    continue
                item_id = str(item.get("npc_id", "")).strip().lower()
                item_name = str(item.get("name", "")).strip().lower()
                if cid and item_id == cid:
                    return item
                if cname and item_name == cname:
                    return item
            return {}
        except Exception:
            logger.warning("Companion context resolution failed.", exc_info=True)
            return {}

    def _build_with_prompt_builder(
        self,
        call_type: AICallType,
        context: AICallContext,
        user_prompt: str,
        custom_system: str = None,
    ) -> tuple[str, str]:
        """Build prompts using prompt_builder."""
        try:
            # Map call types to prompt_builder methods
            if call_type == AICallType.NARRATION:
                system_prompt = self.prompt_builder.build_narrator_prompt(
                    context=context.game_context,
                    player_action=user_prompt,
                    include_mechanics=False,
                    memory_context="",
                    include_yggdrasil=context.include_yggdrasil,
                )
                user_prompt_enhanced = user_prompt

            elif call_type == AICallType.DIALOGUE:
                # For dialogue, we need to identify which character is speaking
                if context.involved_characters:
                    char_data = context.involved_characters[0]
                    # Convert back to character dict for prompt_builder
                    char_dict = {
                        "identity": {"name": char_data.name},
                        "personality": {"traits": char_data.personality_traits},
                        "backstory": {"summary": char_data.backstory_summary},
                    }
                    companion_context = self._resolve_companion_context(
                        context.game_context,
                        char_data.name,
                        "",
                    )
                    system_prompt = self.prompt_builder.build_character_voice_prompt(
                        character=char_dict,
                        situation=user_prompt,
                        include_yggdrasil=context.include_yggdrasil,
                        game_context=context.game_context,
                        companion_context=companion_context,
                    )
                    user_prompt_enhanced = f"Respond to: {user_prompt}"
                else:
                    # Fallback to narrator prompt
                    system_prompt = self.prompt_builder.build_narrator_prompt(
                        context=context.game_context,
                        player_action=user_prompt,
                        include_mechanics=False,
                        memory_context="",
                        include_yggdrasil=context.include_yggdrasil,
                    )
                    user_prompt_enhanced = user_prompt

            elif call_type == AICallType.CHARACTER_VOICE:
                # Specialized character voice prompt
                if context.involved_characters:
                    char_data = context.involved_characters[0]
                    char_dict = {
                        "identity": {"name": char_data.name},
                        "personality": {"traits": char_data.personality_traits},
                        "backstory": {"summary": char_data.backstory_summary},
                    }
                    companion_context = self._resolve_companion_context(
                        context.game_context,
                        char_data.name,
                        "",
                    )
                    system_prompt = self.prompt_builder.build_character_voice_prompt(
                        character=char_dict,
                        situation=user_prompt,
                        include_yggdrasil=context.include_yggdrasil,
                        game_context=context.game_context,
                        companion_context=companion_context,
                    )
                    user_prompt_enhanced = user_prompt
                else:
                    system_prompt = self.prompt_builder.build_narrator_prompt(
                        context=context.game_context,
                        player_action=user_prompt,
                        include_mechanics=False,
                        memory_context="",
                        include_yggdrasil=context.include_yggdrasil,
                    )
                    user_prompt_enhanced = user_prompt

            else:
                # For other call types, use base prompt with enhancements
                system_prompt = self.prompt_builder.build_base_personality(
                    n_principles=8
                )
                system_prompt += "\n\n" + self.prompt_builder.build_cultural_filter(
                    n_values=6
                )

                # Add Yggdrasil context if enabled
                if context.include_yggdrasil:
                    ygg_context = self.prompt_builder.build_yggdrasil_context(
                        context.game_context
                    )
                    if ygg_context:
                        system_prompt += "\n\n" + ygg_context

                user_prompt_enhanced = (
                    context.to_prompt_context()
                    + "\n\n=== YOUR TASK ===\n"
                    + user_prompt
                )

            # Add custom system prompt if provided
            if custom_system:
                system_prompt += "\n\n" + custom_system

            return system_prompt, user_prompt_enhanced

        except Exception as e:
            logger.error(f"Error building prompt with prompt_builder: {e}")
            # Fall back to basic prompt building
            return self._build_system_prompt(
                call_type, context, custom_system
            ), self._build_full_prompt(user_prompt, context)

    def _build_system_prompt(
        self, call_type: AICallType, context: AICallContext, custom_system: str = None
    ) -> str:
        """Build the complete system prompt (fallback method)."""
        sections = []

        ai_prompts = getattr(self.prompt_builder, "charts", {}).get("ai_prompts", {})
        router_prompts = ai_prompts.get("yggdrasil_router", {})

        # Base instruction
        base = router_prompts.get(
            "instructions",
            "You are the Game Master for a Norse Viking saga RPG. Your responses must be authentic to 9th century Scandinavia.",
        )
        sections.append(base.strip())

        # Call type specific instructions
        type_str = call_type.value if hasattr(call_type, "value") else str(call_type)
        call_types_dict = router_prompts.get("call_types", {})

        if type_str in call_types_dict:
            sections.append(call_types_dict[type_str])
        else:
            # Fallback for undefined types
            type_instructions = {
                AICallType.DIALOGUE: "Generate in-character dialogue for the NPC. Use their personality traits and current mood.",
                AICallType.NARRATION: "Describe the scene vividly with sensory details. Keep the Norse atmosphere.",
                AICallType.COMBAT: "Narrate the combat dramatically. Include the dice results in the narrative.",
                AICallType.PLANNING: "Analyze the situation and provide strategic options.",
                AICallType.MEMORY: "Summarize the events accurately with specific details.",
                AICallType.ANALYSIS: "Analyze the current situation and identify key elements.",
                AICallType.CREATION: "Create a new character/item/location fitting the Norse setting.",
                AICallType.REACTION: "Generate appropriate NPC reactions based on their personality.",
                AICallType.SUMMARY: "Provide a comprehensive summary of what happened.",
                AICallType.PROPHECY: "Speak in mysterious, prophetic terms appropriate to a völva.",
                AICallType.CHARACTER_VOICE: "Speak in the voice of the character, using their personality and background.",
            }
            sections.append(type_instructions.get(call_type, "Respond appropriately."))

        # Social protocols summary
        if self.social_protocols:
            sections.append("\n=== VIKING SOCIAL PROTOCOLS ===")
            sections.append("- Honor (drengskapr) is paramount")
            sections.append("- Social hierarchy: Thrall < Karl < Jarl < King")
            sections.append("- Hospitality to guests is sacred")
            sections.append("- Oaths are binding upon honor")
            sections.append("- Blood feuds may be settled by weregild")
            sections.append("- The gods watch and judge")

        # Chaos factor influence
        chaos = context.chaos_factor
        if chaos >= 70:
            sections.append(
                "\n[HIGH CHAOS] The unexpected is likely. Include surprising elements."
            )
        elif chaos <= 30:
            sections.append(
                "\n[LOW CHAOS] Events proceed predictably. Focus on steady progression."
            )

        # Custom system prompt
        if custom_system:
            sections.append(f"\n{custom_system}")

        return "\n".join(sections)

    def _build_full_prompt(self, prompt: str, context: AICallContext) -> str:
        """Build the complete user prompt with context (fallback method)."""
        sections = []

        # Context
        sections.append(context.to_prompt_context())

        # The actual prompt
        sections.append("\n=== YOUR TASK ===")
        sections.append(prompt)

        return "\n".join(sections)

    # Convenience methods for specific call types

    def generate_dialogue(
        self,
        npc: Dict,
        game_state: Dict,
        player_action: str,
        use_prompt_builder: bool = True,
    ) -> str:
        """Generate NPC dialogue."""
        prompt = f"The player {player_action}. Generate {npc.get('identity', {}).get('name', 'the NPC')}'s response."
        return self.route_call(
            call_type=AICallType.DIALOGUE,
            prompt=prompt,
            game_state=game_state,
            involved_npcs=[npc],
            use_prompt_builder=use_prompt_builder,
        )

    def generate_narration(
        self,
        game_state: Dict,
        action: str,
        npcs: List[Dict] = None,
        use_prompt_builder: bool = True,
    ) -> str:
        """Generate scene narration."""
        prompt = f"Narrate: {action}"
        return self.route_call(
            call_type=AICallType.NARRATION,
            prompt=prompt,
            game_state=game_state,
            involved_npcs=npcs,
            use_prompt_builder=use_prompt_builder,
        )

    def generate_character_voice(
        self,
        character: Dict,
        game_state: Dict,
        situation: str,
        use_prompt_builder: bool = True,
    ) -> str:
        """Generate dialogue in a specific character's voice."""
        prompt = f"Speaking as {character.get('identity', {}).get('name', 'the character')}: {situation}"
        return self.route_call(
            call_type=AICallType.CHARACTER_VOICE,
            prompt=prompt,
            game_state=game_state,
            involved_npcs=[character],
            use_prompt_builder=use_prompt_builder,
        )

    def generate_combat_narration(
        self,
        game_state: Dict,
        combat_results: List[Dict],
        npcs: List[Dict],
        use_prompt_builder: bool = True,
    ) -> str:
        """Generate combat narration with dice results."""
        prompt = "Narrate this combat round dramatically."
        return self.route_call(
            call_type=AICallType.COMBAT,
            prompt=prompt,
            game_state=game_state,
            involved_npcs=npcs,
            additional_context={"dice_results": combat_results},
            use_prompt_builder=use_prompt_builder,
        )

    def generate_turn_summary(
        self,
        game_state: Dict,
        player_action: str,
        narrative_result: str,
        use_prompt_builder: bool = True,
    ) -> str:
        """Generate a turn summary for memory."""
        prompt = f"""Summarize this turn:
Player Action: {player_action}
Result: {narrative_result}

Provide a JSON response with: what, why, how, importance (1-10), event_tags, prose_summary"""

        return self.route_call(
            call_type=AICallType.SUMMARY,
            prompt=prompt,
            game_state=game_state,
            use_prompt_builder=use_prompt_builder,
        )


# Factory function
def create_enhanced_yggdrasil_router(
    llm_callable: Callable[[str, str], str],
    prompt_builder: Any,
    data_path: str = None,
    comprehensive_logger=None,
    wyrd_system=None,
    enhanced_memory=None,
    yggdrasil_cognition=None,
) -> EnhancedYggdrasilAIRouter:
    """Create an enhanced Yggdrasil AI router with prompt_builder integration."""
    return EnhancedYggdrasilAIRouter(
        llm_callable=llm_callable,
        prompt_builder=prompt_builder,
        data_path=data_path,
        comprehensive_logger=comprehensive_logger,
        wyrd_system=wyrd_system,
        enhanced_memory=enhanced_memory,
        yggdrasil_cognition=yggdrasil_cognition,
    )
