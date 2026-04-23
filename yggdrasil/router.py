"""
Yggdrasil AI Router - All AI Calls Must Flow Through Here
==========================================================

This is the ONLY entry point for AI calls in the Norse Saga Engine.
No AI system is to bypass Yggdrasil or the Ravens.

Every AI call:
1. Receives full character data for any characters involved
2. Receives current game state and chaos factor
3. Is processed through the appropriate Yggdrasil realm
4. Has results logged comprehensively
5. Updates the Wyrd system

The Router ensures:
- Vikings social protocols are always applied
- Character sheets are always fed to AI
- Dice rolls use character stats
- Memory is properly formed
- All data flows through the sacred wells
"""

import logging
import time
import json
from typing import Dict, List, Any, Callable, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Lazy SRD imports — resolved once at first use
_ConditionsSystem = None
_DndRulesEngine = None


def _get_conditions_system():
    global _ConditionsSystem
    if _ConditionsSystem is None:
        try:
            from systems.conditions_system import ConditionsSystem
            _ConditionsSystem = ConditionsSystem()
        except ImportError:
            pass
    return _ConditionsSystem


def _get_rules_engine():
    global _DndRulesEngine
    if _DndRulesEngine is None:
        try:
            from systems.dnd_rules_engine import DndRulesEngine
            _DndRulesEngine = DndRulesEngine()
        except ImportError:
            pass
    return _DndRulesEngine


from yggdrasil.router_enhanced import AICallType, CharacterDataFeed, AICallContext  # noqa: E402
from systems.context_optimizer import ContextOptimizer
from yggdrasil.identity import validate_identity_isolation

try:
    from ai.prompt_builder import GameContext as _GameContext
except ImportError:
    _GameContext = None
    logger.debug("ai.prompt_builder.GameContext not available; prompt builder disabled.")


