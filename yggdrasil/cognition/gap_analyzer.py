"""
The Void Walker: Autonomous Gap Analysis Engine
===============================================

Evaluates the Knowledge Graph for completeness. If context is missing
(e.g., lacks sociological depth, runic ties, historical anchors), it
dynamically spawns TaskNodes to synthesize the missing dimensions via the LLM.
"""

import logging
import uuid
import json
from typing import List, Optional

from yggdrasil.cognition.contracts import EntityContextNode
from yggdrasil.core.dag import TaskNode, TaskType, RealmAffinity

logger = logging.getLogger(__name__)


class ContextualGapAnalyzer:
    """
    Analyzes an EntityContextNode for heuristic completeness and generates DAG nodes if gaps exist.
    """

    def __init__(self, max_recursion_depth: int = 2):
        """
        Args:
            max_recursion_depth: Maximum number of times the engine can spawn sub-tasks
                                 to prevent philosophical rabbit holes.
        """
        self.max_recursion_depth = max_recursion_depth

        # We track recursion simply by analyzing how many nested generation tags are in the node metadata

    def evaluate_subgraph(
        self, context_nodes: List[EntityContextNode]
    ) -> List[TaskNode]:
        """
        Evaluates a list of retrieved graph nodes against macro-level heuristics.
        Returns a list of dynamically generated TaskNodes to resolve missing context.
        """
        tasks_to_spawn = []

        for index, node in enumerate(context_nodes):
            # Only evaluate top highly-relevant nodes (top 3) to prevent massive DAG bloat
            if index > 2:
                break

            missing_contexts = self._identify_missing_heuristics(node)

            for missing_type in missing_contexts:
                task = self._spawn_generation_task(node, missing_type)
                if task:
                    tasks_to_spawn.append(task)
                    logger.info(
                        f"[VOID WALKER] Identified missing '{missing_type}' context for '{node.entity_name}'. Dynamically appending DAG task {task.id}."
                    )

        return tasks_to_spawn

    def _identify_missing_heuristics(self, node: EntityContextNode) -> List[str]:
        """
        Evaluates a single node against strict heuristics.
        """
        missing = []

        try:
            # Parse the underlying raw node JSON to check specific fields
            raw_data = json.loads(node.raw_content) if node.raw_content else {}
        except json.JSONDecodeError:
            raw_data = {}

        links = node.causal_links

        # 1. Sociological Depth
        # Does the NPC lack a connection to the SocialLedgerEngine (honor/debt/witness events)?
        # If it's an NPC or faction, do they have social links or ledger entries?
        is_npc_or_faction = (
            raw_data.get("type") in ["npc", "character", "faction"]
            or "ideals" in raw_data
        )
        has_social_links = any(
            link.relationship_type
            in ["blood_debt", "honor_oath", "historical_alliance", "blood_feud"]
            for link in links
        )
        if (
            is_npc_or_faction
            and not has_social_links
            and not node.social_ledger_summary
        ):
            missing.append("sociological_depth")

        # 2. Metaphysical / Runic Ties
        # Does a major world event or quest lack a tie to the WyrdSystem or active runic omens?
        is_event_or_quest = (
            raw_data.get("type") in ["quest", "event", "saga_arc"]
            or "prerequisites" in raw_data
        )
        has_runic_ties = any(
            link.relationship_type in ["associated_rune", "wyrd_thread"]
            for link in links
        )
        if is_event_or_quest and not has_runic_ties:
            missing.append("metaphysical_runic_ties")

        # 3. Historical Precedence
        # Does a location or faction lack a macro-level historical anchor?
        is_location_or_faction = (
            raw_data.get("type") in ["location", "subregion", "faction"]
            or "located_in" in raw_data
        )
        has_history = "historical_context" in raw_data or any(
            l.historical_context for l in links
        )
        if is_location_or_faction and not has_history:
            missing.append("historical_precedence")

        # 4. Psychological & Emotional Depth
        # Check for relationship types that graph_weaver actually generates and that
        # indicate social/emotional bonds: feuds, debts, alliances, conflict, recovery.
        _EMOTIONAL_REL_TYPES = {
            "blood_feud", "blood_debt", "historical_alliance",
            "historical_conflict", "alliance", "recovery_path",
        }
        has_emotional_ties = any(
            link.relationship_type in _EMOTIONAL_REL_TYPES
            for link in links
        )
        if is_npc_or_faction and not has_emotional_ties:
            missing.append("psychological_depth")

        # 5. Ancestral Debt & Blood Oath Ties
        # Does an NPC lack dependencies to BloodOath or AncestralDebt?
        has_ancestral_ties = any(
            link.relationship_type in ["ancestral_debt", "blood_oath"] for link in links
        )
        if is_npc_or_faction and not has_ancestral_ties:
            missing.append("ancestral_oath_ties")

        return missing

    def _spawn_generation_task(
        self, target_node: EntityContextNode, missing_context_type: str
    ) -> Optional[TaskNode]:
        """
        Instantiates a TaskNode configured to query the LLM to deduce missing dimensions.
        """
        # Protect against infinite loops by counting existing resolution markers if we embedded them in previous turns
        # In a fully stateful loop, we'd check if target_node has an attribute like "_recursion_depth_reached"
        # For now, we spawn the task and rely on World Tree orchestration limits.

        task_id = f"gen_context_{missing_context_type}_{uuid.uuid4().hex[:6]}"

        # Craft a targeted prompt requesting structured JSON payload addressing the specific gap
        prompts = {
            "sociological_depth": (
                f"Analyze the entity '{target_node.entity_name}' (Raw Data extracts: {target_node.raw_content[:200]}...). "
                f"Deduce implicit sociological connections, blood debts, or honor oaths consistent with Norse values and Epic C structures. "
                "Output JSON strictly matching the CausalLink schema with relationships like 'blood_debt' or 'honor_oath'."
            ),
            "metaphysical_runic_ties": (
                f"Analyze the entity '{target_node.entity_name}' (Raw Data extracts: {target_node.raw_content[:200]}...). "
                f"Deduce underlying metaphysical resonance or runic omens that tie this event to the Wyrd. "
                "Output JSON strictly matching the CausalLink schema with relationship_type 'associated_rune' and historical_context justifying the fate."
            ),
            "historical_precedence": (
                f"Analyze the entity '{target_node.entity_name}' (Raw Data extracts: {target_node.raw_content[:200]}...). "
                f"Deduce a deep historical or mythological precedent for this entity originating from previous mythic ages. "
                "Output JSON strictly matching the CausalLink schema with relationship 'historical_precedent'."
            ),
            "psychological_depth": (
                f"Analyze the entity '{target_node.entity_name}' (Raw Data extracts: {target_node.raw_content[:200]}...). "
                f"Deduce implicit psychological and emotional undercurrents, such as unresolved trauma or hormonal/menstrual phase alignments affecting their mood. "
                "Output JSON strictly matching the CausalLink schema with relationships like 'emotional_state' or 'psychological_trauma'."
            ),
            "ancestral_oath_ties": (
                f"Analyze the entity '{target_node.entity_name}' (Raw Data extracts: {target_node.raw_content[:200]}...). "
                f"Deduce an inherited Ancestral Debt or strict Blood Oath binding this character, transcending normal emotional logic. "
                "Output JSON strictly matching the CausalLink schema with relationship 'ancestral_debt' or 'blood_oath'."
            ),
        }

        system_prompt = (
            "You are The Void Walker. Your purpose is to fill gaps in the Yggdrasil Knowledge Graph. "
            "Return valid JSON matching the exact schema requested, no markdown, no conversational text."
        )

        full_prompt = f"System: {system_prompt}\nTask: {prompts.get(missing_context_type, 'Analyze and fill gaps.')}"

        # We spawn an LLM generation task pointing to Jotunheim or Svartalfheim
        task = TaskNode(
            id=task_id,
            task_type=TaskType.LLM,
            realm=RealmAffinity.SVARTALFHEIM,  # Forging new data
            prompt=full_prompt,
            priority=8,  # High priority as synthesis depends on it
            args={
                "target_entity": target_node.entity_name,
                "missing_type": missing_context_type,
                "expected_schema": "CausalLink",
            },
        )

        return task
