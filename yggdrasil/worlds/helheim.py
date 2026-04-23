"""
Helheim - Reflection & Ancestral Memory
======================================

The underworld—death, wisdom from the past, resurrection of knowledge.
Archiving the fallen.

Processes:
- Memory storage and retrieval
- Ancestral log analysis
- Pattern resurrection
- Memory compression
- Wisdom extraction from past runs

This is where Muninn dwells, keeper of memory.
"""

import logging
import json
import sqlite3
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """A single memory entry in Helheim."""
    id: str
    content: Any
    memory_type: str  # fact, event, result, error, lesson
    realm_source: str
    importance: int  # 1-10
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)
    accessed_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content if not callable(self.content) else str(self.content),
            "memory_type": self.memory_type,
            "realm_source": self.realm_source,
            "importance": self.importance,
            "timestamp": self.timestamp.isoformat(),
            "tags": self.tags,
            "accessed_count": self.accessed_count,
        }


class Helheim:
    """
    Reflection & Ancestral Memory.
    
    Handles:
    - Memory storage with SQLite persistence
    - Ancestral log analysis
    - Pattern resurrection and matching
    - Memory compression algorithms
    - Wisdom extraction from past runs
    """
    
    def __init__(self, db_path: str = None, in_memory: bool = True):
        """
        Initialize Helheim.
        
        Args:
            db_path: Path to SQLite database
            in_memory: Use in-memory storage only
        """
        self.in_memory = in_memory
        self.db_path = db_path
        self._lock = threading.Lock()
        
        # In-memory storage
        self._memories: Dict[str, Memory] = {}
        self._memory_index: Dict[str, List[str]] = {}  # tag -> memory_ids
        
        # SQLite for persistence
        self._conn: Optional[sqlite3.Connection] = None
        if not in_memory and db_path:
            self._init_database()
    
    def _init_database(self):
        """Initialize SQLite database."""
        try:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT,
                    memory_type TEXT,
                    realm_source TEXT,
                    importance INTEGER,
                    timestamp TEXT,
                    tags TEXT,
                    accessed_count INTEGER DEFAULT 0
                )
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memory_type ON memories(memory_type)
            """)
            self._conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_importance ON memories(importance)
            """)
            self._conn.commit()
            logger.info(f"Helheim database initialized: {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize Helheim database: {e}")
            self._conn = None
    
    def _generate_memory_id(self, content: Any) -> str:
        """Generate unique memory ID based on content."""
        content_str = json.dumps(content, default=str, sort_keys=True)
        hash_val = hashlib.sha256(content_str.encode()).hexdigest()[:16]
        return f"mem_{hash_val}_{int(datetime.now().timestamp())}"
    
    def store(
        self,
        content: Any,
        memory_type: str = "fact",
        realm_source: str = "unknown",
        importance: int = 5,
        tags: List[str] = None
    ) -> str:
        """
        Store a memory.
        
        Args:
            content: Content to store
            memory_type: Type of memory (fact, event, result, error, lesson)
            realm_source: Which realm created this memory
            importance: Importance level 1-10
            tags: Optional tags for indexing
            
        Returns:
            Memory ID
        """
        memory_id = self._generate_memory_id(content)
        tags = tags or []
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            realm_source=realm_source,
            importance=importance,
            tags=tags,
        )
        
        with self._lock:
            # Store in memory
            self._memories[memory_id] = memory
            
            # Update index
            for tag in tags:
                if tag not in self._memory_index:
                    self._memory_index[tag] = []
                self._memory_index[tag].append(memory_id)
            
            # Also index by type
            if memory_type not in self._memory_index:
                self._memory_index[memory_type] = []
            self._memory_index[memory_type].append(memory_id)
        
        # Persist to database if available
        if self._conn:
            try:
                self._conn.execute(
                    """INSERT OR REPLACE INTO memories 
                       (id, content, memory_type, realm_source, importance, timestamp, tags, accessed_count)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (memory_id, json.dumps(content, default=str), memory_type,
                     realm_source, importance, datetime.now().isoformat(),
                     json.dumps(tags), 0)
                )
                self._conn.commit()
            except Exception as e:
                logger.warning(f"Failed to persist memory: {e}")
        
        logger.debug(f"Helheim stored memory {memory_id}: {memory_type}, importance={importance}")
        
        return memory_id
    
    def retrieve(self, memory_id: str) -> Optional[Memory]:
        """
        Retrieve a specific memory.
        
        Args:
            memory_id: Memory ID to retrieve
            
        Returns:
            Memory object or None
        """
        with self._lock:
            memory = self._memories.get(memory_id)
            
            if memory:
                memory.accessed_count += 1
                return memory
        
        # Try database
        if self._conn:
            try:
                cursor = self._conn.execute(
                    "SELECT * FROM memories WHERE id = ?",
                    (memory_id,)
                )
                row = cursor.fetchone()
                if row:
                    # Update access count
                    self._conn.execute(
                        "UPDATE memories SET accessed_count = accessed_count + 1 WHERE id = ?",
                        (memory_id,)
                    )
                    self._conn.commit()
                    
                    return Memory(
                        id=row[0],
                        content=json.loads(row[1]),
                        memory_type=row[2],
                        realm_source=row[3],
                        importance=row[4],
                        timestamp=datetime.fromisoformat(row[5]),
                        tags=json.loads(row[6]),
                        accessed_count=row[7] + 1,
                    )
            except Exception as e:
                logger.warning(f"Failed to retrieve from database: {e}")
        
        return None
    
    def search(
        self,
        query: str = None,
        memory_type: str = None,
        tags: List[str] = None,
        min_importance: int = 0,
        limit: int = 10
    ) -> List[Memory]:
        """
        Search memories.
        
        Args:
            query: Text to search in content
            memory_type: Filter by type
            tags: Filter by tags (any match)
            min_importance: Minimum importance level
            limit: Maximum results
            
        Returns:
            List of matching memories
        """
        results = []
        
        with self._lock:
            candidates = list(self._memories.values())
        
        for memory in candidates:
            # Filter by type
            if memory_type and memory.memory_type != memory_type:
                continue
            
            # Filter by importance
            if memory.importance < min_importance:
                continue
            
            # Filter by tags
            if tags and not any(t in memory.tags for t in tags):
                continue
            
            # Filter by query
            if query:
                content_str = json.dumps(memory.content, default=str).lower()
                if query.lower() not in content_str:
                    continue
            
            results.append(memory)
        
        # Sort by importance and recency
        results.sort(key=lambda m: (m.importance, m.timestamp.timestamp()), reverse=True)
        
        return results[:limit]
    
    def retrieve_ancestral(self, realm: str, limit: int = 5) -> List[Memory]:
        """
        Retrieve ancestral memories from a specific realm.
        
        Args:
            realm: Realm to search
            limit: Maximum results
            
        Returns:
            List of memories from that realm
        """
        return self.search(
            memory_type=None,
            tags=[realm],
            limit=limit
        )
    
    def analyze_logs(self, memory_type: str = "error") -> List[Dict[str, Any]]:
        """
        Analyze logs/errors for patterns.
        
        Args:
            memory_type: Type to analyze
            
        Returns:
            Analysis results
        """
        memories = self.search(memory_type=memory_type, limit=100)
        
        # Group by realm
        by_realm = {}
        for m in memories:
            realm = m.realm_source
            if realm not in by_realm:
                by_realm[realm] = []
            by_realm[realm].append(m)
        
        analysis = []
        for realm, realm_memories in by_realm.items():
            analysis.append({
                "realm": realm,
                "count": len(realm_memories),
                "avg_importance": sum(m.importance for m in realm_memories) / max(1, len(realm_memories)),
                "recent": realm_memories[0].timestamp.isoformat() if realm_memories else None,
            })
        
        return analysis
    
    def resurrect_patterns(self, pattern: str) -> List[Memory]:
        """
        Find memories matching a pattern for resurrection/reuse.
        
        Args:
            pattern: Pattern to match
            
        Returns:
            Matching memories
        """
        return self.search(query=pattern, min_importance=5, limit=5)
    
    def archive_memory(self, data: Any) -> str:
        """
        Archive data with compression.
        
        Args:
            data: Data to archive
            
        Returns:
            Compressed JSON string
        """
        # Simple compression: remove whitespace
        return json.dumps(data, separators=(',', ':'), default=str)
    
    def extract_wisdom(self, realm: str = None, limit: int = 3) -> List[str]:
        """
        Extract wisdom (high-importance lessons) from past runs.
        
        Args:
            realm: Optional realm filter
            limit: Maximum wisdom items
            
        Returns:
            List of wisdom strings
        """
        tags = [realm] if realm else None
        lessons = self.search(memory_type="lesson", tags=tags, min_importance=7, limit=limit)
        
        wisdom = []
        for lesson in lessons:
            if isinstance(lesson.content, str):
                wisdom.append(lesson.content)
            elif isinstance(lesson.content, dict):
                wisdom.append(lesson.content.get("lesson", str(lesson.content)))
            else:
                wisdom.append(str(lesson.content))
        
        return wisdom
    
    def dump(self, limit: int = 50) -> Dict[str, Any]:
        """
        Dump all memories for serialization.
        
        Args:
            limit: Maximum memories to dump
            
        Returns:
            Dictionary of all memories
        """
        with self._lock:
            memories = sorted(
                self._memories.values(),
                key=lambda m: m.importance,
                reverse=True
            )[:limit]
        
        return {
            "memory_count": len(self._memories),
            "memories": [m.to_dict() for m in memories],
        }
    
    def clear(self, memory_type: str = None):
        """
        Clear memories.
        
        Args:
            memory_type: Optional type filter (clears all if None)
        """
        with self._lock:
            if memory_type:
                to_remove = [
                    mid for mid, m in self._memories.items()
                    if m.memory_type == memory_type
                ]
                for mid in to_remove:
                    del self._memories[mid]
            else:
                self._memories.clear()
                self._memory_index.clear()
        
        if self._conn and not memory_type:
            try:
                self._conn.execute("DELETE FROM memories")
                self._conn.commit()
            except Exception as e:
                logger.warning(f"Failed to clear database: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        with self._lock:
            by_type = {}
            by_realm = {}
            total_importance = 0
            
            for m in self._memories.values():
                by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
                by_realm[m.realm_source] = by_realm.get(m.realm_source, 0) + 1
                total_importance += m.importance
            
            return {
                "total_memories": len(self._memories),
                "by_type": by_type,
                "by_realm": by_realm,
                "avg_importance": total_importance / max(1, len(self._memories)),
            }
