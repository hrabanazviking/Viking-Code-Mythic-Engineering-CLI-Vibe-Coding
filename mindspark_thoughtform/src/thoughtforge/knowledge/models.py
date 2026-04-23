"""
All 14 core data structure types for MindSpark: ThoughtForge.

Storage formats:
- PersonalityCoreRecord     → YAML  (personality_core.yaml)
- UserPreferenceRecord      → JSONL (user_profile_store.jsonl)
- UserFactRecord            → JSONL (user_profile_store.jsonl)
- EpisodicMemoryRecord      → JSONL (episodic_store.jsonl)
- ResponsePatternRecord     → JSONL (response_patterns.jsonl)
- ActiveThreadStateRecord   → JSON  (active_thread_state.json)
- InputSketch               → transient (not persisted)
- MemoryActivationBundle    → transient
- CognitionScaffold         → transient
- CandidateRecord           → transient
- FragmentRecord            → transient
- FinalResponseRecord       → transient (optionally logged)
- WritebackRecord           → transient (drives persistence)
- RuntimeTurnState          → transient (full execution trace)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal


# ── Helpers ────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


RecordStatus = Literal["created", "reinforced", "active", "cooling", "stale", "archived", "deleted"]
RetentionClass = Literal["protected", "durable", "standard", "ephemeral", "discardable"]


# ── 1. PersonalityCoreRecord ───────────────────────────────────────────────────

@dataclass
class PersonalityCoreRecord:
    """Stable behavioral identity. Never auto-pruned. Versioned manually."""

    record_id: str                         # e.g. "pers_001"
    version: int = 1
    traits: list[str] = field(default_factory=list)
    speech_style: list[str] = field(default_factory=list)
    behavior_rules: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    weights: dict[str, float] = field(default_factory=dict)
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    status: RecordStatus = "active"
    retention_class: RetentionClass = "protected"

    def to_dict(self) -> dict[str, Any]:
        return {
            "record_id": self.record_id,
            "version": self.version,
            "traits": self.traits,
            "speech_style": self.speech_style,
            "behavior_rules": self.behavior_rules,
            "avoid": self.avoid,
            "weights": self.weights,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "retention_class": self.retention_class,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "PersonalityCoreRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 2. UserPreferenceRecord ────────────────────────────────────────────────────

@dataclass
class UserPreferenceRecord:
    """User tone/style preference. Soft-decays if unconfirmed."""

    record_id: str
    category: str                          # e.g. "tone", "format", "depth"
    tags: list[str] = field(default_factory=list)
    summary: str = ""                      # max 160 chars
    value: str = ""
    importance: float = 0.5               # 0.0–1.0
    confidence: float = 0.5
    recency_weight: float = 1.0
    times_reinforced: int = 0
    times_retrieved: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_used_at: str = field(default_factory=_now_iso)
    last_confirmed_at: str = field(default_factory=_now_iso)
    status: RecordStatus = "created"
    retention_class: RetentionClass = "standard"
    stale_after_turns: int = 200
    record_type: str = "user_preference"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserPreferenceRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 3. UserFactRecord ──────────────────────────────────────────────────────────

@dataclass
class UserFactRecord:
    """Durable contextual fact about the user or their work."""

    record_id: str
    tags: list[str] = field(default_factory=list)
    summary: str = ""                      # max 180 chars
    fact_value: dict[str, Any] = field(default_factory=dict)
    importance: float = 0.5
    confidence: float = 0.6
    recency_weight: float = 1.0
    times_reinforced: int = 0
    times_retrieved: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_used_at: str = field(default_factory=_now_iso)
    status: RecordStatus = "created"
    retention_class: RetentionClass = "standard"
    stale_after_turns: int = 500
    record_type: str = "user_fact"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "UserFactRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 4. EpisodicMemoryRecord ────────────────────────────────────────────────────

@dataclass
class EpisodicMemoryRecord:
    """Compact summary of a notable conversation moment."""

    record_id: str
    tags: list[str] = field(default_factory=list)
    summary: str = ""                      # max 240 chars
    tone: str = ""
    importance: float = 0.4
    confidence: float = 0.5
    quality: float = 0.5
    recency_weight: float = 1.0
    linked_preferences: list[str] = field(default_factory=list)
    linked_facts: list[str] = field(default_factory=list)
    times_reinforced: int = 0
    times_retrieved: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_used_at: str = field(default_factory=_now_iso)
    status: RecordStatus = "created"
    retention_class: RetentionClass = "ephemeral"
    stale_after_turns: int = 30
    record_type: str = "episode"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "EpisodicMemoryRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 5. ResponsePatternRecord ───────────────────────────────────────────────────

@dataclass
class ResponsePatternRecord:
    """Reusable successful response structure."""

    record_id: str
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    pattern_shape: list[str] = field(default_factory=list)  # e.g. ["acknowledge", "explain", "example"]
    quality: float = 0.6
    times_successful: int = 0
    times_retrieved: int = 0
    importance: float = 0.5
    confidence: float = 0.6
    recency_weight: float = 1.0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    last_used_at: str = field(default_factory=_now_iso)
    status: RecordStatus = "created"
    retention_class: RetentionClass = "standard"
    stale_after_turns: int = 100
    record_type: str = "response_pattern"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ResponsePatternRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 6. ActiveThreadStateRecord ─────────────────────────────────────────────────

@dataclass
class ActiveThreadStateRecord:
    """Hot-path current conversation thread state. Aggressive expiry."""

    record_id: str
    topic: str = ""
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    priority: float = 0.8
    status: RecordStatus = "active"
    open_loops: list[str] = field(default_factory=list)   # max 6 soft / 8 hard
    expires_after_turns: int = 10
    turns_since_touch: int = 0
    created_at: str = field(default_factory=_now_iso)
    updated_at: str = field(default_factory=_now_iso)
    retention_class: RetentionClass = "ephemeral"
    record_type: str = "active_thread_state"

    def cool_down(self) -> None:
        """Apply one turn of priority cooling."""
        self.turns_since_touch += 1
        self.priority = max(0.0, self.priority - 0.08 * self.turns_since_touch)
        self.expires_after_turns = max(0, self.expires_after_turns - self.turns_since_touch)
        if self.expires_after_turns <= 0 or self.priority < 0.20:
            self.status = "stale"

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "ActiveThreadStateRecord":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 7. InputSketch ─────────────────────────────────────────────────────────────

@dataclass
class InputSketch:
    """Transient representation of the user's current message. Not persisted."""

    raw_text: str
    intent: str = ""                       # e.g. "question", "command", "request", "chitchat"
    topic: str = ""
    tone_in: str = ""                      # detected tone of user's message
    response_mode: str = "conversational"  # conversational | technical | supportive | creative
    memory_triggers: list[str] = field(default_factory=list)
    urgency: float = 0.5                   # 0.0 = low, 1.0 = urgent
    retrieval_path: str = "hybrid"         # sql | vector | hybrid


