#!/usr/bin/env python3
"""
Memory Manager
==============
Maintains running summaries and long-term memory for the AI.

The AI cannot hold long-term memory - this system provides it.
Generates compressed summaries periodically and feeds them back
into prompts for continuity.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
import re


@dataclass
class MemoryState:
    """Current memory state for a session."""
    session_id: str
    
    # Story arc tracking
    current_arc: str = "Beginning"
    arc_summary: str = ""
    
    # Known entities (discovered during play)
    known_npcs: List[Dict[str, str]] = field(default_factory=list)  # {id, name, relationship, last_seen}
    known_locations: List[Dict[str, str]] = field(default_factory=list)  # {id, name, visited}
    known_factions: List[Dict[str, str]] = field(default_factory=list)  # {id, name, standing}
    known_items: List[Dict[str, str]] = field(default_factory=list)  # {id, name, significance}
    
    # Active story threads
    active_conflicts: List[str] = field(default_factory=list)
    active_mysteries: List[str] = field(default_factory=list)
    pending_consequences: List[str] = field(default_factory=list)
    
    # Player state
    player_status: str = "Healthy"
    player_reputation: Dict[str, str] = field(default_factory=dict)  # {faction: standing}
    player_goals: List[str] = field(default_factory=list)
    
    # Recent events (rolling buffer)
    recent_events: List[str] = field(default_factory=list)
    
    # Important dialogue/revelations
    key_revelations: List[str] = field(default_factory=list)
    important_promises: List[str] = field(default_factory=list)
    
    # World state changes
    world_changes: List[str] = field(default_factory=list)
    
    # Timestamps
    last_updated: str = ""
    turn_count: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryState':
        return cls(**data)


class MemoryManager:
    """
    Manages long-term memory and context for AI continuity.
    
    Key responsibilities:
    1. Generate periodic summaries from gameplay
    2. Track all named entities for canonization
    3. Provide context injection for AI prompts
    4. Enable session recovery
    """
    
    def __init__(self, memory_dir: str = "data/memory"):
        self.memory_dir = Path(memory_dir)
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        
        self.state: Optional[MemoryState] = None
        self.memory_path: Optional[Path] = None
        
        # Buffer for recent exchanges (used for summary generation)
        self.exchange_buffer: List[Dict[str, str]] = []
        self.max_buffer_size = 20
        
        # Summary generation interval
        self.summary_interval = 5  # Generate summary every N turns
    
    def start_session(self, session_id: str, player_character: Dict, starting_location: str):
        """Initialize memory for a new session."""
        self.memory_path = self.memory_dir / f"{session_id}_memory.json"
        
        pc_name = player_character.get("identity", {}).get("name", "Unknown")
        
        self.state = MemoryState(
            session_id=session_id,
            current_arc="Arrival",
            arc_summary=f"{pc_name} begins their saga.",
            player_status="Healthy, ready for adventure",
            last_updated=datetime.now().isoformat()
        )
        
        # Add starting location to known
        self.state.known_locations.append({
            "id": starting_location,
            "name": starting_location.replace("_", " ").title(),
            "visited": datetime.now().isoformat()
        })
        
        self.save()
        return self.state
    
    def load_session(self, session_id: str) -> Optional[MemoryState]:
        """Load existing memory state."""
        self.memory_path = self.memory_dir / f"{session_id}_memory.json"
        
        if not self.memory_path.exists():
            return None
        
        with open(self.memory_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.state = MemoryState.from_dict(data)
        return self.state
    
    def save(self):
        """Save current memory state."""
        if not self.state or not self.memory_path:
            return
        
        self.state.last_updated = datetime.now().isoformat()
        
        with open(self.memory_path, 'w', encoding='utf-8') as f:
            json.dump(self.state.to_dict(), f, indent=2, default=str)
    
    def add_exchange(self, player_input: str, ai_response: str):
        """Add an exchange to the buffer."""
        self.exchange_buffer.append({
            "turn": self.state.turn_count if self.state else 0,
            "player": player_input,
            "ai": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Trim buffer if needed
        if len(self.exchange_buffer) > self.max_buffer_size:
            self.exchange_buffer = self.exchange_buffer[-self.max_buffer_size:]
        
        if self.state:
            self.state.turn_count += 1
            
            # Check if we should generate a summary
            if self.state.turn_count % self.summary_interval == 0:
                self.generate_summary()
    
    def add_event(self, event: str):
        """Add a significant event to memory."""
        if not self.state:
            return
        
        self.state.recent_events.append(event)
        
        # Keep only last 20 events
        if len(self.state.recent_events) > 20:
            self.state.recent_events = self.state.recent_events[-20:]
        
        self.save()
    
    def add_npc(self, npc_id: str, npc_name: str, relationship: str = "neutral"):
        """Add or update an NPC in memory."""
        if not self.state:
            return
        
        # Check if already known
        for npc in self.state.known_npcs:
            if npc["id"] == npc_id:
                npc["last_seen"] = datetime.now().isoformat()
                npc["relationship"] = relationship
                self.save()
                return
        
        # Add new
        self.state.known_npcs.append({
            "id": npc_id,
            "name": npc_name,
            "relationship": relationship,
            "last_seen": datetime.now().isoformat()
        })
        self.save()
    
    def add_location(self, location_id: str, location_name: str):
        """Add a location to memory."""
        if not self.state:
            return
        
        # Check if already known
        for loc in self.state.known_locations:
            if loc["id"] == location_id:
                loc["visited"] = datetime.now().isoformat()
                self.save()
                return
        
        # Add new
        self.state.known_locations.append({
            "id": location_id,
            "name": location_name,
            "visited": datetime.now().isoformat()
        })
        self.save()
    
    def add_revelation(self, revelation: str):
        """Add an important revelation/discovery."""
        if not self.state:
            return
        
        if revelation not in self.state.key_revelations:
            self.state.key_revelations.append(revelation)
            self.save()
    
    def add_conflict(self, conflict: str):
        """Add an active conflict/tension."""
        if not self.state:
            return
        
        if conflict not in self.state.active_conflicts:
            self.state.active_conflicts.append(conflict)
            self.save()
    
    def resolve_conflict(self, conflict: str, resolution: str = ""):
        """Mark a conflict as resolved."""
        if not self.state:
            return
        
        if conflict in self.state.active_conflicts:
            self.state.active_conflicts.remove(conflict)
            if resolution:
                self.add_event(f"Conflict resolved: {conflict} - {resolution}")
            self.save()
    
    def update_player_status(self, status: str):
        """Update player's current status."""
        if self.state:
            self.state.player_status = status
            self.save()
    
    def update_arc(self, arc_name: str, summary: str = ""):
        """Update the current story arc."""
        if self.state:
            self.state.current_arc = arc_name
            if summary:
                self.state.arc_summary = summary
            self.save()
    
    def generate_summary(self) -> Dict[str, Any]:
        """
        Generate a compressed summary from recent exchanges.
        This is the core memory consolidation function.
        """
        if not self.state:
            return {}
        
        # Build summary from buffer
        recent_text = "\n".join([
            f"Player: {ex['player']}\nAI: {ex['ai'][:500]}..."
            for ex in self.exchange_buffer[-5:]
        ])
        
        # Extract key events from recent exchanges
        # (In production, this would use AI to summarize)
        events = self._extract_events_simple(recent_text)
        
        for event in events:
            if event not in self.state.recent_events:
                self.state.recent_events.append(event)
        
        # Trim old events
        if len(self.state.recent_events) > 20:
            self.state.recent_events = self.state.recent_events[-20:]
        
        self.save()
        
        return self.get_context_for_prompt()
    
    def _extract_events_simple(self, text: str) -> List[str]:
        """
        Simple event extraction (rule-based).
        In production, use AI for this.
        """
        events = []
        
        # Look for action verbs and outcomes
        action_patterns = [
            r"(\w+) (attacked|killed|defeated|spoke to|met|discovered|found|learned|entered|left)",
            r"(combat|battle|fight) (began|ended|concluded)",
            r"(received|obtained|lost|gave) (\w+)",
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                events.append(" ".join(match))
        
        return events[:5]  # Limit to 5 events per summary
    
    def get_context_for_prompt(self) -> Dict[str, Any]:
        """
        Get memory context to inject into AI prompts.
        This is what gives the AI long-term memory.
        """
        if not self.state:
            return {}
        
        context = {
            "current_arc": self.state.current_arc,
            "arc_summary": self.state.arc_summary,
            "player_status": self.state.player_status,
            "turn_count": self.state.turn_count,
            
            # Recent history
            "recent_events": self.state.recent_events[-10:],
            
            # Active threads
            "active_conflicts": self.state.active_conflicts,
            "active_mysteries": self.state.active_mysteries,
            "pending_consequences": self.state.pending_consequences,
            
            # Key knowledge
            "key_revelations": self.state.key_revelations[-5:],
            "important_promises": self.state.important_promises,
            
            # Known NPCs (just names and relationships for prompt)
            "known_npcs": [
                f"{npc['name']} ({npc['relationship']})"
                for npc in self.state.known_npcs[-10:]
            ],
            
            # World changes
            "world_changes": self.state.world_changes[-5:]
        }
        
        return context
    
    def get_context_string(self) -> str:
        """Get memory context as a formatted string for prompts."""
        ctx = self.get_context_for_prompt()
        
        if not ctx:
            return ""
        
        parts = []
        
        parts.append(f"[STORY ARC: {ctx.get('current_arc', 'Unknown')}]")
        parts.append(f"Summary: {ctx.get('arc_summary', '')}")
        parts.append(f"Player Status: {ctx.get('player_status', 'Unknown')}")
        
        if ctx.get('recent_events'):
            parts.append("\n[RECENT EVENTS]")
            for event in ctx['recent_events']:
                parts.append(f"• {event}")
        
        if ctx.get('active_conflicts'):
            parts.append("\n[ACTIVE CONFLICTS]")
            for conflict in ctx['active_conflicts']:
                parts.append(f"• {conflict}")
        
        if ctx.get('key_revelations'):
            parts.append("\n[KEY REVELATIONS]")
            for rev in ctx['key_revelations']:
                parts.append(f"• {rev}")
        
        if ctx.get('known_npcs'):
            parts.append("\n[KNOWN NPCS]")
            for npc in ctx['known_npcs']:
                parts.append(f"• {npc}")
        
        return "\n".join(parts)
    
    def extract_entities_from_text(self, text: str) -> Dict[str, List[str]]:
        """
        Extract potential new entities from AI response.
        Used for auto-canonization.
        
        Returns dict with lists of: characters, locations, items, factions
        """
        entities = {
            "characters": [],
            "locations": [],
            "items": [],
            "factions": []
        }
        
        # Pattern for proper nouns (capitalized words)
        # Look for names that appear multiple times or in dialogue
        
        # Character patterns: "Name said", "Name the [title]", etc
        char_patterns = [
            r"([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:said|spoke|replied|asked|demanded|whispered|shouted|growled|laughed)",
            r"([A-Z][a-z]+(?:\s+the\s+[A-Z][a-z]+)?)\s+(?:is|was|stands|stood|looks|looked)",
            r"(?:called|named|known as)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
        ]
        
        for pattern in char_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and len(match) > 2:
                    entities["characters"].append(match)
        
        # Location patterns: "in/at/to [the] Name"
        loc_patterns = [
            r"(?:in|at|to|from|near)\s+(?:the\s+)?([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+(?:Hall|Temple|Grove|Market|Inn|Forge|House|Tower|Gate|Bridge|Ford|River|Forest|Mountain))?)",
            r"([A-Z][a-z]+(?:'s)?\s+(?:Hall|Temple|Grove|Market|Inn|Forge|House|Tower|Gate|Bridge|Ford))",
        ]
        
        for pattern in loc_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and len(match) > 3:
                    entities["locations"].append(match)
        
        # Item patterns: "the Name [weapon/item type]"
        item_patterns = [
            r"(?:the|a|an)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:sword|axe|spear|shield|helm|ring|amulet|staff|blade|bow)",
            r"([A-Z][a-z]+(?:-[A-Z][a-z]+)?)\s+(?:Blade|Edge|Bane|Bringer|Slayer)",
        ]
        
        for pattern in item_patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match:
                    entities["items"].append(match)
        
        # Deduplicate
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
