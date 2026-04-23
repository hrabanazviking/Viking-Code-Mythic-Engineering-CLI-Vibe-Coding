"""
Yggdrasil Deep Integration Module
==================================

This module provides deep integration between the Yggdrasil cognitive architecture
and the NorseSagaEngine using the DAG-based Contextual Matrix.
"""

import logging
import json
import time
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from datetime import datetime

from yggdrasil.cognition.contracts import (
    PromptSynthesisPayload,
    MetaphysicalState,
    EntityContextNode,
)
from yggdrasil.cognition.gap_analyzer import ContextualGapAnalyzer
from yggdrasil.router_enhanced import (
    AICallType,
    create_enhanced_yggdrasil_router,
)
from systems.rag_system import get_chart_context

logger = logging.getLogger(__name__)


class DeepYggdrasilIntegration:
    """
    Deep integration layer connecting the DAG-based Yggdrasil to NorseSagaEngine.
    """

    def __init__(
        self,
        llm_callable: Callable[[str], str],
        data_path: str,
        engine: Any = None,  # NorseSagaEngine reference
    ):
        """
        Initialize the deep integration.

        Args:
            llm_callable: Function to call for AI inference
            data_path: Path to game data
            engine: Optional reference to the game engine
        """
        self.llm = llm_callable
        self.data_path = Path(data_path)
        self.engine = engine
        self.gap_analyzer = ContextualGapAnalyzer(max_recursion_depth=2)

        self.enhanced_router = None
        try:
            self.enhanced_router = create_enhanced_yggdrasil_router(
                llm_callable=self.llm,
                prompt_builder=getattr(engine, "prompt_builder", None),
                data_path=str(self.data_path),
                comprehensive_logger=getattr(engine, "comp_logger", None),
                wyrd_system=getattr(engine, "wyrd_system", None),
                enhanced_memory=getattr(engine, "enhanced_memory", None),
                yggdrasil_cognition=self,
            )
        except Exception as exc:
            logger.warning(
                "Enhanced router wiring failed in DeepYggdrasilIntegration: %s", exc
            )

        # Tracking
        self._total_ai_calls = 0
        self._session_history = []
        self._memory_store = {}
        logger.info("DeepYggdrasilIntegration initialized with DAG Contextual Matrix")

    def execute_turn_cognition(
        self, turn_context: Dict[str, Any]
    ) -> PromptSynthesisPayload:
        """
        Orchestrates the DAG Contextual Matrix for a given turn.

        1. Identifies targets from the turn context.
        2. Retrieves local subgraphs using the Weaver.
        3. Analyzes metadata gaps using the Void Walker.
        4. Synthesizes the final PromptSynthesisPayload.
        """
        logger.info("[YGGDRASIL] Executing DAG Turn Cognition...")

        # 1. Identify targets
        action = turn_context.get("action") or turn_context.get("player_input") or ""
        targets = self._identify_targets(action, turn_context)

        # 2. Retrieve Subgraph (Weaver)
        graph_context: List[EntityContextNode] = []
        weaver = getattr(self.engine, "lore_ingestion", None) if self.engine else None
        if weaver and hasattr(weaver, "extract_subgraph_context"):
            for target in targets:
                try:
                    nodes = weaver.extract_subgraph_context(target, depth=2)
                    graph_context.extend(nodes)
                except Exception as e:
                    logger.warning(
                        f"Failed to extract subgraph for target {target}: {e}"
                    )
        elif targets and self.engine:
            logger.debug(
                "Lore weaver unavailable; skipping subgraph extraction for %d targets.",
                len(targets),
            )

        # Deduplicate and sort by relevance
        unique_nodes = {}
        for node in graph_context:
            if (
                node.entity_name not in unique_nodes
                or node.relevance_score > unique_nodes[node.entity_name].relevance_score
            ):
                unique_nodes[node.entity_name] = node
        graph_context = sorted(
            unique_nodes.values(), key=lambda x: x.relevance_score, reverse=True
        )[:5]

        # 3. Analyze gaps (Void Walker) & Expand DAG
        if graph_context:
            tasks_to_spawn = self.gap_analyzer.evaluate_subgraph(graph_context)
            if tasks_to_spawn:
                # Execute dynamically spawned tasks to fill gaps
                self._execute_dag_tasks(tasks_to_spawn, graph_context)

        # 4. Extract Metaphysical State
        metaphysical_context = self._extract_metaphysical_state(turn_context)

        # 5. Extract Cultural Directives
        cultural_directives = self._extract_cultural_directives(
            turn_context, graph_context
        )

        payload = PromptSynthesisPayload(
            turn_intent=f"Resolve action: {action}",
            metaphysical_context=metaphysical_context,
            graph_context=graph_context,
            cultural_authenticity_directives=cultural_directives,
        )

        logger.info("[YGGDRASIL] DAG Cognition Complete. Synthesized Payload.")
        return payload

    def _identify_targets(self, text: str, context: Dict[str, Any]) -> List[str]:
        """Naively extract potential entity names from the action or context."""
        targets = []
        if context.get("npc"):
            npc = context["npc"]
            name = npc.get("identity", {}).get("name") or npc.get("id")
            if name:
                targets.append(name)
        if context.get("characters_present"):
            for char in context["characters_present"]:
                if isinstance(char, dict):
                    name = (
                        char.get("identity", {}).get("name")
                        or char.get("name")
                        or char.get("id")
                    )
                    if name:
                        targets.append(name)

        # If no explicit targets, use some placeholders or try to extract from text
        if text:
            import re

            words = re.findall(r"\b[A-Z][a-z]{2,}\b", text)
            for word in words:
                if word not in ["The", "I", "He", "She", "It", "They"]:
                    targets.append(word)

        return list(set(targets))

    def _execute_dag_tasks(
        self, tasks: List[Any], graph_context: List[EntityContextNode]
    ):
        """Execute tasks generated by the gap analyzer."""
        for task in tasks:
            if not getattr(task, "prompt", None):
                continue
            try:
                # Execute LLM to resolve the gap
                self._total_ai_calls += 1
                response = self.llm(task.prompt)

                # Parse the response (expected JSON)
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    data = json.loads(response[json_start:json_end])

                    # Attach the deduced causal link to the relevant node
                    target_entity = getattr(task, "args", {}).get(
                        "target_entity", "unknown"
                    )

                    rel_type = data.get("relationship_type", "deduced_metadata")
                    source_ent = data.get("source_entity", "DAG_Synthesis")
                    hist_ctx = data.get(
                        "historical_context", response[json_start:json_end]
                    )

                    for node in graph_context:
                        if node.entity_name == target_entity:
                            from yggdrasil.cognition.contracts import CausalLink

                            link = CausalLink(
                                source_entity=source_ent,
                                target_entity=target_entity,
                                relationship_type=rel_type,
                                historical_context=hist_ctx,
                                temporal_weight=1.0,
                            )
                            node.causal_links.append(link)

                            # SYSTEMIC CAUSALITY FEEDBACK LOOP
                            if self.engine:
                                # 1. Anchor to Wyrd Tethers (Ancestral Debt, Blood Oath)
                                if getattr(self.engine, "wyrd_tethers", None):
                                    if rel_type == "ancestral_debt":
                                        self.engine.wyrd_tethers.register_debt(
                                            holder_id=source_ent,
                                            counterpart_id=target_entity,
                                            debt_type="DAG_Deduced_Debt",
                                            description=hist_ctx,
                                            generation=2,
                                        )
                                        logger.info(
                                            f"[SYSTEMIC CAUSALITY] Registered deduced Ancestral Debt between {source_ent} and {target_entity}."
                                        )
                                    elif rel_type == "blood_oath":
                                        self.engine.wyrd_tethers.register_oath(
                                            swearer_id=source_ent,
                                            witness_id=target_entity,
                                            terms=hist_ctx,
                                            turn=getattr(
                                                self.engine, "current_turn", 0
                                            ),
                                            hamingja_penalty=0.5,
                                        )
                                        logger.info(
                                            f"[SYSTEMIC CAUSALITY] Registered deduced Blood Oath between {source_ent} and {target_entity}."
                                        )

                                # 2. Anchor to Wyrd System (Urd Well)
                                if getattr(self.engine, "wyrd_system", None):
                                    if rel_type in ["associated_rune", "wyrd_thread"]:
                                        if hasattr(self.engine.wyrd_system, "urd_well"):
                                            # Create a valid WyrdThread and inject into the past (Urd)
                                            from systems.wyrd_system import (
                                                WyrdThread,
                                                WyrdType,
                                            )
                                            from uuid import uuid4
                                            from datetime import datetime

                                            new_thread = WyrdThread(
                                                id=uuid4().hex[:8],
                                                thread_type=WyrdType.REVELATION,
                                                content=hist_ctx,
                                                characters_involved=[target_entity],
                                                location="DAG_Synthesis",
                                                turn_number=getattr(
                                                    self.engine, "current_turn", 0
                                                ),
                                                timestamp=datetime.now().isoformat(),
                                            )
                                            self.engine.wyrd_system.urd_well.record(
                                                new_thread
                                            )
                                            logger.info(
                                                f"[SYSTEMIC CAUSALITY] Registered deduced Wyrd Thread '{rel_type}' in Urd's Well."
                                            )
            except Exception as e:
                logger.warning(
                    f"[VOID WALKER] Failed to execute task {getattr(task, 'id', 'unknown')}: {e}"
                )

    def _extract_metaphysical_state(self, context: Dict[str, Any]) -> MetaphysicalState:
        """Extracts wyrd, runes, and chaos from the game state."""
        runes = []
        threads = []
        chaos = 0.0
        alignment = "Midgard"

        if self.engine:
            if hasattr(self.engine, "wyrd_system") and self.engine.wyrd_system:
                threads = [
                    t.get("name", "Fate")
                    for t in getattr(
                        self.engine.wyrd_system, "get_active_threads", lambda: []
                    )()
                ][:3]
            if hasattr(self.engine, "cosmic_cycle") and self.engine.cosmic_cycle:
                ecosystem = getattr(self.engine.cosmic_cycle, "get_state", lambda: {})()
                chaos = (
                    ecosystem.get("chaos_tension", 0.0) / 100.0
                    if "chaos_tension" in ecosystem
                    else 0.0
                )
                alignment = ecosystem.get("dominant_realm", "Midgard")

        return MetaphysicalState(
            active_runes=runes,
            wyrd_threads=threads,
            chaos_modifier=chaos,
            cosmological_alignment=alignment,
        )

    def _extract_cultural_directives(
        self, context: Dict[str, Any], graph_context: List[EntityContextNode]
    ) -> List[str]:
        directives = [
            "Use historically authentic 9th century Norse speech.",
            "Avoid modern anachronisms and psychologized dialogue.",
        ]

        # Inject social ledgers directly to avoid expensive lookups
        ledger_info = []
        for node in graph_context:
            if getattr(node, "social_ledger_summary", None):
                ledger_info.append(
                    f"{node.entity_name} Ledger: {node.social_ledger_summary}"
                )

        if ledger_info:
            directives.append(
                "Acknowledge honor debts and social ledger implications:\n"
                + "\n".join(ledger_info)
            )

        return directives

    def process_full_pipeline(self, query: str, game_context: Dict[str, Any]) -> Any:
        """Process through DAG matrix and route call."""
        # 1. Get DAG Data
        turn_context = {"action": query, **game_context}
        payload = self.execute_turn_cognition(turn_context)

        # 2. Add Payload to Context and call Router
        additional_context = {"dag_payload": payload}

        class DummySession:
            def __init__(self, output: str, time_taken: float):
                self.final_output = output
                self.success = True
                self.total_time = time_taken

        start_t = time.time()

        if self.enhanced_router:
            logger.info(
                "Routing process_full_pipeline via enhanced_router with DAG Payload"
            )
            final_response = self.enhanced_router.route_call(
                call_type=AICallType.NARRATION,
                prompt=f"Narrate: {query}",
                game_state=game_context,
                additional_context=additional_context,
                use_prompt_builder=True,
            )
        else:
            final_response = "The gods are silent. Yggdrasil router missing."

        return DummySession(final_response, time.time() - start_t)

    def process_dialogue(
        self,
        npc_id: str,
        npc_data: Dict[str, Any],
        player_input: str,
        conversation_history: List[Dict] = None,
        game_context: Dict[str, Any] = None,
    ) -> str:
        """Fallback for process_dialogue."""
        turn_context = {
            "action": player_input,
            "npc": npc_data,
            "game_state": game_context or {},
        }
        payload = self.execute_turn_cognition(turn_context)
        additional_context = {"dag_payload": payload}

        if self.enhanced_router:
            prompt = f"The player says: '{player_input}'. Generate {npc_data.get('identity', {}).get('name', 'the NPC')}'s response."
            return self.enhanced_router.route_call(
                call_type=AICallType.DIALOGUE,
                prompt=prompt,
                game_state=game_context or {},
                involved_npcs=[npc_data],
                additional_context=additional_context,
                use_prompt_builder=True,
            )
        return "..."

    def process_action(
        self,
        action: str,
        game_state: Dict[str, Any],
        characters_present: List[Dict] = None,
    ) -> str:
        """Fallback for process_action."""
        turn_context = {
            "action": action,
            "characters_present": characters_present or [],
            "game_state": game_state,
        }
        payload = self.execute_turn_cognition(turn_context)
        additional_context = {"dag_payload": payload}

        if self.enhanced_router:
            return self.enhanced_router.route_call(
                call_type=AICallType.NARRATION,
                prompt=f"Narrate player action: {action}",
                game_state=game_state,
                involved_npcs=characters_present,
                additional_context=additional_context,
                use_prompt_builder=True,
            )
        return "Your action has no apparent effect."

    def store_character_memory(
        self,
        character_id: str,
        memory_content: str,
        memory_type: str = "experience",
        importance: int = 5,
        **metadata: Any,
    ) -> Optional[str]:
        """Compatibility API for prompt builder and legacy callers."""
        try:
            # Muninn preserves the thread in a local branch when full memory roots are absent.
            memory_id = f"{character_id}:{int(time.time() * 1000)}"
            memory_entry = {
                "id": memory_id,
                "content": memory_content,
                "type": memory_type,
                "importance": importance,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
            }
            self._memory_store.setdefault(character_id, []).append(memory_entry)
            self._memory_store[character_id] = self._memory_store[character_id][-100:]
            return memory_id
        except Exception as exc:
            logger.warning("Failed to store character memory for %s: %s", character_id, exc)
            return None

    def recall_character_memories(
        self,
        character_id: str,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """Compatibility API expected by ai.prompt_builder."""
        try:
            memories = self._memory_store.get(character_id, [])
            filtered = memories
            if memory_type:
                filtered = [m for m in filtered if m.get("type") == memory_type]
            if query:
                q = query.lower()
                filtered = [m for m in filtered if q in m.get("content", "").lower()]
            ranked = sorted(filtered, key=lambda m: m.get("importance", 0), reverse=True)
            return [m.get("content", "") for m in ranked[: max(limit, 0)] if m.get("content")]
        except Exception as exc:
            logger.warning("Failed to recall character memories for %s: %s", character_id, exc)
            return []

    def query_world_knowledge(
        self, query: str, category: Optional[str] = None, limit: int = 3
    ) -> List[str]:
        """Compatibility API for prompt builder world context retrieval."""
        try:
            chart_context = get_chart_context(query, max_tokens=1200)
            if not chart_context:
                return []
            lines = [line.strip("- ") for line in chart_context.splitlines() if line.strip()]
            if category:
                category_lower = category.lower()
                lines = [line for line in lines if category_lower in line.lower()] or lines
            return lines[: max(limit, 0)]
        except Exception as exc:
            logger.warning("Failed to query world knowledge for '%s': %s", query, exc)
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        return {
            "total_ai_calls": self._total_ai_calls,
            "sessions_processed": len(self._session_history),
            "memories_stored": len(self._memory_store),
        }


# Factory function
def create_deep_integration(
    llm_callable: Callable[[str], str], data_path: str, engine: Any = None
) -> DeepYggdrasilIntegration:
    """Create a deep Yggdrasil integration instance."""
    return DeepYggdrasilIntegration(
        llm_callable=llm_callable, data_path=data_path, engine=engine
    )
