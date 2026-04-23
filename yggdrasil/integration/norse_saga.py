"""
NorseSagaEngine Integration
===========================

Integration layer connecting Yggdrasil cognitive architecture
with the Norse Saga Engine game systems.

This module provides game-specific interfaces for:
- Character memory and knowledge
- World state management
- NPC dialogue generation
- Quest and event processing
- Combat decision making

Uses the new hierarchical memory system with Huginn advanced retrieval
and Muninn memory storage.
"""

import logging
import json
import csv
import importlib
import importlib.util
import re
from typing import Dict, List, Any, Optional, Callable, Tuple
from pathlib import Path
from datetime import datetime

import yaml

from yggdrasil.cognition_integration import YggdrasilCognitionSystem
from yggdrasil.cognition import NodeDomain, MemoryType

logger = logging.getLogger(__name__)


class NorseSagaCognition:
    """
    Game-specific cognitive system for Norse Saga Engine.
    
    Provides high-level interfaces for:
    - Character memories and personalities
    - World knowledge and lore
    - Dialogue generation with context
    - Quest and event processing
    - Combat AI decisions
    """
    
    def __init__(
        self,
        llm_callable: Callable[[str], str] = None,
        data_path: str = None,
        game_world: str = "midgard"
    ):
        """
        Initialize the Norse Saga cognition system.
        
        Args:
            llm_callable: Function to call for LLM inference
            data_path: Path for persistent data
            game_world: Name of the game world
        """
        self.game_world = game_world
        self.llm_callable = llm_callable
        
        # Set up data path
        if data_path:
            self.data_path = Path(data_path) / "yggdrasil_data"
            self.data_path.mkdir(parents=True, exist_ok=True)
        else:
            self.data_path = None

        self.charts_path = Path("data") / "charts"
        self._chart_read_failures: Dict[str, int] = {}
        self._chart_knowledge_cache: Dict[str, Dict[str, Any]] = {}
        self.engine = None
        self.deep_integration = None

        def _llm_adapter(prompt: str, *args: Any, **kwargs: Any) -> str:
            try:
                return llm_callable(prompt, *args, **kwargs) if llm_callable else ""
            except TypeError:
                return llm_callable(prompt) if llm_callable else ""

        self._llm_adapter = _llm_adapter

        try:
            from yggdrasil.integration.deep_integration import DeepYggdrasilIntegration
            if llm_callable:
                self.deep_integration = DeepYggdrasilIntegration(
                    llm_callable=self._llm_adapter,
                    data_path=str(Path(data_path or "data")),
                    engine=self.engine,
                )
        except Exception as exc:
            logger.warning("Deep integration unavailable for dialogue cognition: %s", exc)

        # Initialize Yggdrasil Cognition System
        self.cognition_system = YggdrasilCognitionSystem(
            data_path=str(self.data_path) if self.data_path else None
        )
        
        # Convenient aliases
        self.memory_orchestrator = self.cognition_system.memory_orchestrator
        self.memory_tree = self.cognition_system.memory_tree
        self.huginn = self.cognition_system.huginn
        self.crosslinker = self.cognition_system.crosslinker

        # Instantiate Muninn (memory raven) using the same data_path
        try:
            from yggdrasil.ravens.muninn import Muninn
            self.muninn = Muninn(data_path=str(self.data_path) if self.data_path else None)
            logger.debug("NorseSagaCognition: Muninn initialised at %s", self.data_path)
        except Exception as _muninn_exc:
            logger.warning("Muninn unavailable for NorseSagaCognition: %s", _muninn_exc)
            self.muninn = None
        
        # Game state tracking
        self._current_session_id: Optional[str] = None
        self._session_start: Optional[datetime] = None
        
        logger.info(f"NorseSagaCognition initialized for world: {game_world}")
        logger.info(f"Using hierarchical memory system with {len(self.memory_tree.nodes)} nodes")

    def _load_npc_data(self, npc_id: str) -> Dict[str, Any]:
        """Load NPC data from data/characters with resilient fallback."""
        try:
            characters_root = Path("data") / "characters"
            if not characters_root.exists():
                return {}

            for file_path in characters_root.rglob("*.yaml"):
                try:
                    payload = yaml.safe_load(file_path.read_text(encoding="utf-8")) or {}
                    if not isinstance(payload, dict):
                        continue
                    candidate_id = str(payload.get("id") or payload.get("character_id") or "")
                    identity_name = str(payload.get("identity", {}).get("name") or "")
                    if candidate_id == npc_id or identity_name.lower() == npc_id.lower():
                        return payload
                except Exception as file_exc:
                    logger.warning("NPC file parse failed %s: %s", file_path.name, file_exc)
        except Exception as exc:
            logger.warning("Failed to load NPC data for %s: %s", npc_id, exc)
        return {}

    def _derive_knowledge_domains(self, npc_data: Dict[str, Any], player_input: str) -> List[str]:
        """Derive knowledge domains from NPC profile, memories, and user intent."""
        domains: List[str] = []
        try:
            if npc_data:
                # Huginn scouts for explicit domain markers first.
                for key in ("knowledge_domains", "domains", "lore_domains", "specialties", "interests"):
                    value = npc_data.get(key)
                    if isinstance(value, list):
                        domains.extend(str(item) for item in value if item)
                    elif isinstance(value, str):
                        domains.extend(part.strip() for part in value.split(",") if part.strip())

                identity = npc_data.get("identity", {})
                for key in ("occupation", "class", "title", "culture", "homeland"):
                    value = identity.get(key) if isinstance(identity, dict) else npc_data.get(key)
                    if value:
                        domains.append(str(value))

                traits = identity.get("traits") if isinstance(identity, dict) else None
                if isinstance(traits, list):
                    domains.extend(str(t) for t in traits if t)

            memory_hints = self.recall_character_memories(character_id=str(npc_data.get("id", "")), limit=5) if npc_data.get("id") else []
            for memory in memory_hints:
                content = str(memory.get("content", ""))
                domains.extend(re.findall(r"[A-Za-z]{5,}", content))

            player_tokens = re.findall(r"[A-Za-z]{4,}", player_input.lower())
            domains.extend(player_tokens)
        except Exception as exc:
            logger.warning("Failed domain extraction: %s", exc)

        cleaned = sorted({d.strip().lower().replace("_", " ") for d in domains if d and d.strip()})
        return cleaned[:40]

    def _is_myth_request(self, player_input: str) -> bool:
        """Detect myth-recitation intent with robust keyword matching."""
        myth_tokens = {
            "edda", "myth", "mythology", "saga", "voluspa", "odin", "thor", "loki",
            "ragnarok", "asgard", "norns", "fenrir", "yggdrasil", "creation story",
        }
        lowered = player_input.lower()
        return any(token in lowered for token in myth_tokens)

    def _safe_chart_text(self, chart_file: Path) -> str:
        """Read charts with self-healing retries and light parse normalization."""
        key = chart_file.as_posix()
        failures = self._chart_read_failures.get(key, 0)
        if failures > 3:
            return ""

        try:
            suffix = chart_file.suffix.lower()
            raw = chart_file.read_text(encoding="utf-8", errors="ignore")
            if suffix in {".yaml", ".yml"}:
                payload = yaml.safe_load(raw)
                return json.dumps(payload, ensure_ascii=False, default=str)[:50000]
            if suffix == ".json":
                payload = json.loads(raw)
                return json.dumps(payload, ensure_ascii=False, default=str)[:50000]
            if suffix in {".csv", ".cvs"}:
                payload = [row for row in csv.DictReader(raw.splitlines())]
                return json.dumps(payload, ensure_ascii=False, default=str)[:50000]
            if suffix == ".pdf":
                return self._extract_pdf_text(chart_file)[:50000]
            return raw[:50000]
        except Exception as exc:
            self._chart_read_failures[key] = failures + 1
            logger.warning("Chart decode failed (%s) attempt %s: %s", key, failures + 1, exc)
            return ""

    def _score_chart_relevance(self, chart_text: str, domains: List[str], player_input: str) -> int:
        """Score chart relevance against domain and intent tokens."""
        if not chart_text:
            return 0
        text = chart_text.lower()
        score = 0
        for domain in domains:
            if domain and domain in text:
                score += 4
        for token in re.findall(r"[A-Za-z]{4,}", player_input.lower()):
            if token in text:
                score += 2
        if self._is_myth_request(player_input):
            if any(k in text for k in ["poetic_edda", "voluspa", "norse_gods", "ragnarok", "odin"]):
                score += 8
        if any(k in text for k in ["rune", "wyrd", "fate", "dream", "symbol"]):
            score += 3
        return score

    def _extract_chart_knowledge(
        self,
        domains: List[str],
        player_input: str,
        limit: int = 12,
    ) -> List[Dict[str, str]]:
        """Retrieve ranked chart snippets with caching and bug resistance."""
        ranked: List[Dict[str, str]] = []
        if not self.charts_path.exists():
            return ranked

        cache_key = f"{','.join(domains[:10])}|{player_input[:120]}|{limit}"
        if cache_key in self._chart_knowledge_cache:
            return self._chart_knowledge_cache[cache_key].get("results", [])

        for chart_file in self.charts_path.glob("*"):
            if chart_file.suffix.lower() not in {
                ".yaml", ".yml", ".json", ".jsonl", ".md", ".txt", ".csv", ".cvs", ".html", ".htm", ".xml", ".pdf"
            }:
                continue
            text = self._safe_chart_text(chart_file)
            if not text:
                continue

            score = self._score_chart_relevance(text, domains, player_input)
            if score <= 0:
                continue

            ranked.append(
                {
                    "file": chart_file.name,
                    "score": str(score),
                    "snippet": text[:1800],
                }
            )

        ranked.sort(key=lambda item: int(item.get("score", "0")), reverse=True)
        selected = ranked[:limit]
        self._chart_knowledge_cache[cache_key] = {"results": selected}
        return selected

    def _extract_pdf_text(self, chart_file: Path) -> str:
        module_name = "pypdf" if importlib.util.find_spec("pypdf") else "PyPDF2"
        if not importlib.util.find_spec(module_name):
            logger.warning("No PDF reader installed; skipping chart PDF: %s", chart_file)
            return ""
        pdf_module = importlib.import_module(module_name)
        reader = pdf_module.PdfReader(str(chart_file))
        return "\n".join((page.extract_text() or "") for page in reader.pages)

    def _extract_symbolic_signals(self, game_state: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Collect wyrd/rune/dream/symbolic cues from available systems."""
        state = game_state or {}
        symbols: Dict[str, Any] = {
            "active_runes": state.get("active_runes", []),
            "wyrd_threads": state.get("wyrd_threads", []),
            "dream_omens": state.get("dream_omens", []),
            "symbolic_resonance": state.get("symbolic_resonance", []),
        }

        if self.engine and getattr(self.engine, "wyrd_system", None):
            try:
                get_threads = getattr(self.engine.wyrd_system, "get_active_threads", None)
                if callable(get_threads):
                    symbols["wyrd_threads"] = [
                        t.get("name", "fate-thread") for t in get_threads()[:5] if isinstance(t, dict)
                    ]
            except Exception as exc:
                logger.warning("Failed pulling wyrd threads: %s", exc)

        if self.engine and getattr(self.engine, "rune_system", None):
            try:
                recent_draw = getattr(self.engine.rune_system, "last_draw", None)
                if recent_draw:
                    symbols["active_runes"] = [recent_draw]
            except Exception as exc:
                logger.warning("Failed pulling rune state: %s", exc)

        return symbols

    def _build_storytelling_directive(self, npc_data: Dict[str, Any], knowledge_hits: List[Dict[str, str]]) -> str:
        """Craft directive for accurate but personalized myth retelling."""
        try:
            name = npc_data.get("identity", {}).get("name", "The NPC")
            temperament = npc_data.get("identity", {}).get("traits", [])
            temperament_text = ", ".join(str(t) for t in temperament[:4]) if isinstance(temperament, list) else ""
            sources = [hit["file"] for hit in knowledge_hits if "edda" in hit["file"].lower() or "voluspa" in hit["file"].lower()]
            source_text = ", ".join(sources[:5]) if sources else "mythic chart records"
            return (
                f"If myth is requested, let {name} retell Edda-consistent stories using sources [{source_text}]. "
                "Preserve canonical events, divine relationships, and outcomes, but adapt diction and cadence to this NPC's voice. "
                "Never invent gods, realms, or myth outcomes that contradict the source corpus. "
                f"Voice cues: {temperament_text or 'proud, saga-like, and culturally grounded'}"
            )
        except Exception as exc:
            logger.warning("Failed to build storytelling directive: %s", exc)
            return "If myth is requested, retell with canonical accuracy and character voice."

    def _run_dag_dialogue_cognition(
        self,
        npc_id: str,
        npc_data: Dict[str, Any],
        player_input: str,
        game_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute DAG cognition for dialogue context, with graceful fallback."""
        if not self.deep_integration:
            return {}
        try:
            payload = self.deep_integration.execute_turn_cognition(
                {
                    "action": player_input,
                    "npc": npc_data,
                    "game_state": game_context,
                    "characters_present": game_context.get("characters_present", []),
                }
            )
            return {
                "turn_intent": getattr(payload, "turn_intent", ""),
                "metaphysical_context": getattr(payload, "metaphysical_context", {}),
                "graph_context": [
                    getattr(node, "entity_name", "unknown")
                    for node in getattr(payload, "graph_context", [])[:8]
                ],
                "cultural_directives": getattr(payload, "cultural_authenticity_directives", []),
            }
        except Exception as exc:
            logger.warning("DAG dialogue cognition failed for %s: %s", npc_id, exc)
            return {}

    def _validate_dialogue_contract(self, response_text: str, myth_requested: bool) -> Tuple[bool, List[str]]:
        """Validate response quality constraints for self-healing loop."""
        issues: List[str] = []
        if not response_text or len(response_text.strip()) < 20:
            issues.append("response_too_short")
        lowered = response_text.lower()
        if any(token in lowered for token in ["smartphone", "internet", "democracy"]):
            issues.append("anachronism_detected")
        if myth_requested and not any(token in lowered for token in ["odin", "thor", "loki", "norn", "ragnarok", "asgard"]):
            issues.append("myth_request_not_addressed")
        return (len(issues) == 0, issues)

    def _repair_dialogue_output(
        self,
        prompt: str,
        original_response: str,
        issues: List[str],
    ) -> str:
        """Repair invalid dialogue output using corrective pass."""
        if not self.llm_callable:
            return original_response
        try:
            repair_prompt = (
                "Repair the NPC dialogue according to Norse authenticity constraints.\n"
                f"Issues: {issues}\n"
                f"Original response:\n{original_response}\n\n"
                f"Original prompt:\n{prompt}\n\n"
                "Return only corrected in-character NPC speech, no commentary."
            )
            return self._llm_adapter(repair_prompt)
        except Exception as exc:
            logger.warning("Dialogue repair pass failed: %s", exc)
            return original_response


    # ========================================================================
    # SESSION MANAGEMENT
    # ========================================================================
    
    def start_session(self, session_id: str = None) -> str:
        """Start a new game session."""
        self._current_session_id = session_id or f"session_{int(datetime.now().timestamp())}"
        self._session_start = datetime.now()
        
        # Store session start using hierarchical memory system
        self.memory_orchestrator.store_memory(
            content={"session_id": self._current_session_id, "start": self._session_start.isoformat()},
            path=f"sessions/{self._current_session_id}",
            memory_type=MemoryType.EVENT,
            domain=NodeDomain.SYSTEM,
            importance=3,
            metadata={"session_id": self._current_session_id}
        )
        
        logger.info(f"Session started: {self._current_session_id}")
        return self._current_session_id
    
    def end_session(self):
        """End the current game session."""
        if self._current_session_id:
            # Store session end using hierarchical memory system
            self.memory_orchestrator.store_memory(
                content={
                    "session_id": self._current_session_id,
                    "end": datetime.now().isoformat(),
                    "duration": (datetime.now() - self._session_start).total_seconds() if self._session_start else 0,
                },
                path=f"sessions/{self._current_session_id}/end",
                memory_type=MemoryType.EVENT,
                domain=NodeDomain.SYSTEM,
                importance=3,
                metadata={"session_id": self._current_session_id}
            )
            
            # Persist data — memory_orchestrator handles persistence automatically
            
            logger.info(f"Session ended: {self._current_session_id}")
            self._current_session_id = None
            self._session_start = None
    
    # ========================================================================
    # CHARACTER MEMORY
    # ========================================================================
    
    def store_character_memory(
        self,
        character_id: str,
        memory_content: Any,
        memory_type: str = "experience",
        importance: int = 5,
        related_characters: List[str] = None,
        location: str = None
    ) -> str:
        """
        Store a memory for a character.
        
        Args:
            character_id: Character's unique ID
            memory_content: The memory content
            memory_type: Type (experience, interaction, knowledge, emotion)
            importance: 1-10 scale
            related_characters: Other characters involved
            location: Where the memory occurred
            
        Returns:
            Memory node ID
        """
        tags = [character_id, memory_type]
        if related_characters:
            tags.extend(related_characters)
        if location:
            tags.append(location)
        
        # Map memory type to domain
        memory_type_map = {
            "experience": MemoryType.EXPERIENCE,
            "interaction": MemoryType.INTERACTION,
            "knowledge": MemoryType.KNOWLEDGE,
            "emotion": MemoryType.EMOTION,
            "dialogue": MemoryType.DIALOGUE,
            "narration": MemoryType.NARRATIVE,
            "combat": MemoryType.COMBAT,
            "planning": MemoryType.PLANNING,
            "memory": MemoryType.MEMORY,
            "analysis": MemoryType.ANALYSIS,
            "creation": MemoryType.CREATION,
            "reaction": MemoryType.REACTION,
            "summary": MemoryType.SUMMARY,
            "prophecy": MemoryType.PROPHECY
        }
        
        mapped_type = memory_type_map.get(memory_type, MemoryType.GENERAL)
        
        # Prepare context
        context = {
            "character_id": character_id,
            "related_characters": related_characters,
            "location": location,
            "session": self._current_session_id
        }
        
        # Store using hierarchical memory system
        result = self.memory_orchestrator.store_memory(
            content=memory_content,
            path=f"characters/{character_id}/memories",
            memory_type=mapped_type,
            domain=NodeDomain.CHARACTERS,
            importance=importance,
            tags=tags,
            metadata={
                "related_characters": related_characters,
                "location": location,
                "session": self._current_session_id,
                "character_id": character_id
            }
        )
        
        return result.node_id if result.success else None
    
    def recall_character_memories(
        self,
        character_id: str,
        query: str = None,
        memory_type: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Recall memories for a character.
        
        Args:
            character_id: Character's unique ID
            query: Optional search query
            memory_type: Filter by type
            limit: Maximum memories
            
        Returns:
            List of memory dictionaries
        """
        # Prepare context for retrieval
        context = {
            "character_id": character_id,
            "memory_type": memory_type
        }
        
        # Build search query
        search_query = query or f"character {character_id}"
        
        # Use hierarchical memory system
        result = self.memory_orchestrator.retrieve_memory(
            query=search_query,
            max_nodes=limit
        )
        
        if not result.success:
            logger.warning(f"Failed to retrieve memories: {result.error}")
            return []
        
        # Filter by character ID and memory type
        memories = []
        for memory in result.nodes:
            metadata = memory.metadata or {}
            if metadata.get("character_id") == character_id:
                if memory_type and memory.memory_type.value != memory_type:
                    continue
                
                memories.append({
                    "id": memory.id,
                    "content": memory.content,
                    "type": memory.memory_type.value,
                    "importance": memory.importance,
                    "path": memory.path,
                    "tags": memory.tags,
                    "metadata": metadata,
                    "created_at": memory.created_at.isoformat() if memory.created_at else None,
                    "updated_at": memory.updated_at.isoformat() if memory.updated_at else None
                })
        
        return memories[:limit]
    
    def get_character_context(
        self,
        character_id: str,
        situation: str = None,
        include_relationships: bool = True
    ) -> Dict[str, Any]:
        """
        Build comprehensive context for a character.
        
        Args:
            character_id: Character's unique ID
            situation: Current situation description
            include_relationships: Include relationship data
            
        Returns:
            Context dictionary for LLM prompts
        """
        context = {
            "character_id": character_id,
            "memories": [],
            "relationships": [],
            "recent_events": [],
        }
        
        # Get relevant memories using hierarchical system
        if situation:
            # Use Huginn advanced retrieval with situation context
            search_context = {
                "character_id": character_id,
                "situation": situation
            }
            
            result = self.memory_orchestrator.retrieve_memory(
                query=f"{character_id} {situation}",
                max_nodes=10
            )
            
            if result.success:
                for memory in result.nodes:
                    metadata = memory.metadata or {}
                    if metadata.get("character_id") == character_id:
                        context["memories"].append({
                            "id": memory.id,
                            "content": memory.content,
                            "type": memory.memory_type.value,
                            "importance": memory.importance,
                            "created_at": memory.created_at.isoformat() if memory.created_at else None
                        })
        else:
            memories = self.recall_character_memories(character_id, limit=5)
            context["memories"] = memories
        
        # Get relationships if requested
        if include_relationships:
            # Search for relationship memories
            relationship_result = self.memory_orchestrator.search_memories(
                keywords=["relationship", "friend", "enemy", "ally", "rival"],
                operator="OR",
                domain=NodeDomain.CHARACTERS,
                min_importance=3
            )
            
            if relationship_result.success:
                for node in relationship_result.nodes:
                    metadata = node.metadata or {}
                    if metadata.get("character_id") == character_id or character_id in metadata.get("related_characters", []):
                        context["relationships"].append({
                            "id": node.id,
                            "content": node.content,
                            "type": node.memory_type.value,
                            "target": metadata.get("related_characters", [])
                        })
        
        # Get recent events using hierarchical memory system
        event_result = self.memory_orchestrator.search_memories(
            keywords=[character_id, "event"],
            operator="AND"
        )
        if event_result.success:
            context["recent_events"] = [n.content for n in event_result.nodes[:3]]
        
        return context
    
    # ========================================================================
    # NPC DIALOGUE
    # ========================================================================
    
    def generate_dialogue(
        self,
        npc_id: str,
        player_input: str,
        conversation_history: List[Dict] = None,
        situation: str = None
    ) -> Dict[str, Any]:
        """
        Generate NPC dialogue response.
        
        Args:
            npc_id: NPC's character ID
            player_input: What the player said
            conversation_history: Previous exchanges
            situation: Current situation
            
        Returns:
            Dialogue response with metadata
        """
        return self.generate_domain_aware_conversation(
            npc_id=npc_id,
            player_input=player_input,
            conversation_history=conversation_history,
            situation=situation,
        )

    def generate_domain_aware_conversation(
        self,
        npc_id: str,
        player_input: str,
        conversation_history: List[Dict] = None,
        situation: str = None,
        npc_data: Optional[Dict[str, Any]] = None,
        max_knowledge_sources: int = 12,
        game_context: Optional[Dict[str, Any]] = None,
        max_repair_attempts: int = 2,
    ) -> Dict[str, Any]:
        """
        Generate advanced domain-aware NPC dialogue grounded in chart lore.

        The response engine blends:
        - NPC autobiographical memory from Yggdrasil
        - Domain-targeted retrieval from data/charts/
        - Myth-recitation constraints that preserve canonical facts while
          allowing the NPC's personal voice and wording
        """
        try:
            resolved_npc = npc_data or self._load_npc_data(npc_id)
            effective_game_context = game_context or {}
            context = self.get_character_context(npc_id, situation)
            context["npc_profile"] = resolved_npc

            trimmed_history = (conversation_history or [])[-10:]
            context["conversation"] = trimmed_history

            domains = self._derive_knowledge_domains(resolved_npc, player_input)
            myth_requested = self._is_myth_request(player_input)
            knowledge_hits = self._extract_chart_knowledge(domains, player_input, max_knowledge_sources)
            storytelling_directive = self._build_storytelling_directive(resolved_npc, knowledge_hits)
            dag_payload = self._run_dag_dialogue_cognition(
                npc_id=npc_id,
                npc_data=resolved_npc,
                player_input=player_input,
                game_context=effective_game_context,
            )
            symbolic_signals = self._extract_symbolic_signals(effective_game_context)

            prompt = (
                f"You are generating a deep NPC conversation for '{npc_id}'.\n\n"
                f"PLAYER INPUT:\n{player_input}\n\n"
                f"SITUATION:\n{situation or 'No explicit situation provided.'}\n\n"
                f"NPC CONTEXT:\n{json.dumps(context, ensure_ascii=False, default=str)[:7000]}\n\n"
                f"NPC KNOWLEDGE DOMAINS:\n{domains}\n\n"
                f"CHART KNOWLEDGE SOURCES:\n{json.dumps(knowledge_hits, ensure_ascii=False, default=str)[:9000]}\n\n"
                f"DAG COGNITION PAYLOAD:\n{json.dumps(dag_payload, ensure_ascii=False, default=str)[:5000]}\n\n"
                f"METAPHYSICAL SIGNALS (runes, wyrd, dreams, symbols):\n"
                f"{json.dumps(symbolic_signals, ensure_ascii=False, default=str)[:2000]}\n\n"
                "RESPONSE CONTRACT:\n"
                "1) Stay fully in-character and culturally authentic to 9th-century Norse worldview.\n"
                "2) Pull only relevant chart knowledge and weave it naturally into dialogue.\n"
                "3) If reciting myth, keep canonical accuracy while phrasing in NPC's personal speech style.\n"
                "4) Reflect fate-pressure, runic omens, dreams, and symbolic resonance when context supports it.\n"
                "5) Blend memory, social context, and lore naturally; avoid list-like exposition.\n"
                "6) Offer nuanced, layered response that can continue multi-turn dialogue.\n"
                "7) Include one subtle question or hook so the conversation can deepen.\n"
                f"8) {storytelling_directive}\n"
            )

            response_text = ""
            confidence = 0.6

            if self.deep_integration and self.deep_integration.enhanced_router:
                response_text = self.deep_integration.process_dialogue(
                    npc_id=npc_id,
                    npc_data=resolved_npc,
                    player_input=player_input,
                    conversation_history=trimmed_history,
                    game_context={
                        **effective_game_context,
                        "symbolic_signals": symbolic_signals,
                        "dag_payload": dag_payload,
                        "knowledge_sources": [item.get("file") for item in knowledge_hits],
                    },
                )
                confidence = 0.85
                failure_markers = ["gods are silent", "norns cloud", "could not weave", "..."]
                if not response_text or any(marker in response_text.lower() for marker in failure_markers):
                    response_text = self._llm_adapter(prompt) if self.llm_callable else response_text
                    confidence = 0.72
            elif hasattr(self, "world_tree") and self.world_tree:
                result = self.world_tree.process(
                    query=prompt,
                    context={"npc_id": npc_id, "type": "domain_dialogue"},
                    memory_paths=[f"characters/{npc_id}", "world/mythology", "world/culture"],
                )
                response_text = getattr(result, "final_output", "")
                confidence = float(getattr(result, "confidence", confidence) or confidence)
            elif self.llm_callable:
                response_text = self._llm_adapter(prompt)
                confidence = 0.75
            else:
                response_text = (
                    "The NPC studies you in silence, knowledge heavy as winter cloud. "
                    "No voice answers yet; the hall waits for a true skald to speak."
                )

            valid, issues = self._validate_dialogue_contract(response_text, myth_requested)
            attempts = 0
            while not valid and attempts < max_repair_attempts:
                attempts += 1
                response_text = self._repair_dialogue_output(prompt, response_text, issues)
                valid, issues = self._validate_dialogue_contract(response_text, myth_requested)

            self.store_character_memory(
                character_id=npc_id,
                memory_content={
                    "type": "domain_dialogue",
                    "player_said": player_input,
                    "npc_response": response_text,
                    "domains": domains,
                    "knowledge_sources": [item.get("file") for item in knowledge_hits],
                    "myth_requested": myth_requested,
                    "symbolic_signals": symbolic_signals,
                    "dag_payload": dag_payload,
                    "repair_attempts": attempts,
                    "validation_issues": issues if not valid else [],
                },
                memory_type="dialogue",
                importance=6 if myth_requested else 5,
            )

            return {
                "response": response_text,
                "confidence": confidence,
                "npc_id": npc_id,
                "domains": domains,
                "knowledge_sources": [item.get("file") for item in knowledge_hits],
                "myth_requested": myth_requested,
                "symbolic_signals": symbolic_signals,
                "dag_payload": dag_payload,
                "self_healed": attempts > 0,
            }
        except Exception as exc:
            logger.warning("Domain-aware conversation failed for %s: %s", npc_id, exc)
            return {
                "response": "The NPC's words falter, as if the Norns cut the thread mid-sentence.",
                "confidence": 0.0,
                "npc_id": npc_id,
                "domains": [],
                "knowledge_sources": [],
            }
    
    # ========================================================================
    # WORLD KNOWLEDGE
    # ========================================================================
    
    def store_world_fact(
        self,
        fact: Any,
        category: str = "lore",
        location: str = None,
        importance: int = 5
    ) -> str:
        """
        Store a fact about the game world.
        
        Args:
            fact: The fact content
            category: Category (lore, geography, history, rules)
            location: Related location
            importance: 1-10 scale
            
        Returns:
            Fact node ID
        """
        tags = [category]
        if location:
            tags.append(location)
        
        # Store world fact using hierarchical memory system
        result = self.memory_orchestrator.store_memory(
            content=fact,
            path=f"world/{category}",
            memory_type=MemoryType.FACT,
            domain=NodeDomain.WORLD_KNOWLEDGE,
            importance=importance,
            tags=tags,
            metadata={"category": category, "location": location}
        )
        return result.node_id if result.success else None
    
    def query_world_knowledge(
        self,
        query: str,
        category: str = None
    ) -> List[Dict[str, Any]]:
        """
        Query world knowledge.
        
        Args:
            query: Search query
            category: Optional category filter
            
        Returns:
            List of relevant facts
        """
        path = f"world/{category}" if category else "world"
        
        # Retrieve world knowledge using hierarchical memory system
        result = self.memory_orchestrator.search_memories(
            keywords=[query] + ([category] if category else []),
            operator="AND"
        )
        nodes = result.nodes if result.success else []
        
        return [{"content": n.content, "category": n.path.split("/")[-1]} for n in nodes[:5]]
    
    # ========================================================================
    # QUEST AND EVENT PROCESSING
    # ========================================================================
    
    def log_event(
        self,
        event_type: str,
        description: str,
        participants: List[str] = None,
        location: str = None,
        importance: int = 5
    ) -> str:
        """
        Log a game event.
        
        Args:
            event_type: Type of event
            description: Event description
            participants: Characters involved
            location: Where it happened
            importance: 1-10 scale
            
        Returns:
            Event node ID
        """
        tags = [event_type]
        if participants:
            tags.extend(participants)
        if location:
            tags.append(location)
        
        event_data = {
            "type": event_type,
            "description": description,
            "participants": participants,
            "location": location,
            "timestamp": datetime.now().isoformat(),
            "session": self._current_session_id,
        }
        
        return self.muninn.store(
            content=event_data,
            path="events/log",
            memory_type="event",
            importance=importance,
            tags=tags,
        )
    
    def process_quest_update(
        self,
        quest_id: str,
        update_type: str,
        details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a quest update.
        
        Args:
            quest_id: Quest identifier
            update_type: Type of update (start, progress, complete, fail)
            details: Update details
            
        Returns:
            Processing result
        """
        # Store quest state
        self.muninn.store(
            content={
                "quest_id": quest_id,
                "update_type": update_type,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            },
            path=f"quests/{quest_id}",
            memory_type="event",
            importance=6,
            tags=[quest_id, update_type],
        )
        
        # Log as event
        self.log_event(
            event_type=f"quest_{update_type}",
            description=f"Quest {quest_id}: {update_type}",
            participants=details.get("participants"),
            importance=6,
        )
        
        return {"quest_id": quest_id, "status": update_type, "success": True}
    
    # ========================================================================
    # COMBAT AI
    # ========================================================================
    
    def get_combat_decision(
        self,
        combatant_id: str,
        combat_state: Dict[str, Any],
        available_actions: List[str]
    ) -> Dict[str, Any]:
        """
        Get AI decision for combat.
        
        Args:
            combatant_id: The combatant's ID
            combat_state: Current combat state
            available_actions: List of possible actions
            
        Returns:
            Decision with action and reasoning
        """
        # Get combatant context
        context = self.get_character_context(combatant_id, "in combat")
        
        # Build combat prompt
        prompt = f"""Combat decision for {combatant_id}.

Combat State:
{combat_state}

Available Actions:
{available_actions}

Character Context:
{context}

Choose the best action and explain why."""
        
        # Route through llm_callable if available, else default to first action
        output = ""
        if self.llm_callable:
            try:
                output = self.llm_callable(prompt) or ""
            except Exception as exc:
                logger.warning("get_combat_decision llm_callable failed: %s", exc)

        chosen_action = available_actions[0]  # Default
        for action in available_actions:
            if action.lower() in output.lower():
                chosen_action = action
                break

        return {
            "action": chosen_action,
            "reasoning": output,
            "confidence": 0.7 if output else 0.3,
        }
    
    # ========================================================================
    # UTILITY METHODS
    # ========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        # Get hierarchical memory system statistics
        memory_stats = self.cognition_system.get_system_statistics()
        
        return {
            "session_id": self._current_session_id,
            "hierarchical_memory": {
                "total_nodes": memory_stats.get("total_nodes", 0),
                "total_links": memory_stats.get("total_links", 0),
                "domains": len(NodeDomain),
                "memory_types": len(MemoryType),
                "performance": memory_stats.get("performance", {}),
                "domain_connectivity": memory_stats.get("domain_connectivity", {})
            },
            "huginn_performance": memory_stats.get("huginn", {}),
            "memory_tree": memory_stats.get("memory_tree", {})
        }
    
    def persist(self):
        """Persist all data to disk."""
        # Note: The hierarchical memory system persists automatically
        # when nodes are created/updated. This is a no-op for now.
        logger.info("Hierarchical memory system persistence is automatic")
    
    def heal(self) -> Dict[str, int]:
        """Self-healing operation."""
        # Run cross-domain link discovery to heal connections
        links_created = self.crosslinker.discover_all_cross_domain_links(
            min_confidence=0.3,
            max_links_per_node=3
        )
        
        # Analyze memory system
        analysis_result = self.memory_orchestrator.analyze_memory_system()
        
        return {
            "cross_domain_links_created": links_created,
            "memory_analysis_success": analysis_result.success if analysis_result else False,
            "total_nodes": len(self.memory_tree.nodes),
            "total_links": sum(len(node.symbolic_links) for node in self.memory_tree.nodes.values())
        }


# ============================================================================
# FACTORY FUNCTION
# ============================================================================

def create_norse_saga_cognition(
    llm_callable: Callable[[str], str] = None,
    data_path: str = None,
    **kwargs
) -> NorseSagaCognition:
    """
    Factory function to create Norse Saga cognition system.
    
    Args:
        llm_callable: LLM function
        data_path: Data storage path
        **kwargs: Additional configuration
        
    Returns:
        Configured NorseSagaCognition instance
    """
    return NorseSagaCognition(
        llm_callable=llm_callable,
        data_path=data_path,
        **kwargs
    )
