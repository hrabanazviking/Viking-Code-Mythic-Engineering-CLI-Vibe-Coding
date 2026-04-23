#!/usr/bin/env python3
"""
Memory System v3.0 - Robust Multi-Level Memory
===============================================

Implements a three-tier memory system:
1. Short-term: Last 5 turns (full detail)
2. Medium-term: Last 20 turns (summarized)
3. Long-term: Entire session (highly condensed)

Each turn generates AI summaries that feed into memory.
Memory is passed to the AI every turn for context.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional
from datetime import datetime
import logging


logger = logging.getLogger(__name__)


@dataclass
class TurnMemory:
    """Memory of a single turn."""
    turn_number: int
    timestamp: str
    player_action: str
    ai_response_summary: str  # AI-generated summary
    rune_drawn: Optional[str] = None
    rune_influence: Optional[str] = None
    location: str = ""
    sub_location: str = ""
    npcs_involved: List[str] = field(default_factory=list)
    combat_occurred: bool = False
    quest_updates: List[str] = field(default_factory=list)
    reputation_changes: List[str] = field(default_factory=list)
    loyalty_changes: List[str] = field(default_factory=list)
    important_events: List[str] = field(default_factory=list)
    mood_shifts: Dict[str, str] = field(default_factory=dict)  # NPC mood changes
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'TurnMemory':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class SessionMemory:
    """Complete memory for a session."""
    session_id: str
    started: str
    player_character: str
    
    # Three tiers of memory
    short_term: List[TurnMemory] = field(default_factory=list)  # Last 5 turns
    medium_term: List[str] = field(default_factory=list)  # Summaries of turns 6-25
    long_term: List[str] = field(default_factory=list)  # Major events only
    
    # Running narrative summary (updated periodically)
    narrative_summary: str = ""
    
    # Key facts extracted
    key_facts: List[str] = field(default_factory=list)  # Important revelations
    relationships_formed: Dict[str, str] = field(default_factory=dict)  # NPC: relationship
    enemies_made: List[str] = field(default_factory=list)
    allies_gained: List[str] = field(default_factory=list)
    quests_discovered: List[str] = field(default_factory=list)
    locations_discovered: List[str] = field(default_factory=list)
    items_acquired: List[str] = field(default_factory=list)
    
    # Configuration
    short_term_limit: int = 5
    medium_term_limit: int = 20
    
    def add_turn(self, turn: TurnMemory):
        """Add a turn to memory, managing the tiers."""
        self.short_term.append(turn)
        
        # Promote to medium-term if short-term is full
        while len(self.short_term) > self.short_term_limit:
            oldest = self.short_term.pop(0)
            # Create summary for medium-term
            summary = self._summarize_turn(oldest)
            self.medium_term.append(summary)
        
        # Promote to long-term if medium-term is full
        while len(self.medium_term) > self.medium_term_limit:
            oldest_summaries = self.medium_term[:5]
            self.medium_term = self.medium_term[5:]
            # Condense into long-term
            condensed = self._condense_summaries(oldest_summaries)
            self.long_term.append(condensed)
        
        # Extract key facts from turn
        self._extract_facts(turn)
    
    def _summarize_turn(self, turn: TurnMemory) -> str:
        """Create a summary of a single turn for medium-term memory."""
        parts = [f"Turn {turn.turn_number}:"]
        
        if turn.rune_drawn:
            parts.append(f"Rune {turn.rune_drawn} drawn.")
        
        if turn.ai_response_summary:
            parts.append(turn.ai_response_summary)
        
        if turn.important_events:
            parts.append(f"Events: {'; '.join(turn.important_events)}")
        
        if turn.quest_updates:
            parts.append(f"Quests: {'; '.join(turn.quest_updates)}")
        
        return " ".join(parts)
    
    def _condense_summaries(self, summaries: List[str]) -> str:
        """Condense multiple summaries into one long-term entry."""
        return " | ".join(summaries)
    
    def _extract_facts(self, turn: TurnMemory):
        """Extract key facts from a turn."""
        # Add any important events as key facts
        for event in turn.important_events:
            if event not in self.key_facts:
                self.key_facts.append(event)
        
        # Track quest discoveries
        for quest in turn.quest_updates:
            if "discovered" in quest.lower() or "new" in quest.lower():
                if quest not in self.quests_discovered:
                    self.quests_discovered.append(quest)
        
        # Track location discoveries
        if turn.location and turn.location not in self.locations_discovered:
            self.locations_discovered.append(turn.location)
        if turn.sub_location and turn.sub_location not in self.locations_discovered:
            self.locations_discovered.append(turn.sub_location)
    
    def get_context_for_ai(self) -> str:
        """Get memory context to pass to AI each turn."""
        sections = []
        
        # Long-term context
        if self.long_term:
            sections.append("=== DISTANT PAST ===")
            sections.append(" | ".join(self.long_term[-3:]))  # Last 3 long-term entries
        
        # Medium-term context
        if self.medium_term:
            sections.append("\n=== RECENT HISTORY ===")
            sections.append("\n".join(self.medium_term[-5:]))  # Last 5 medium summaries
        
        # Short-term (full detail)
        if self.short_term:
            sections.append("\n=== RECENT TURNS ===")
            for turn in self.short_term[-3:]:  # Last 3 turns with detail
                turn_text = f"Turn {turn.turn_number}"
                if turn.rune_drawn:
                    turn_text += f" (Rune: {turn.rune_drawn})"
                turn_text += f": {turn.player_action[:100]}..."
                if turn.ai_response_summary:
                    turn_text += f"\n  Result: {turn.ai_response_summary}"
                sections.append(turn_text)
        
        # Key facts
        if self.key_facts:
            sections.append("\n=== KEY FACTS ===")
            sections.append("; ".join(self.key_facts[-10:]))
        
        # Relationships
        if self.relationships_formed:
            sections.append("\n=== RELATIONSHIPS ===")
            for npc, rel in list(self.relationships_formed.items())[-5:]:
                sections.append(f"  {npc}: {rel}")
        
        # Current narrative
        if self.narrative_summary:
            sections.append(f"\n=== STORY SO FAR ===\n{self.narrative_summary}")
        
        return "\n".join(sections)
    
    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "started": self.started,
            "player_character": self.player_character,
            "short_term": [t.to_dict() for t in self.short_term],
            "medium_term": self.medium_term,
            "long_term": self.long_term,
            "narrative_summary": self.narrative_summary,
            "key_facts": self.key_facts,
            "relationships_formed": self.relationships_formed,
            "enemies_made": self.enemies_made,
            "allies_gained": self.allies_gained,
            "quests_discovered": self.quests_discovered,
            "locations_discovered": self.locations_discovered,
            "items_acquired": self.items_acquired
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionMemory':
        memory = cls(
            session_id=data.get("session_id", ""),
            started=data.get("started", ""),
            player_character=data.get("player_character", "")
        )
        memory.short_term = [TurnMemory.from_dict(t) for t in data.get("short_term", [])]
        memory.medium_term = data.get("medium_term", [])
        memory.long_term = data.get("long_term", [])
        memory.narrative_summary = data.get("narrative_summary", "")
        memory.key_facts = data.get("key_facts", [])
        memory.relationships_formed = data.get("relationships_formed", {})
        memory.enemies_made = data.get("enemies_made", [])
        memory.allies_gained = data.get("allies_gained", [])
        memory.quests_discovered = data.get("quests_discovered", [])
        memory.locations_discovered = data.get("locations_discovered", [])
        memory.items_acquired = data.get("items_acquired", [])
        return memory


class MemorySystemV3:
    """
    Enhanced memory system with AI-powered summarization.
    """
    
    def __init__(self, data_path: str = "data/memory"):
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.current_memory: Optional[SessionMemory] = None
        self.ai_summarizer = None  # Set externally with AI client
    
    def start_session(self, session_id: str, player_character: str) -> SessionMemory:
        """Start a new memory session."""
        self.current_memory = SessionMemory(
            session_id=session_id,
            started=datetime.now().isoformat(),
            player_character=player_character
        )
        return self.current_memory
    
    def load_session(self, session_id: str) -> Optional[SessionMemory]:
        """Load memory for a session."""
        memory_path = self.data_path / f"{session_id}_memory.json"
        if memory_path.exists():
            with open(memory_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.current_memory = SessionMemory.from_dict(data)
                return self.current_memory
        return None
    
    def save_session(self):
        """Save current memory to disk."""
        if not self.current_memory:
            return
        
        memory_path = self.data_path / f"{self.current_memory.session_id}_memory.json"
        with open(memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.current_memory.to_dict(), f, indent=2, ensure_ascii=False)
    
    def record_turn(
        self,
        turn_number: int,
        player_action: str,
        ai_response: str,
        rune_data: Optional[Dict] = None,
        location: str = "",
        sub_location: str = "",
        npcs_involved: List[str] = None,
        combat: bool = False,
        quest_updates: List[str] = None,
        important_events: List[str] = None
    ) -> TurnMemory:
        """
        Record a turn in memory.
        
        Args:
            turn_number: Current turn number
            player_action: What the player did
            ai_response: The AI's full response
            rune_data: Rune information if drawn
            location: Current city/region
            sub_location: Current sub-location
            npcs_involved: NPCs who appeared this turn
            combat: Whether combat occurred
            quest_updates: Any quest changes
            important_events: Major events to remember
        """
        if not self.current_memory:
            return None
        
        # Generate summary of AI response
        ai_summary = self._generate_summary(ai_response)
        
        turn = TurnMemory(
            turn_number=turn_number,
            timestamp=datetime.now().isoformat(),
            player_action=player_action[:500],  # Truncate if needed
            ai_response_summary=ai_summary,
            rune_drawn=rune_data.get("name") if rune_data else None,
            rune_influence=rune_data.get("mystic_effect", {}).get("description") if rune_data else None,
            location=location,
            sub_location=sub_location,
            npcs_involved=npcs_involved or [],
            combat_occurred=combat,
            quest_updates=quest_updates or [],
            important_events=important_events or []
        )
        
        self.current_memory.add_turn(turn)
        
        # Auto-save every 5 turns
        if turn_number % 5 == 0:
            self.save_session()
        
        return turn
    
    def _generate_summary(self, ai_response: str) -> str:
        """Generate a summary of the AI response."""
        # If we have an AI summarizer, use it
        if self.ai_summarizer:
            try:
                return self.ai_summarizer.summarize(ai_response)
            except Exception as exc:
                logger.warning("AI summary generation failed; falling back to heuristic summary: %s", exc)
        
        # Fallback: Extract first sentence and any key phrases
        if not ai_response:
            return ""
        
        # Simple extraction: first 2-3 sentences
        sentences = ai_response.replace('\n', ' ').split('.')
        summary_sentences = [s.strip() for s in sentences[:3] if s.strip()]
        return '. '.join(summary_sentences)[:200]
    
    def get_context(self) -> str:
        """Get memory context for AI."""
        if self.current_memory:
            return self.current_memory.get_context_for_ai()
        return ""
    
    def add_key_fact(self, fact: str):
        """Add a key fact manually."""
        if self.current_memory and fact not in self.current_memory.key_facts:
            self.current_memory.key_facts.append(fact)
    
    def add_relationship(self, npc: str, relationship: str):
        """Track a relationship."""
        if self.current_memory:
            self.current_memory.relationships_formed[npc] = relationship
    
    def update_narrative(self, narrative: str):
        """Update the running narrative summary."""
        if self.current_memory:
            self.current_memory.narrative_summary = narrative
    
    def get_full_history(self) -> str:
        """Get complete session history for export."""
        if not self.current_memory:
            return ""
        
        lines = [
            f"# Session {self.current_memory.session_id}",
            f"Started: {self.current_memory.started}",
            f"Character: {self.current_memory.player_character}",
            "",
            "## Timeline",
            ""
        ]
        
        # All turns
        for turn in self.current_memory.short_term:
            lines.append(f"### Turn {turn.turn_number}")
            lines.append(f"**Action:** {turn.player_action}")
            lines.append(f"**Result:** {turn.ai_response_summary}")
            if turn.rune_drawn:
                lines.append(f"**Rune:** {turn.rune_drawn}")
            lines.append("")
        
        return "\n".join(lines)


# AI Summary Generator (uses the game's AI client)
class AISummarizer:
    """Uses the game's AI to generate summaries."""
    
    def __init__(self, ai_client):
        self.ai_client = ai_client
    
    def summarize(self, text: str, max_length: int = 100) -> str:
        """Generate a brief summary of text."""
        if not text or len(text) < max_length:
            return text
        
        prompt = f"""Summarize this game event in 1-2 sentences (max {max_length} characters):

{text[:1000]}

Summary:"""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                temperature=0.3
            )
            return response.strip()[:max_length]
        except Exception as exc:
            # Fallback
            logger.warning("AISummarizer failed during summarize(); using truncation fallback: %s", exc)
            return text[:max_length]
    
    def generate_narrative_summary(self, memory: SessionMemory) -> str:
        """Generate a narrative summary of the session so far."""
        context = memory.get_context_for_ai()
        
        prompt = f"""Based on this game session history, write a brief narrative summary (2-3 paragraphs) of what has happened:

{context}

Write as if summarizing an adventure story. Include key events, relationships formed, and current situation.

Narrative Summary:"""
        
        try:
            response = self.ai_client.generate(
                prompt=prompt,
                temperature=0.7
            )
            return response.strip()
        except Exception as exc:
            logger.warning("AISummarizer failed during narrative summary generation: %s", exc)
            return ""