class YggdrasilAIRouter:
    """
    The unified AI router. ALL AI calls MUST go through here.

    This ensures:
    - Full character data is always sent
    - Viking social protocols are applied
    - Chaos factor influences results
    - Results are logged
    - Wyrd is updated
    """

    # Class-level cache for social protocol data — loaded once from disk, reused by all instances.
    _social_protocols_cache: Optional[Dict[str, Any]] = None

    def __init__(
        self,
        llm_callable: Callable[[str, str], str],
        data_path: str = None,
        comprehensive_logger=None,
        wyrd_system=None,
        enhanced_memory=None,
        prompt_builder=None,
        yggdrasil_cognition=None,
    ):
        self.llm = llm_callable
        self.data_path = Path(data_path) if data_path else Path("data")
        self.comp_logger = comprehensive_logger
        self.wyrd = wyrd_system
        self.memory = enhanced_memory
        self.prompt_builder = prompt_builder
        self.yggdrasil = yggdrasil_cognition

        # Initialize Yggdrasil cognition system if not provided
        if not self.yggdrasil:
            try:
                from .cognition_integration import YggdrasilCognitionSystem

                self.yggdrasil = YggdrasilCognitionSystem(str(self.data_path))
                logger.info("Yggdrasil cognition system initialized")
            except ImportError as e:
                logger.warning(f"Could not import YggdrasilCognitionSystem: {e}")
                self.yggdrasil = None

        # Connect prompt_builder to Yggdrasil if available
        if (
            self.yggdrasil
            and self.prompt_builder
            and hasattr(self.prompt_builder, "connect_yggdrasil")
        ):
            self.prompt_builder.connect_yggdrasil(self.yggdrasil, self)

        # Load social protocols
        self.social_protocols = self._load_social_protocols()

        # T3-A: Context Optimizer (MEMO — SOTG block) + Identity Protocol (LDP)
        self.context_optimizer = ContextOptimizer(config=None)  # config injected later if available

        # Alfheim — heuristic routing pre-processor (probabilistic branching, path hints)
        try:
            from yggdrasil.worlds.alfheim import Alfheim
            self.alfheim = Alfheim()
        except Exception as _af_exc:
            logger.debug("Alfheim routing pre-processor unavailable: %s", _af_exc)
            self.alfheim = None

        # Asgard — strategic planner for complex multi-step query decomposition
        try:
            from yggdrasil.worlds.asgard import Asgard
            self.asgard = Asgard()
        except Exception as _as_exc:
            logger.debug("Asgard strategic planner unavailable: %s", _as_exc)
            self.asgard = None

        # Call tracking
        self.call_count = 0
        self.total_time = 0.0

        if prompt_builder:
            logger.info("YggdrasilAIRouter initialized with prompt_builder integration")
        else:
            logger.info(
                "YggdrasilAIRouter initialized - All AI flows through Yggdrasil"
            )

    def _load_social_protocols(self) -> Dict[str, Any]:
        """Load Viking social protocols from charts (cached at class level after first load)."""
        if YggdrasilAIRouter._social_protocols_cache is not None:
            return YggdrasilAIRouter._social_protocols_cache
        protocols = {}

        chart_files = [
            "viking_social_protocols.json",
            "viking_and_norse_pagan_social_protocols.json",
            "viking_values.yaml",
            "viking_cultural_practices.yaml",
        ]

        charts_path = self.data_path / "charts"

        for filename in chart_files:
            filepath = charts_path / filename
            if filepath.exists():
                try:
                    if filename.endswith(".json"):
                        with open(filepath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                    else:
                        import yaml

                        with open(filepath, "r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)

                    protocols[filename] = data
                    logger.info(f"Loaded protocols: {filename}")
                except Exception as e:
                    logger.warning(f"Failed to load {filename}: {e}")

        YggdrasilAIRouter._social_protocols_cache = protocols
        return protocols

    def prepare_character_data(
        self, character: Dict, is_player: bool = False
    ) -> CharacterDataFeed:
        """Prepare complete character data for AI."""
        return CharacterDataFeed.from_character_dict(character)

    def prepare_context(
        self,
        call_type: AICallType,
        game_state: Dict,
        involved_npcs: List[Dict] = None,
        additional_context: Dict = None,
    ) -> AICallContext:
        """
        Prepare complete context for an AI call.

        This gathers ALL relevant data for the AI.
        """
        # Player character
        pc = game_state.get("player_character", {})
        pc_feed = self.prepare_character_data(pc, is_player=True) if pc else None

        # Involved NPCs
        npc_feeds = []
        for npc in involved_npcs or []:
            npc_feeds.append(self.prepare_character_data(npc))

        # Create GameContext for prompt_builder if available
        game_context = None
        if self.prompt_builder and _GameContext is not None:
            try:
                kwargs = {
                    "player_character": game_state.get("player_character"),
                    "current_location": game_state.get("current_location_name", ""),
                    "location_description": game_state.get("location_description", ""),
                    "location_type": "wilderness",
                    "time_of_day": game_state.get("time_of_day", "day"),
                    "npcs_present": involved_npcs or [],
                    "chaos_factor": game_state.get("chaos_factor", 30),
                }

                # Check if GameContext has dag_payload (added in World Tree Integration)
                if (
                    hasattr(_GameContext, "__annotations__")
                    and "dag_payload" in _GameContext.__annotations__
                ):
                    kwargs["dag_payload"] = (
                        additional_context.get("dag_payload")
                        if additional_context
                        else None
                    )

                # Create a GameContext directly from the imported class
                game_context = _GameContext(**kwargs)
            except Exception as e:
                logger.warning(f"Could not create GameContext: {e}")

        # Build context
        context = AICallContext(
            call_type=call_type,
            turn_number=game_state.get("turn_count", 0),
            timestamp=datetime.now().isoformat(),
            player_character=pc_feed,
            involved_characters=npc_feeds,
            location_id=game_state.get("current_location_id", ""),
            location_name=game_state.get("current_location_name", ""),
            location_description=game_state.get("location_description", ""),
            chaos_factor=game_state.get("chaos_factor", 30),
            time_of_day=game_state.get("time_of_day", "day"),
            weather=game_state.get("weather", "clear"),
            social_protocols=self.social_protocols,
            game_context=game_context,
            include_yggdrasil=self.yggdrasil is not None,
        )

        # Add recent events from memory
        if self.memory and getattr(self.memory, 'summarizer', None):
            context.recent_events = [
                s.prose_summary for s in self.memory.summarizer.get_recent_summaries(5)
            ]

        # Add Wyrd summary
        if self.wyrd:
            context.wyrd_summary = self.wyrd.get_wyrd_summary_for_ai(5)
            try:
                context.karma = self.wyrd.mimir.state.total_karma
            except AttributeError:
                context.karma = 0.0

        # Add Yggdrasil cognition system memories if available
        if self.yggdrasil:
            try:
                # Prepare context for cognition system
                cognition_context = {
                    "player_character": game_state.get("player_character"),
                    "location_name": game_state.get("current_location_name", ""),
                    "location_description": game_state.get("location_description", ""),
                    "chaos_factor": game_state.get("chaos_factor", 30),
                    "time_of_day": game_state.get("time_of_day", "day"),
                    "weather": game_state.get("weather", "clear"),
                    "recent_events": context.recent_events,
                    "involved_characters": involved_npcs or [],
                }

                # Get enhanced context with relevant memories
                enhanced_context = self.yggdrasil.analyze_context_for_ai(
                    cognition_context
                )

                # Add relevant memories to context
                if "relevant_memories" in enhanced_context:
                    memory_summaries = []
                    for memory in enhanced_context["relevant_memories"]:
                        summary = f"[{memory.get('domain', 'unknown')}] {memory.get('content', '')[:200]}..."
                        if memory.get("cross_domain", False):
                            summary += f" (Linked from {memory.get('source_domain', 'unknown')})"
                        memory_summaries.append(summary)

                    # Add to recent events (they're relevant memories)
                    if not isinstance(getattr(context, "recent_events", None), list):
                        context.recent_events = []
                    context.recent_events.extend(memory_summaries[:5])

                    # Store memory stats for logging
                    context.memory_stats = enhanced_context.get("memory_stats", {})

                    logger.info(
                        f"Yggdrasil cognition retrieved {len(enhanced_context['relevant_memories'])} memories"
                    )

            except Exception as e:
                logger.error(f"Error retrieving Yggdrasil memories: {e}")

        # Add any dice results from additional context
        if additional_context and "dice_results" in additional_context:
            context.dice_results = additional_context["dice_results"]

        # ── SRD condition + weapon enrichment ─────────────────────────────
        try:
            pc_raw = game_state.get("player_character") or {}
            if isinstance(pc_raw, dict):
                pc_dnd5e = pc_raw.get("dnd5e", {}) if isinstance(pc_raw.get("dnd5e"), dict) else {}
                pc_status = pc_raw.get("status", {}) if isinstance(pc_raw.get("status"), dict) else {}
                pc_conditions = pc_status.get("conditions") or pc_dnd5e.get("conditions") or []
                if isinstance(pc_conditions, str):
                    pc_conditions = [pc_conditions]
                pc_exhaustion = int(pc_dnd5e.get("exhaustion", 0) or 0)
                cs = _get_conditions_system()
                if (pc_conditions or pc_exhaustion) and cs is not None:
                    block = cs.apply_condition_modifiers(pc_conditions, exhaustion_level=pc_exhaustion)
                    cond_notes: List[str] = []
                    if not block.can_take_actions:
                        cond_notes.append("no actions")
                    if not block.can_move:
                        cond_notes.append("no movement")
                    if block.attack_disadvantage:
                        cond_notes.append("attack disadvantage")
                    if block.attack_advantage:
                        cond_notes.append("attack advantage")
                    if block.save_auto_fail_str_dex:
                        cond_notes.append("auto-fail STR/DEX saves")
                    if block.auto_crit_melee:
                        cond_notes.append("incoming melee = auto-crit")
                    if block.speed_halved:
                        cond_notes.append("speed halved")
                    if block.speed_zero:
                        cond_notes.append("speed 0")
                    if cond_notes and hasattr(context, "recent_events") and isinstance(context.recent_events, list):
                        context.recent_events.append(
                            f"[SRD CONDITION MECHANICS] {', '.join(pc_conditions)}: {'; '.join(cond_notes)}"
                        )
                # Primary weapon SRD profile
                re = _get_rules_engine()
                if re is not None:
                    equipment = pc_dnd5e.get("equipment", {})
                    if isinstance(equipment, dict):
                        weapons = equipment.get("weapons", [])
                        if isinstance(weapons, list) and weapons:
                            wp = re.get_weapon_by_name(str(weapons[0]))
                            if wp and hasattr(context, "recent_events") and isinstance(context.recent_events, list):
                                props = ", ".join(wp.properties) if wp.properties else ""
                                context.recent_events.append(
                                    f"[SRD WEAPON] {wp.name}: {wp.damage} {wp.damage_type}"
                                    f"{' (' + props + ')' if props else ''}"
                                )
        except Exception as exc:
            logger.debug("Yggdrasil router SRD enrichment failed: %s", exc)

        return context

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
        Route an AI call through Yggdrasil.

        This is the ONLY method that should call the LLM.
        """
        start_time = time.time()
        self.call_count += 1

        # Alfheim routing hint — lightweight heuristic pre-pass on the prompt
        if self.alfheim and prompt:
            try:
                _route_hint = self.alfheim.route_node_type(prompt)
                logger.debug("Alfheim routing hint for call_type=%s: %s", call_type, _route_hint)
            except Exception:
                pass  # Non-critical; routing continues normally

        # Asgard decomposition — flag complex multi-step prompts for logging/future dispatch
        if self.asgard and prompt:
            try:
                _complexity = self.asgard.estimate_complexity(prompt)
                if _complexity >= 2:
                    _decomp = self.asgard.decompose_query(prompt)
                    logger.debug(
                        "Asgard decomposed complex prompt (complexity=%d, branches=%s)",
                        _complexity,
                        _decomp.get("branches", [])[:3],
                    )
            except Exception:
                pass  # Non-critical; routing continues normally

        # Prepare full context
        context = self.prepare_context(
            call_type=call_type,
            game_state=game_state,
            involved_npcs=involved_npcs,
            additional_context=additional_context,
        )

        # Build prompts
        if use_prompt_builder and self.prompt_builder and context.game_context:
            full_system, full_prompt = self._build_with_prompt_builder(
                call_type, context, prompt, system_prompt
            )
        else:
            full_system = self._build_system_prompt(call_type, context, system_prompt)
            full_prompt = self._build_full_prompt(prompt, context)

        # T3-A: prepend State of the Game block (MEMO / Context Optimizer)
        full_prompt = self.context_optimizer.prepend_sotg(full_prompt, game_state)

        # T3-A: validate NPC identity isolation (LDP) — strip nested tags, log violations
        full_prompt, _violations = validate_identity_isolation(full_prompt, strip_violations=True)

        # Log the call
        if self.comp_logger:
            self.comp_logger.log_ai_call(
                realm=f"yggdrasil_{call_type.value}",
                call_type=call_type.value,
                prompt=full_prompt,
                response="[pending]",
                context={"type": call_type.value, "turn": context.turn_number},
                characters=[c.name for c in context.involved_characters],
                data_sources=["character_sheets", "social_protocols", "wyrd", "memory"],
                data_path=["YggdrasilRouter", call_type.value],
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
                    data_path=["YggdrasilRouter", call_type.value, "complete"],
                )

            logger.info(f"[AI:{call_type.value}] Completed in {elapsed:.2f}s")

            # Store the AI response in Yggdrasil cognition system
            self._store_ai_response_in_memory(
                call_type, prompt, response, context, game_state
            )

            return response

        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"AI call failed: {e}")

            if self.comp_logger:
                self.comp_logger.log_error(e, f"YggdrasilRouter.{call_type.value}")

            return f"[AI Error: {e}]"

    def _build_system_prompt(
        self, call_type: AICallType, context: AICallContext, custom_system: str = None
    ) -> str:
        """Build the complete system prompt."""
        sections = []

        # Base instruction
        sections.append("You are the Game Master for a Norse Viking saga RPG.")
        sections.append("Your responses must be authentic to 9th century Scandinavia.")

        # Call type specific instructions
        type_instructions = {
            AICallType.DIALOGUE: "Generate in-character dialogue for the NPC. Use their personality traits and current mood.",
            AICallType.NARRATION: "Describe the scene vividly with sensory details. Keep the Norse atmosphere.",
            AICallType.COMBAT: "Narrate the combat dramatically. Include the dice results in the narrative.",
            AICallType.PLANNING: "Analyze the situation and provide strategic options.",
            AICallType.MEMORY: "Summarize the events accurately with specific details.",
            AICallType.ANALYSIS: "Analyze the current situation and identify key elements.",
            AICallType.CREATION: "Create a new character/item/location fitting the Norse setting.",
            AICallType.REACTION: "Generate appropriate NPC reactions based on their personality.",
            AICallType.SUMMARY: "Format your response as strict JSON. Do not include markdown formatting or prose. Output only raw data fields.",
            AICallType.PROPHECY: "Speak in mysterious, prophetic terms appropriate to a völva.",
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

    def _build_with_prompt_builder(
        self,
        call_type: AICallType,
        context: AICallContext,
        user_prompt: str,
        custom_system: str = None,
    ) -> tuple[str, str]:
        """Build prompts using prompt_builder.

        CRITICAL FIX (v8.0.0): The custom_system parameter now contains the
        FULL, ALREADY-BUILT system prompt from the engine (including config
        AI prompts, myth engine context, memory, dead characters, etc.).
        We use it directly instead of rebuilding and losing all that context.
        """
        try:
            # Use the custom_system as the base (it contains the engine's full prompt)
            if custom_system:
                system_prompt = custom_system
            else:
                # Only build from scratch if no custom system provided
                system_prompt = self._build_system_prompt(call_type, context, None)

            # Add Yggdrasil-specific context if enabled and not already included
            if context.include_yggdrasil and hasattr(
                self.prompt_builder, "build_yggdrasil_context"
            ):
                ygg_context = self.prompt_builder.build_yggdrasil_context(
                    context.game_context
                )
                if ygg_context and ygg_context not in system_prompt:
                    system_prompt += "\n\n" + ygg_context

            # Build the user prompt with context
            user_prompt_enhanced = (
                context.to_prompt_context() + "\n\n=== YOUR TASK ===\n" + user_prompt
            )

            return system_prompt, user_prompt_enhanced

        except Exception as e:
            logger.error(f"Error building prompt with prompt_builder: {e}")
            # Fall back to basic prompt building
            return self._build_system_prompt(
                call_type, context, custom_system
            ), self._build_full_prompt(user_prompt, context)

    def _build_full_prompt(self, prompt: str, context: AICallContext) -> str:
        """Build the complete user prompt with context."""
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

    def route(
        self,
        messages: List,
        call_type: AICallType,
        game_state: Dict = None,
        use_prompt_builder: bool = False,
        prompt_builder=None,
        yggdrasil_cognition=None,
    ):
        """
        Route method compatible with engine's expected interface.

        Converts messages list to prompt string and calls route_call().
        Returns a CompletionResponse-like object with .content attribute.

        Args:
            messages: List of Message objects with role/content
            call_type: AICallType enum
            game_state: Current game state dictionary
            use_prompt_builder: Whether to use prompt builder
            prompt_builder: Prompt builder instance
            yggdrasil_cognition: Yggdrasil cognition instance

        Returns:
            Object with .content attribute containing AI response
        """
        # Extract prompt and system prompt from messages
        user_prompt = ""
        system_prompt = ""

        for msg in messages:
            if msg.role == "user":
                user_prompt = msg.content
                break  # Take first user message as prompt

        # Extract system prompt from messages
        system_messages = [msg.content for msg in messages if msg.role == "system"]
        if system_messages:
            system_prompt = "\n\n".join(system_messages)

        # If no user prompt found, use a default
        if not user_prompt:
            user_prompt = "Continue the saga."

        # Call route_call with converted parameters
        response_content = self.route_call(
            call_type=call_type,
            prompt=user_prompt,
            game_state=game_state or {},
            system_prompt=system_prompt if system_prompt else None,
            use_prompt_builder=use_prompt_builder,
            additional_context={
                "prompt_builder": prompt_builder,
                "yggdrasil_cognition": yggdrasil_cognition,
            },
        )

        # Return a CompletionResponse-like object
        class RouterResponse:
            def __init__(self, content):
                self.content = content
                self.model = "yggdrasil_router"
                self.usage = {"total_tokens": 0}
                self.finish_reason = "stop"
                self.raw_response = {}

        return RouterResponse(response_content)

    def _store_ai_response_in_memory(
        self,
        call_type: AICallType,
        prompt: str,
        response: str,
        context: AICallContext,
        game_state: Dict,
    ):
        """
        Store AI response in Yggdrasil cognition system memory.

        Args:
            call_type: Type of AI call
            prompt: Original prompt
            response: AI response
            context: AI call context
            game_state: Current game state
        """
        if not self.yggdrasil:
            return

        try:
            # Prepare context for memory storage
            memory_context = {
                "player_character": game_state.get("player_character"),
                "location_name": context.location_name,
                "location_description": context.location_description,
                "chaos_factor": context.chaos_factor,
                "time_of_day": context.time_of_day,
                "weather": context.weather,
                "recent_events": context.recent_events,
                "involved_characters": [
                    c.to_dict() if hasattr(c, "to_dict") else c
                    for c in context.involved_characters
                ]
                if context.involved_characters
                else [],
            }

            # Determine importance based on call type
            importance_map = {
                AICallType.DIALOGUE: 6,
                AICallType.NARRATION: 7,
                AICallType.COMBAT: 8,
                AICallType.PLANNING: 9,
                AICallType.MEMORY: 10,
                AICallType.ANALYSIS: 8,
                AICallType.CREATION: 7,
                AICallType.REACTION: 6,
                AICallType.SUMMARY: 9,
                AICallType.PROPHECY: 8,
            }

            importance = importance_map.get(call_type, 5)

            # Create tags
            tags = [
                f"ai_call_{call_type.value}",
                f"turn_{context.turn_number}",
                f"chaos_{context.chaos_factor}",
            ]

            # Add location tag if available
            if context.location_name:
                location_tag = context.location_name.lower().replace(" ", "_")
                tags.append(f"location_{location_tag}")

            # Add character tags
            if context.player_character:
                pc_name = context.player_character.name.lower().replace(" ", "_")
                tags.append(f"pc_{pc_name}")

            # Store the memory
            if len(response) > 500:
                memory_content = f"AI Response ({call_type.value}): {response[:500]}... [truncated]"
            else:
                memory_content = f"AI Response ({call_type.value}): {response}"

            node_id = self.yggdrasil.store_game_event(
                event_type=call_type.value,
                content=memory_content,
                context=memory_context,
                importance=importance,
                tags=tags,
            )

            if node_id:
                logger.info(f"Stored AI response in Yggdrasil memory (node: {node_id})")

                # Create cross-domain links for this memory
                self.yggdrasil.create_cross_domain_links_for_context(memory_context)

        except Exception as e:
            logger.error(f"Failed to store AI response in memory: {e}")

    def generate_combat_narration(
        self, game_state: Dict, combat_results: List[Dict], npcs: List[Dict]
    ) -> str:
        """Generate combat narration with dice results."""
        prompt = "Narrate this combat round dramatically."
        return self.route_call(
            call_type=AICallType.COMBAT,
            prompt=prompt,
            game_state=game_state,
            involved_npcs=npcs,
            additional_context={"dice_results": combat_results},
        )

    def generate_turn_summary(
        self, game_state: Dict, player_action: str, narrative_result: str
    ) -> str:
        """Generate a turn summary for memory."""
        prompt = f"""Summarize this turn:
Player Action: {player_action}
Result: {narrative_result}

Provide a JSON model response with ONLY: what, why, how, importance (1-10), event_tags, action_log"""

        return self.route_call(
            call_type=AICallType.SUMMARY, prompt=prompt, game_state=game_state
        )


# Factory function
def create_yggdrasil_router(
    llm_callable: Callable[[str, str], str],
    data_path: str = None,
    comprehensive_logger=None,
    wyrd_system=None,
    enhanced_memory=None,
    prompt_builder=None,
    yggdrasil_cognition=None,
) -> YggdrasilAIRouter:
    """Create a Yggdrasil AI router."""
    return YggdrasilAIRouter(
        llm_callable=llm_callable,
        data_path=data_path,
        comprehensive_logger=comprehensive_logger,
        wyrd_system=wyrd_system,
        enhanced_memory=enhanced_memory,
        prompt_builder=prompt_builder,
        yggdrasil_cognition=yggdrasil_cognition,
    )
