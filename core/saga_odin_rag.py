"""
Saga-Odin RAG System

Implements Retrieval-Augmented Generation for lore channel between Saga and Odin
"""

import numpy as np
from ..yggdrasil_core import tree
from typing import List, Dict, Tuple
from sklearn.metrics.pairwise import cosine_similarity

class LoreMemory:
    """Stores and retrieves lore fragments"""
    def __init__(self):
        self.lore_fragments = []  # List of (text, embedding) tuples
        self.fragment_metadata = []  # List of metadata dicts
        
    def add_fragment(self, text: str, embedding: np.ndarray, metadata: Dict):
        """Store a new lore fragment"""
        self.lore_fragments.append((text, embedding))
        self.fragment_metadata.append(metadata)
        
    def retrieve_relevant(self, query_embedding: np.ndarray, top_k: int = 3) -> List[Tuple[str, Dict]]:
        """Retrieve top_k most relevant lore fragments"""
        if not self.lore_fragments:
            return []
            
        # Calculate similarities
        embeddings = np.array([emb for _, emb in self.lore_fragments])
        similarities = cosine_similarity([query_embedding], embeddings)[0]
        
        # Get top indices
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        return [
            (self.lore_fragments[i][0], self.fragment_metadata[i])
            for i in top_indices
        ]

class SagaOdinRAG:
    """Handles RAG-based communication between Saga and Odin"""

    # SRD condition lore fragments injected when the query references combat/conditions
    _SRD_CONDITION_LORE: Dict[str, str] = {
        "blinded":       "Blinded: attacks at disadvantage; attackers have advantage against you; cannot see.",
        "charmed":       "Charmed: cannot attack charmer; charmer has advantage on social checks.",
        "frightened":    "Frightened: disadvantage on attacks and ability checks; cannot move toward source of fear.",
        "grappled":      "Grappled: speed becomes 0.",
        "incapacitated": "Incapacitated: cannot take actions or reactions.",
        "invisible":     "Invisible: unseen; attacks at advantage; attacks against at disadvantage.",
        "paralyzed":     "Paralyzed: incapacitated; auto-fail STR/DEX saves; attacks against have advantage; melee hits are critical.",
        "petrified":     "Petrified: transformed to stone; incapacitated; auto-fail STR/DEX saves; resistance to all damage.",
        "poisoned":      "Poisoned: attacks and ability checks at disadvantage.",
        "prone":         "Prone: melee attacks against have advantage; ranged attacks have disadvantage; movement costs double.",
        "restrained":    "Restrained: speed 0; attacks at disadvantage; attackers have advantage; DEX saves at disadvantage.",
        "stunned":       "Stunned: incapacitated; auto-fail STR/DEX saves; attackers have advantage.",
        "unconscious":   "Unconscious: incapacitated; auto-fail STR/DEX saves; attackers have advantage; melee hits are critical; falls prone.",
        "exhaustion":    "Exhaustion level 1-6: 1=ability check disadvantage, 2=half speed, 3=attack/save disadvantage, 4=half max HP, 5=speed 0, 6=death.",
        "deafened":      "Deafened: cannot hear; auto-fail hearing-based checks.",
        "death saving":  "Death saves: 3 successes = stable; 3 failures = dead; nat 1 = 2 failures; nat 20 = regain 1 HP.",
    }

    def __init__(self, lore_memory: LoreMemory):
        self.lore_memory = lore_memory

    def _inject_srd_lore(self, query: str) -> str:
        """Return SRD condition/combat lore snippets relevant to *query*.

        Only injects when the query mentions specific SRD terms. Returns an
        empty string when no relevant SRD lore is found.
        """
        query_lower = query.lower()
        matched: List[str] = []
        for term, lore in self._SRD_CONDITION_LORE.items():
            if term in query_lower:
                matched.append(lore)
        return "\n".join(matched)

    def generate_response(self, query: str, query_embedding: np.ndarray) -> str:
        """Generate response using RAG pipeline with SRD lore injection."""
        # Retrieve relevant lore
        relevant_fragments = self.lore_memory.retrieve_relevant(query_embedding)

        # Build context from retrieved fragments
        lore_context = "\n\n".join([f"* {text}" for text, _ in relevant_fragments])

        # Inject SRD condition lore if query is combat/condition related
        srd_lore = self._inject_srd_lore(query)
        if srd_lore:
            lore_context = f"[SRD Mechanics]\n{srd_lore}\n\n{lore_context}".strip()

        prompt = (
            f"Saga-Odin RAG Context:\n{lore_context}\n\nQuery: {query}"
            if lore_context
            else f"Query: {query}"
        )
        response = tree.call_oracle(
            prompt=prompt,
            system_msg="You are Odin's memory, answer using Norse lore and runic wisdom",
            model=tree.config.get("RAG_MODEL", "anthropic/claude-3-opus")
        )
        return response

    def process_message(self, message: Dict) -> Dict:
        """Process incoming message from Saga-Odin channel"""
        msg_type = message.get("type") if isinstance(message, dict) else None
        if msg_type == "lore_query":
            content = message.get("content") or {}
            query = content.get("query", "") if isinstance(content, dict) else ""
            raw_embedding = content.get("embedding") if isinstance(content, dict) else None
            if not query or raw_embedding is None:
                return {"type": "error", "content": "lore_query missing query or embedding"}
            response = self.generate_response(query, np.array(raw_embedding))
            return {"type": "lore_response", "content": response}

        return {"type": "unhandled_message", "content": message}