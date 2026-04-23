"""
File-based persistent memory store for ThoughtForge.

Manages reading/writing of all memory record types to their storage files:
  - personality_core.yaml
  - user_profile_store.jsonl  (preferences + facts)
  - episodic_store.jsonl
  - response_patterns.jsonl
  - active_thread_state.json
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any

import yaml

from thoughtforge.knowledge.models import (
    ActiveThreadStateRecord,
    EpisodicMemoryRecord,
    PersonalityCoreRecord,
    ResponsePatternRecord,
    UserFactRecord,
    UserPreferenceRecord,
)
from thoughtforge.utils.paths import get_memory_dir

logger = logging.getLogger(__name__)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


class MemoryStore:
    """Read/write layer for all persistent memory files."""

    def __init__(self, memory_dir: Path | None = None) -> None:
        self.dir: Path = memory_dir or get_memory_dir()
        self.dir.mkdir(parents=True, exist_ok=True)
        self._personality_path = self.dir / "personality_core.yaml"
        self._profile_path = self.dir / "user_profile_store.jsonl"
        self._episodic_path = self.dir / "episodic_store.jsonl"
        self._patterns_path = self.dir / "response_patterns.jsonl"
        self._thread_path = self.dir / "active_thread_state.json"
        self._tag_index_path = self.dir / "tag_index.json"
        self._recent_queue_path = self.dir / "recent_queue.json"

    # ── Personality Core ───────────────────────────────────────────────────────

    def load_personality_core(self) -> PersonalityCoreRecord | None:
        if not self._personality_path.exists():
            return None
        with self._personality_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data:
            return None
        return PersonalityCoreRecord.from_dict(data)

    def save_personality_core(self, record: PersonalityCoreRecord) -> None:
        with self._personality_path.open("w", encoding="utf-8") as f:
            yaml.safe_dump(record.to_dict(), f, allow_unicode=True, sort_keys=False)
        logger.debug("Saved personality core %s", record.record_id)

    # ── User Profile (preferences + facts combined store) ──────────────────────

    def load_profile_records(self) -> list[UserPreferenceRecord | UserFactRecord]:
        records: list[UserPreferenceRecord | UserFactRecord] = []
        if not self._profile_path.exists():
            return records
        with self._profile_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    rtype = d.get("record_type", "")
                    if rtype == "user_preference":
                        records.append(UserPreferenceRecord.from_dict(d))
                    elif rtype == "user_fact":
                        records.append(UserFactRecord.from_dict(d))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Skipping malformed profile record: %s", e)
        return records

    def append_profile_record(self, record: UserPreferenceRecord | UserFactRecord) -> None:
        with self._profile_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Appended %s record %s", record.record_type, record.record_id)

    def rewrite_profile_store(self, records: list[UserPreferenceRecord | UserFactRecord]) -> None:
        with self._profile_path.open("w", encoding="utf-8") as f:
            for r in records:
                if r.status not in ("archived", "deleted"):
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Rewrote profile store with %d records", len(records))

    # ── Episodic Store ─────────────────────────────────────────────────────────

    def load_episodes(self) -> list[EpisodicMemoryRecord]:
        records: list[EpisodicMemoryRecord] = []
        if not self._episodic_path.exists():
            return records
        with self._episodic_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(EpisodicMemoryRecord.from_dict(d))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Skipping malformed episode record: %s", e)
        return records

    def append_episode(self, record: EpisodicMemoryRecord) -> None:
        with self._episodic_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Appended episode %s", record.record_id)

    def rewrite_episodic_store(self, records: list[EpisodicMemoryRecord]) -> None:
        with self._episodic_path.open("w", encoding="utf-8") as f:
            for r in records:
                if r.status not in ("archived", "deleted"):
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Rewrote episodic store with %d records", len(records))

    # ── Response Patterns ──────────────────────────────────────────────────────

    def load_patterns(self) -> list[ResponsePatternRecord]:
        records: list[ResponsePatternRecord] = []
        if not self._patterns_path.exists():
            return records
        with self._patterns_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                    records.append(ResponsePatternRecord.from_dict(d))
                except (json.JSONDecodeError, TypeError) as e:
                    logger.warning("Skipping malformed pattern record: %s", e)
        return records

    def append_pattern(self, record: ResponsePatternRecord) -> None:
        with self._patterns_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Appended response pattern %s", record.record_id)

    def rewrite_patterns_store(self, records: list[ResponsePatternRecord]) -> None:
        with self._patterns_path.open("w", encoding="utf-8") as f:
            for r in records:
                if r.status not in ("archived", "deleted"):
                    f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        logger.debug("Rewrote patterns store with %d records", len(records))

    # ── Active Thread State ────────────────────────────────────────────────────

    def load_thread_state(self) -> ActiveThreadStateRecord | None:
        if not self._thread_path.exists():
            return None
        try:
            with self._thread_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return ActiveThreadStateRecord.from_dict(data)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Could not load thread state: %s", e)
            return None

    def save_thread_state(self, record: ActiveThreadStateRecord) -> None:
        with self._thread_path.open("w", encoding="utf-8") as f:
            json.dump(record.to_dict(), f, ensure_ascii=False, indent=2)
        logger.debug("Saved thread state %s (priority=%.2f)", record.record_id, record.priority)

    def clear_thread_state(self) -> None:
        if self._thread_path.exists():
            self._thread_path.unlink()
        logger.debug("Cleared active thread state")

    # ── Tag Index ──────────────────────────────────────────────────────────────

    def load_tag_index(self) -> dict[str, list[str]]:
        if not self._tag_index_path.exists():
            return {}
        with self._tag_index_path.open("r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def save_tag_index(self, index: dict[str, list[str]]) -> None:
        with self._tag_index_path.open("w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False)

    def rebuild_tag_index(self) -> dict[str, list[str]]:
        """Rebuild tag → [record_id] index from all live records."""
        index: dict[str, list[str]] = {}

        def _add(record_id: str, tags: list[str]) -> None:
            for tag in tags:
                index.setdefault(tag, [])
                if record_id not in index[tag]:
                    index[tag].append(record_id)

        for r in self.load_profile_records():
            _add(r.record_id, r.tags)
        for r in self.load_episodes():
            _add(r.record_id, r.tags)
        for r in self.load_patterns():
            _add(r.record_id, r.tags)

        self.save_tag_index(index)
        logger.debug("Rebuilt tag index: %d tags", len(index))
        return index

    # ── Recent Queue ───────────────────────────────────────────────────────────

    def load_recent_queue(self) -> list[str]:
        if not self._recent_queue_path.exists():
            return []
        with self._recent_queue_path.open("r", encoding="utf-8") as f:
            return json.load(f)  # type: ignore[no-any-return]

    def save_recent_queue(self, queue: list[str]) -> None:
        with self._recent_queue_path.open("w", encoding="utf-8") as f:
            json.dump(queue, f)

    def push_to_recent_queue(self, record_id: str, max_size: int = 64) -> None:
        queue = self.load_recent_queue()
        if record_id in queue:
            queue.remove(record_id)
        queue.insert(0, record_id)
        self.save_recent_queue(queue[:max_size])

    # ── Factory helpers ────────────────────────────────────────────────────────

    @staticmethod
    def new_preference_id() -> str:
        return _new_id("usr")

    @staticmethod
    def new_fact_id() -> str:
        return _new_id("fct")

    @staticmethod
    def new_episode_id() -> str:
        return _new_id("ep")

    @staticmethod
    def new_pattern_id() -> str:
        return _new_id("pat")

    @staticmethod
    def new_thread_id() -> str:
        return _new_id("thr")

    # ── Bulk load all records ──────────────────────────────────────────────────

    def load_all(self) -> dict[str, Any]:
        return {
            "personality_core": self.load_personality_core(),
            "profile_records": self.load_profile_records(),
            "episodes": self.load_episodes(),
            "patterns": self.load_patterns(),
            "thread_state": self.load_thread_state(),
        }