# ── 8. MemoryActivationBundle ──────────────────────────────────────────────────

@dataclass
class ActivatedRecord:
    """A single activated memory record with its retrieval score and compressed cue."""

    record_id: str
    record_type: str
    score: float
    cue: str                               # 5–18 word compressed cue
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryActivationBundle:
    """Compact retrieved memory passed to the generation layer."""

    personality_core_id: str | None = None
    activated_records: list[ActivatedRecord] = field(default_factory=list)
    total_retrieved: int = 0
    retrieval_confidence: float = 0.0


# ── 9. CognitionScaffold ──────────────────────────────────────────────────────

@dataclass
class CognitionScaffold:
    """Tiny YAML-like steering object for deterministic generation guidance."""

    goal: str = ""
    tone: list[str] = field(default_factory=list)          # e.g. ["warm", "direct", "grounded"]
    focus: list[str] = field(default_factory=list)         # e.g. ["clarity", "brevity"]
    avoid: list[str] = field(default_factory=list)         # e.g. ["fluff", "handwaving"]
    depth: str = "medium"                                  # light | medium | expert
    candidate_modes: list[str] = field(default_factory=list)
    fact_block: str = ""                                   # injected retrieval context
    prompt_text: str = ""                                  # fully assembled prompt

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


# ── 10. CandidateRecord ────────────────────────────────────────────────────────

@dataclass
class CandidateScores:
    relevance: float = 0.0
    clarity: float = 0.0
    coherence: float = 0.0
    personality_fit: float = 0.0
    specificity: float = 0.0
    genericness_penalty: float = 0.0
    goal_fit: float = 0.0

    @property
    def composite(self) -> float:
        return (
            self.relevance * 0.28
            + self.clarity * 0.18
            + self.coherence * 0.16
            + self.personality_fit * 0.16
            + self.specificity * 0.14
            + self.goal_fit * 0.08
            - self.genericness_penalty * 0.10
        )


