"""
Wyrd System - The Three Sacred Wells
=====================================

In Norse cosmology, three sacred wells lie at the roots of Yggdrasil:

1. URÐARBRUNNR (Well of Urd/Fate) - The Past
   - Where the Norns dwell
   - Records all that has happened
   - Stores completed events and their consequences

2. MÍMISBRUNNR (Mimir's Well) - The Present/Wisdom
   - Source of all knowledge
   - Where Odin sacrificed his eye
   - Stores current state and active knowledge

3. HVERGELMIR (Roaring Kettle) - The Future/Potential
   - Source of all rivers
   - Where Níðhöggr gnaws at the roots
   - Stores predictions, prophecies, and potential outcomes

All data in the game flows through these wells:
- Past events → Urðarbrunnr
- Current state → Mímisbrunnr  
- Future possibilities → Hvergelmir

The Norns (Urd, Verdandi, Skuld) weave the threads of fate
by drawing from and contributing to these wells.
"""

import logging
import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field, asdict
from pathlib import Path
from enum import Enum
import threading

logger = logging.getLogger(__name__)


class WellType(Enum):
    """The three sacred wells."""
    URDARBRUNNR = "urdarbrunnr"   # Past - Fate
    MIMISBRUNNR = "mimisbrunnr"   # Present - Wisdom
    HVERGELMIR = "hvergelmir"     # Future - Potential


class NornType(Enum):
    """The three Norns who tend the wells."""
    URD = "urd"           # What was (Past)
    VERDANDI = "verdandi" # What is (Present)
    SKULD = "skuld"       # What shall be (Future)


@dataclass
class WyrdThread:
    """A single thread of fate."""
    id: str
    content: Any
    thread_type: str  # event, state, prophecy, memory, action, outcome
    timestamp: str
    importance: int  # 1-10
    tags: List[str] = field(default_factory=list)
    related_threads: List[str] = field(default_factory=list)
    characters_involved: List[str] = field(default_factory=list)
    location: str = ""
    turn_number: int = 0
    norn_source: str = ""  # Which Norn created this thread
    verified: bool = False


@dataclass
class WellContents:
    """Contents of a sacred well."""
    well_type: WellType
    threads: Dict[str, WyrdThread] = field(default_factory=dict)
    last_updated: str = ""
    total_threads: int = 0


