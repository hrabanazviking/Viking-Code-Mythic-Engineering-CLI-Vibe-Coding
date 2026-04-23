"""
Data Contracts for the Yggdrasil Cognitive Architecture
=========================================================

This module defines the strict Pydantic schemas used to pass contextual
data between the DAG-based knowledge matrix and the LLM Prompt Builder.
"""

from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class MetaphysicalState(BaseModel):
    """
    Captures the deeper forces at play (Wyrd, Fate, Chaos) extracted from the graph,
    ensuring the AI looks at the situation from a broader spiritual and cosmic perspective.
    """

    active_runes: List[str] = Field(
        description="Runic omens currently active in the world state"
    )
    wyrd_threads: List[str] = Field(
        description="Active fate threads pulling on the characters"
    )
    chaos_modifier: float = Field(
        description="Current environmental chaos level (0.0 to 1.0)"
    )
    cosmological_alignment: str = Field(
        description="Which of the Nine Realms is currently exerting the most influence"
    )


class CausalLink(BaseModel):
    """
    Replaces standard RAG chunks mapping how a current event connects to history,
    social debts, and quest prerequisites (aligning with Epic C: Quest Causality Graph & NPC Social Ledger).
    """

    source_entity: str = Field(description="The NPC, item, or location")
    target_entity: str = Field(description="What it connects to")
    relationship_type: str = Field(
        description="e.g., 'blood_debt', 'historical_alliance', 'quest_prerequisite'"
    )
    historical_context: str = Field(
        description="Macro-level historical or sociological reasoning for this link"
    )


class EntityContextNode(BaseModel):
    """
    A specific node representing an entity and all its causal ties pulled from the Graph Weaver.
    """

    entity_name: str
    relevance_score: float = Field(
        description="Scored by recency, emotional resonance, and entity overlap"
    )
    causal_links: List[CausalLink]
    social_ledger_summary: Optional[Dict[str, int]] = Field(
        description="Honor, debt, and gift economy metrics cross-referenced from systems/social_ledger.py",
        default_factory=dict,
    )
    raw_content: Optional[str] = Field(
        description="The underlying raw data/lore associated with this entity",
        default="",
    )


class PromptSynthesisPayload(BaseModel):
    """
    The ultimate payload that the DAG hands over to ai/prompt_builder.py.
    This acts as the 'hidden state-intent payload' demanded by FEAT-002.
    """

    turn_intent: str = Field(
        description="The mechanical and narrative goal of the upcoming turn"
    )
    metaphysical_context: MetaphysicalState
    graph_context: List[EntityContextNode] = Field(
        description="Top-K highly connected knowledge graph nodes"
    )
    cultural_authenticity_directives: List[str] = Field(
        description="Required kennings, speech styles, and anachronism warnings extracted during synthesis"
    )

    def to_prompt_injection(self) -> str:
        """
        Formats this validated schema into the hidden system prompt block
        that the OpenRouter/Local LLM will consume.
        """
        lines = []
        lines.append("\n=== DAG CONTEXTUAL MATRIX (HIDDEN STATE PAYLOAD) ===")
        lines.append(f"Turn Intent: {self.turn_intent}")

        # Format Metaphysical State
        lines.append("\n[METAPHYSICAL STATE]")
        lines.append(
            f"- Active Runes: {', '.join(self.metaphysical_context.active_runes) if self.metaphysical_context.active_runes else 'None'}"
        )
        lines.append(
            f"- Wyrd Threads: {', '.join(self.metaphysical_context.wyrd_threads) if self.metaphysical_context.wyrd_threads else 'None'}"
        )
        lines.append(f"- Chaos Level: {self.metaphysical_context.chaos_modifier:.2f}")
        lines.append(
            f"- Cosmological Alignment: {self.metaphysical_context.cosmological_alignment}"
        )

        # Format Graph Context
        lines.append("\n[CAUSAL GRAPH & LORE NETWORK]")
        if self.graph_context:
            for node in self.graph_context:
                lines.append(
                    f"\nEntity: {node.entity_name} (Relevance: {node.relevance_score:.2f})"
                )
                if node.raw_content:
                    lines.append(f"  Context: {node.raw_content[:200]}...")
                if node.social_ledger_summary:
                    ledger_strs = [
                        f"{k}: {v}" for k, v in node.social_ledger_summary.items()
                    ]
                    lines.append(f"  Social Ledger: {', '.join(ledger_strs)}")
                if node.causal_links:
                    lines.append("  Causal Links:")
                    for link in node.causal_links:
                        lines.append(
                            f"    -> {link.target_entity} [{link.relationship_type}]"
                        )
                        lines.append(f"       History: {link.historical_context}")
        else:
            lines.append("- No specific graph nodes retrieved.")

        # Format Cultural Directives
        lines.append("\n[CULTURAL AUTHENTICITY DIRECTIVES]")
        if self.cultural_authenticity_directives:
            for directive in self.cultural_authenticity_directives:
                lines.append(f"- {directive}")
        else:
            lines.append("- None explicitly required.")

        lines.append("==================================================\n")
        return "\n".join(lines)