@dataclass
class CandidateRecord:
    """First-pass generation output awaiting salvage scoring."""

    candidate_id: str
    mode: str = ""
    text: str = ""
    token_estimate: int = 0
    scores: CandidateScores = field(default_factory=CandidateScores)


# ── 11. FragmentRecord ────────────────────────────────────────────────────────

@dataclass
class FragmentScores:
    relevance: float = 0.0
    clarity: float = 0.0
    specificity: float = 0.0
    usefulness: float = 0.0
    personality_fit: float = 0.0
    genericness_penalty: float = 0.0

    @property
    def composite(self) -> float:
        return (
            self.relevance * 0.30
            + self.clarity * 0.18
            + self.specificity * 0.18
            + self.usefulness * 0.20
            + self.personality_fit * 0.14
            - self.genericness_penalty * 0.10
        )


@dataclass
class FragmentRecord:
    """A salvaged text fragment extracted from a candidate draft."""

    fragment_id: str
    source_candidate_id: str
    text: str = ""
    position: int = 0                      # character offset in source candidate
    scores: FragmentScores = field(default_factory=FragmentScores)
    keep: bool = False


# ── 12. FinalResponseRecord ───────────────────────────────────────────────────

@dataclass
class FinalResponseScores:
    relevance: float = 0.0
    clarity: float = 0.0
    coherence: float = 0.0
    personality_fit: float = 0.0
    usefulness: float = 0.0
    goal_fit: float = 0.0
    genericness_penalty: float = 0.0

    @property
    def composite(self) -> float:
        return (
            self.relevance * 0.24
            + self.clarity * 0.18
            + self.coherence * 0.18
            + self.personality_fit * 0.14
            + self.usefulness * 0.16
            + self.goal_fit * 0.10
            - self.genericness_penalty * 0.10
        )

    @property
    def quality_tier(self) -> str:
        s = self.composite
        if s >= 0.85:
            return "excellent"
        if s >= 0.70:
            return "strong"
        if s >= 0.55:
            return "usable"
        if s >= 0.40:
            return "weak"
        return "reject"


@dataclass
class FinalResponseRecord:
    """The chosen output with source citations and enforcement status."""

    response_id: str
    text: str = ""
    source_candidate_ids: list[str] = field(default_factory=list)
    source_fragment_ids: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    scores: FinalResponseScores = field(default_factory=FinalResponseScores)
    enforcement_passed: bool = False
    enforcement_notes: str = ""
    token_count: int = 0
    created_at: str = field(default_factory=_now_iso)
    turn_id: str = ""
    salvage_path: str = "direct"
    retrieval_confidence: float = 0.0
    mode: str = "knowledge_only"


# ── 13. WritebackRecord ───────────────────────────────────────────────────────

@dataclass
class WritebackRecord:
    """Instructions for updating persistent memory after a turn."""

    turn_id: str
    new_preferences: list[dict[str, Any]] = field(default_factory=list)
    new_facts: list[dict[str, Any]] = field(default_factory=list)
    new_episodes: list[dict[str, Any]] = field(default_factory=list)
    new_patterns: list[dict[str, Any]] = field(default_factory=list)
    thread_updates: dict[str, Any] = field(default_factory=dict)
    records_to_reinforce: list[str] = field(default_factory=list)
    records_to_archive: list[str] = field(default_factory=list)
    records_to_delete: list[str] = field(default_factory=list)


# ── 14. RuntimeTurnState ──────────────────────────────────────────────────────

@dataclass
class RuntimeTurnState:
    """Full transient state for one complete turn execution."""

    turn_id: str
    input_sketch: InputSketch | None = None
    memory_bundle: MemoryActivationBundle | None = None
    scaffold: CognitionScaffold | None = None
    candidates: list[CandidateRecord] = field(default_factory=list)
    fragments: list[FragmentRecord] = field(default_factory=list)
    final_response: FinalResponseRecord | None = None
    writeback: WritebackRecord | None = None
    started_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    total_tokens_used: int = 0
    retrieval_ms: int = 0
    generation_ms: int = 0
    salvage_ms: int = 0