class SacredWell:
    """
    A single sacred well that stores threads of fate.
    """
    
    def __init__(self, well_type: WellType, storage_path: Path = None):
        self.well_type = well_type
        self.storage_path = storage_path
        self.threads: Dict[str, WyrdThread] = {}
        self._lock = threading.Lock()
        self._thread_counter = 0
        
        # Load existing threads if storage exists
        if storage_path:
            self._load_from_storage()
    
    def _generate_thread_id(self, content: str) -> str:
        """Generate unique thread ID."""
        self._thread_counter += 1
        hash_base = f"{self.well_type.value}_{datetime.now().isoformat()}_{content[:50]}_{self._thread_counter}"
        return hashlib.sha256(hash_base.encode()).hexdigest()[:16]
    
    def add_thread(
        self,
        content: Any,
        thread_type: str,
        importance: int = 5,
        tags: List[str] = None,
        characters: List[str] = None,
        location: str = "",
        turn_number: int = 0,
        norn_source: str = ""
    ) -> str:
        """Add a new thread to the well."""
        with self._lock:
            thread_id = self._generate_thread_id(str(content))
            
            thread = WyrdThread(
                id=thread_id,
                content=content,
                thread_type=thread_type,
                timestamp=datetime.now().isoformat(),
                importance=importance,
                tags=tags or [],
                characters_involved=characters or [],
                location=location,
                turn_number=turn_number,
                norn_source=norn_source
            )
            
            self.threads[thread_id] = thread
            
            # Save to storage
            if self.storage_path:
                self._save_to_storage()
            
            logger.debug(f"[{self.well_type.value}] Added thread: {thread_id}")
            return thread_id
    
    def get_thread(self, thread_id: str) -> Optional[WyrdThread]:
        """Get a specific thread."""
        return self.threads.get(thread_id)
    
    def get_threads_by_type(self, thread_type: str) -> List[WyrdThread]:
        """Get all threads of a specific type."""
        return [t for t in self.threads.values() if t.thread_type == thread_type]
    
    def get_threads_by_tag(self, tag: str) -> List[WyrdThread]:
        """Get all threads with a specific tag."""
        return [t for t in self.threads.values() if tag in t.tags]
    
    def get_threads_by_character(self, character: str) -> List[WyrdThread]:
        """Get all threads involving a character."""
        char_lower = character.lower()
        return [t for t in self.threads.values() 
                if any(char_lower in c.lower() for c in t.characters_involved)]
    
    def get_recent_threads(self, count: int = 10) -> List[WyrdThread]:
        """Get most recent threads."""
        sorted_threads = sorted(
            self.threads.values(),
            key=lambda t: t.timestamp,
            reverse=True
        )
        return sorted_threads[:count]
    
    def get_important_threads(self, min_importance: int = 7) -> List[WyrdThread]:
        """Get threads above importance threshold."""
        return [t for t in self.threads.values() if t.importance >= min_importance]
    
    def link_threads(self, thread_id1: str, thread_id2: str):
        """Link two threads together."""
        if thread_id1 in self.threads and thread_id2 in self.threads:
            if thread_id2 not in self.threads[thread_id1].related_threads:
                self.threads[thread_id1].related_threads.append(thread_id2)
            if thread_id1 not in self.threads[thread_id2].related_threads:
                self.threads[thread_id2].related_threads.append(thread_id1)
    
    def _load_from_storage(self):
        """Load threads from storage file."""
        if not self.storage_path:
            return
        
        filepath = self.storage_path / f"{self.well_type.value}.json"
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for thread_data in data.get("threads", []):
                    thread = WyrdThread(**thread_data)
                    self.threads[thread.id] = thread
                
                self._thread_counter = data.get("counter", 0)
                logger.info(f"Loaded {len(self.threads)} threads from {self.well_type.value}")
            except Exception as e:
                logger.error(f"Failed to load {self.well_type.value}: {e}")
    
    def _save_to_storage(self):
        """Save threads to storage file."""
        if not self.storage_path:
            return
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        filepath = self.storage_path / f"{self.well_type.value}.json"
        
        try:
            data = {
                "well_type": self.well_type.value,
                "counter": self._thread_counter,
                "last_updated": datetime.now().isoformat(),
                "threads": [asdict(t) for t in self.threads.values()]
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to save {self.well_type.value}: {e}")


class Norn:
    """
    A Norn who tends a sacred well and weaves fate.
    """
    
    def __init__(self, norn_type: NornType, well: SacredWell, llm_callable=None):
        self.norn_type = norn_type
        self.well = well
        self.llm = llm_callable
    
    def weave(
        self,
        content: Any,
        thread_type: str,
        importance: int = 5,
        **kwargs
    ) -> str:
        """Weave a new thread into the well."""
        return self.well.add_thread(
            content=content,
            thread_type=thread_type,
            importance=importance,
            norn_source=self.norn_type.value,
            **kwargs
        )
    
    def divine(self, query: str) -> List[WyrdThread]:
        """Divine relevant threads based on a query."""
        relevant = []
        query_lower = query.lower()
        
        for thread in self.well.threads.values():
            # Check content match
            content_str = str(thread.content).lower()
            if query_lower in content_str:
                relevant.append(thread)
                continue
            
            # Check tag match
            if any(query_lower in tag.lower() for tag in thread.tags):
                relevant.append(thread)
                continue
            
            # Check character match
            if any(query_lower in char.lower() for char in thread.characters_involved):
                relevant.append(thread)
        
        # Sort by importance
        relevant.sort(key=lambda t: t.importance, reverse=True)
        return relevant[:10]


class WyrdSystem:
    """
    The complete Wyrd system managing all three sacred wells
    and the three Norns who tend them.
    
    All game events flow through this system:
    - Past events are recorded in Urðarbrunnr
    - Current state is maintained in Mímisbrunnr
    - Prophecies and possibilities go to Hvergelmir
    """
    
    def __init__(self, storage_path: str = None, llm_callable=None):
        self.storage_path = Path(storage_path) if storage_path else None
        self.llm = llm_callable
        
        # Create the three sacred wells
        well_storage = self.storage_path / "wells" if self.storage_path else None
        
        self.urdarbrunnr = SacredWell(WellType.URDARBRUNNR, well_storage)  # Past
        self.mimisbrunnr = SacredWell(WellType.MIMISBRUNNR, well_storage)  # Present
        self.hvergelmir = SacredWell(WellType.HVERGELMIR, well_storage)    # Future
        
        # Create the three Norns
        self.urd = Norn(NornType.URD, self.urdarbrunnr, llm_callable)
        self.verdandi = Norn(NornType.VERDANDI, self.mimisbrunnr, llm_callable)
        self.skuld = Norn(NornType.SKULD, self.hvergelmir, llm_callable)
        
        logger.info("Wyrd System initialized with three sacred wells")
    
    # ========================================================================
    # PAST - Urðarbrunnr (Well of Fate)
    # ========================================================================
    
    def record_past_event(
        self,
        event_description: str,
        event_type: str = "event",
        importance: int = 5,
        characters: List[str] = None,
        location: str = "",
        turn_number: int = 0,
        tags: List[str] = None
    ) -> str:
        """Record a past event in the Well of Fate."""
        return self.urd.weave(
            content=event_description,
            thread_type=event_type,
            importance=importance,
            characters=characters,
            location=location,
            turn_number=turn_number,
            tags=tags or ["past", "event"]
        )
    
    def record_turn_summary(
        self,
        turn_number: int,
        player_action: str,
        narrative_result: str,
        characters_involved: List[str] = None,
        location: str = "",
        ai_summary: str = None
    ) -> str:
        """Record a complete turn summary."""
        summary_content = {
            "turn": turn_number,
            "player_action": player_action,
            "narrative": narrative_result[:500],  # Truncate for storage
            "ai_summary": ai_summary or f"Turn {turn_number}: {player_action[:100]}",
            "characters": characters_involved or [],
            "location": location,
            "timestamp": datetime.now().isoformat()
        }
        
        return self.urd.weave(
            content=summary_content,
            thread_type="turn_summary",
            importance=6,
            characters=characters_involved,
            location=location,
            turn_number=turn_number,
            tags=["turn", "summary", f"turn_{turn_number}"]
        )
    
    def get_past_events(self, count: int = 10) -> List[WyrdThread]:
        """Get recent past events."""
        return self.urdarbrunnr.get_recent_threads(count)
    
    def get_character_history(self, character: str) -> List[WyrdThread]:
        """Get all past events involving a character."""
        return self.urdarbrunnr.get_threads_by_character(character)
    
    # ========================================================================
    # PRESENT - Mímisbrunnr (Well of Wisdom)
    # ========================================================================
    
    def update_current_state(
        self,
        state_key: str,
        state_value: Any,
        importance: int = 5
    ) -> str:
        """Update current state in the Well of Wisdom."""
        return self.verdandi.weave(
            content={"key": state_key, "value": state_value},
            thread_type="state",
            importance=importance,
            tags=["present", "state", state_key]
        )
    
    def store_knowledge(
        self,
        knowledge: str,
        knowledge_type: str = "fact",
        importance: int = 5,
        tags: List[str] = None
    ) -> str:
        """Store knowledge in the Well of Wisdom."""
        return self.verdandi.weave(
            content=knowledge,
            thread_type=knowledge_type,
            importance=importance,
            tags=tags or ["knowledge", knowledge_type]
        )
    
    def store_character_data(
        self,
        character_id: str,
        character_data: Dict[str, Any],
        importance: int = 7
    ) -> str:
        """Store character data for AI consumption."""
        return self.verdandi.weave(
            content=character_data,
            thread_type="character_data",
            importance=importance,
            characters=[character_id],
            tags=["character", "data", character_id]
        )
    
    def get_current_knowledge(self, query: str) -> List[WyrdThread]:
        """Divine current knowledge related to a query."""
        return self.verdandi.divine(query)
    
    # ========================================================================
    # FUTURE - Hvergelmir (Roaring Kettle)
    # ========================================================================
    
    def store_prophecy(
        self,
        prophecy: str,
        probability: float = 0.5,
        related_to: List[str] = None,
        importance: int = 6
    ) -> str:
        """Store a prophecy or prediction."""
        return self.skuld.weave(
            content={"prophecy": prophecy, "probability": probability},
            thread_type="prophecy",
            importance=importance,
            characters=related_to,
            tags=["future", "prophecy"]
        )
    
    def store_potential_outcome(
        self,
        action: str,
        possible_outcomes: List[str],
        importance: int = 5
    ) -> str:
        """Store potential outcomes for an action."""
        return self.skuld.weave(
            content={"action": action, "outcomes": possible_outcomes},
            thread_type="potential",
            importance=importance,
            tags=["future", "potential", "outcomes"]
        )
    
    def get_prophecies(self, character: str = None) -> List[WyrdThread]:
        """Get prophecies, optionally filtered by character."""
        if character:
            return self.hvergelmir.get_threads_by_character(character)
        return self.hvergelmir.get_threads_by_type("prophecy")
    
    # ========================================================================
    # CROSS-WELL OPERATIONS
    # ========================================================================
    
    def weave_fate(
        self,
        past_thread_id: str,
        present_thread_id: str,
        future_thread_id: str
    ):
        """
        Weave threads from all three wells together,
        creating a complete fate tapestry.
        """
        # Link the threads
        self.urdarbrunnr.link_threads(past_thread_id, present_thread_id)
        self.mimisbrunnr.link_threads(present_thread_id, future_thread_id)
        
        # Mark as verified fate
        if past_thread_id in self.urdarbrunnr.threads:
            self.urdarbrunnr.threads[past_thread_id].verified = True
    
    def divine_fate(self, query: str) -> Dict[str, List[WyrdThread]]:
        """Divine fate across all three wells."""
        return {
            "past": self.urd.divine(query),
            "present": self.verdandi.divine(query),
            "future": self.skuld.divine(query)
        }
    
    def get_context_for_ai(
        self,
        query: str,
        max_past: int = 5,
        max_present: int = 5,
        max_future: int = 3
    ) -> Dict[str, Any]:
        """
        Get context from all three wells for AI consumption.
        This is the primary interface for feeding the AI.
        """
        fate = self.divine_fate(query)
        
        return {
            "past_events": [
                {"content": t.content, "turn": t.turn_number, "importance": t.importance}
                for t in fate["past"][:max_past]
            ],
            "current_knowledge": [
                {"content": t.content, "type": t.thread_type}
                for t in fate["present"][:max_present]
            ],
            "future_possibilities": [
                {"content": t.content, "type": t.thread_type}
                for t in fate["future"][:max_future]
            ]
        }
    
    def get_statistics(self) -> Dict[str, int]:
        """Get statistics about the wells."""
        return {
            "urdarbrunnr_threads": len(self.urdarbrunnr.threads),
            "mimisbrunnr_threads": len(self.mimisbrunnr.threads),
            "hvergelmir_threads": len(self.hvergelmir.threads),
            "total_threads": (
                len(self.urdarbrunnr.threads) +
                len(self.mimisbrunnr.threads) +
                len(self.hvergelmir.threads)
            )
        }


# Factory function
def create_wyrd_system(storage_path: str = None, llm_callable=None) -> WyrdSystem:
    """Create a Wyrd system instance."""
    return WyrdSystem(storage_path=storage_path, llm_callable=llm_callable)
