"""
Memory lifecycle management and pruning for ThoughtForge.

Implements all four pruning modes (light, routine, heavy, emergency),
recency decay, reinforcement, consolidation, and retention class enforcement.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal, Union

from thoughtforge.knowledge.models import (
    ActiveThreadStateRecord,
    EpisodicMemoryRecord,
    RecordStatus,
    ResponsePatternRecord,
    UserFactRecord,
    UserPreferenceRecord,
)
from thoughtforge.knowledge.scoring import (
    MIN_MEMORY_SCORE,
    PruneComponents,
    SurvivalComponents,
    compute_prune_score,
    compute_recency_score,
    compute_survival_score,
)
from thoughtforge.knowledge.store import MemoryStore

logger = logging.getLogger(__name__)

PruneMode = Literal["light", "routine", "heavy", "emergency"]

ProfileRecord = Union[UserPreferenceRecord, UserFactRecord]

# ── Pruning thresholds per mode ────────────────────────────────────────────────

ARCHIVE_THRESHOLDS: dict[str, dict[str, float]] = {
    "light":     {"preference": 0.85, "fact": 0.85, "episode": 0.85, "pattern": 0.85},
    "routine":   {"preference": 0.72, "fact": 0.72, "episode": 0.68, "pattern": 0.70},
    "heavy":     {"preference": 0.60, "fact": 0.58, "episode": 0.55, "pattern": 0.58},
    "emergency": {"preference": 0.40, "fact": 0.40, "episode": 0.35, "pattern": 0.40},
}

DELETE_THRESHOLDS: dict[str, dict[str, float]] = {
    "light":     {"preference": 0.95, "fact": 0.95, "episode": 0.95, "pattern": 0.95},
    "routine":   {"preference": 0.86, "fact": 0.86, "episode": 0.82, "pattern": 0.84},
    "heavy":     {"preference": 0.75, "fact": 0.72, "episode": 0.70, "pattern": 0.72},
    "emergency": {"preference": 0.55, "fact": 0.55, "episode": 0.50, "pattern": 0.55},
}

# Store caps
STORE_CAPS: dict[str, dict[str, int]] = {
    "user_preference": {"soft": 128, "hard": 256},
    "user_fact":       {"soft": 128, "hard": 256},
    "episode":         {"soft": 256, "hard": 512},
    "response_pattern":{"soft": 128, "hard": 256},
    "recent_queue":    {"soft": 64,  "hard": 128},
    "open_loops":      {"soft": 6,   "hard": 8},
}


def _age_days(timestamp_iso: str) -> float:
    """Return age in days from an ISO 8601 UTC timestamp to now."""
    try:
        ts = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        return max(0.0, (now - ts).total_seconds() / 86400.0)
    except (ValueError, AttributeError):
        return 30.0  # default age on parse failure


def _build_prune_components(
    record: ProfileRecord | EpisodicMemoryRecord | ResponsePatternRecord,
    age_days: float,
    redundancy: float = 0.0,
    future_relevance: float = 0.5,
) -> PruneComponents:
    """Build PruneComponents from a live record."""
    recency = compute_recency_score(age_days, getattr(record, "record_type", "episode"))
    staleness = 1.0 - recency
    confidence = getattr(record, "confidence", 0.5)
    importance = getattr(record, "importance", 0.5)
    quality = getattr(record, "quality", confidence)
    times_reinforced = getattr(record, "times_reinforced", 0)
    reinforcement_signal = min(times_reinforced / 10.0, 1.0)

    return PruneComponents(
        staleness=staleness,
        redundancy=redundancy,
        low_confidence=1.0 - confidence,
        low_importance=1.0 - importance,
        low_quality=1.0 - quality,
        low_future_relevance=1.0 - future_relevance,
        low_reinforcement=1.0 - reinforcement_signal,
    )


def _build_survival_components(
    record: ProfileRecord | EpisodicMemoryRecord | ResponsePatternRecord,
    age_days: float,
    future_relevance: float = 0.5,
) -> SurvivalComponents:
    record_type = getattr(record, "record_type", "episode")
    recency = compute_recency_score(age_days, record_type)
    times_reinforced = getattr(record, "times_reinforced", 0)
    reinforcement_strength = min(times_reinforced / 10.0, 1.0)
    return SurvivalComponents(
        importance=getattr(record, "importance", 0.5),
        confidence=getattr(record, "confidence", 0.5),
        quality=getattr(record, "quality", getattr(record, "confidence", 0.5)),
        future_relevance=future_relevance,
        recency=recency,
        reinforcement_strength=reinforcement_strength,
    )


class MemoryLifecycle:
    """
    Manages memory lifecycle: pruning, reinforcement, consolidation, and decay.
    All state changes are persisted via MemoryStore.
    """

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()

    # ── Public pruning API ─────────────────────────────────────────────────────

    def prune(self, mode: PruneMode = "routine") -> dict[str, int]:
        """
        Run a pruning pass in the given mode.
        Returns counts: {archived: N, deleted: N, deduplicated: N}.
        """
        logger.info("Starting %s prune pass", mode)
        counts: dict[str, int] = {"archived": 0, "deleted": 0, "deduplicated": 0}

        counts = self._accumulate(counts, self._prune_profile(mode))
        counts = self._accumulate(counts, self._prune_episodes(mode))
        counts = self._accumulate(counts, self._prune_patterns(mode))
        self._prune_thread_state()

        if mode in ("routine", "heavy", "emergency"):
            self.store.rebuild_tag_index()

        logger.info(
            "%s prune complete — archived=%d, deleted=%d, deduplicated=%d",
            mode, counts["archived"], counts["deleted"], counts["deduplicated"],
        )
        return counts

    def prune_light(self) -> dict[str, int]:
        return self.prune("light")

    def prune_routine(self) -> dict[str, int]:
        return self.prune("routine")

    def prune_heavy(self) -> dict[str, int]:
        return self.prune("heavy")

    def prune_emergency(self) -> dict[str, int]:
        return self.prune("emergency")

    # ── Reinforcement ──────────────────────────────────────────────────────────

    def reinforce(self, record_id: str, signal_strength: float = 1.0) -> bool:
        """
        Apply reinforcement to a record by ID.
        Searches across all stores; returns True if found and updated.
        """
        from thoughtforge.knowledge.scoring import (
            REINFORCE_CONFIDENCE_DELTA,
            REINFORCE_IMPORTANCE_DELTA,
            REINFORCE_QUALITY_DELTA,
        )

        # Profile records
        profile = self.store.load_profile_records()
        for r in profile:
            if r.record_id == record_id:
                r.confidence = min(1.0, r.confidence + REINFORCE_CONFIDENCE_DELTA * signal_strength)
                r.importance = min(1.0, r.importance + REINFORCE_IMPORTANCE_DELTA * signal_strength)
                r.times_reinforced += 1
                r.status = "reinforced"
                from datetime import datetime, timezone
                r.updated_at = datetime.now(timezone.utc).isoformat()
                self.store.rewrite_profile_store(profile)
                logger.debug("Reinforced profile record %s", record_id)
                return True

        # Episodes
        episodes = self.store.load_episodes()
        for ep in episodes:
            if ep.record_id == record_id:
                ep.confidence = min(1.0, ep.confidence + REINFORCE_CONFIDENCE_DELTA * signal_strength)
                ep.importance = min(1.0, ep.importance + REINFORCE_IMPORTANCE_DELTA * signal_strength)
                ep.quality = min(1.0, ep.quality + REINFORCE_QUALITY_DELTA * signal_strength)
                ep.times_reinforced += 1
                ep.status = "reinforced"
                from datetime import datetime, timezone
                ep.updated_at = datetime.now(timezone.utc).isoformat()
                self.store.rewrite_episodic_store(episodes)
                logger.debug("Reinforced episode %s", record_id)
                return True

        # Patterns
        patterns = self.store.load_patterns()
        for p in patterns:
            if p.record_id == record_id:
                p.quality = min(1.0, p.quality + REINFORCE_QUALITY_DELTA * signal_strength)
                p.times_successful += 1
                p.times_reinforced += 1
                p.status = "reinforced"
                from datetime import datetime, timezone
                p.updated_at = datetime.now(timezone.utc).isoformat()
                self.store.rewrite_patterns_store(patterns)
                logger.debug("Reinforced pattern %s", record_id)
                return True

        logger.debug("Reinforce: record not found — %s", record_id)
        return False

    # ── Thread state cooling ───────────────────────────────────────────────────

    def cool_thread(self) -> None:
        """Apply one turn of cooling to the active thread state."""
        thread = self.store.load_thread_state()
        if thread is None:
            return
        thread.cool_down()
        if thread.status == "stale":
            self.store.clear_thread_state()
            logger.debug("Thread state %s expired and cleared", thread.record_id)
        else:
            self.store.save_thread_state(thread)

    # ── Internal pruning helpers ───────────────────────────────────────────────

    def _prune_profile(self, mode: PruneMode) -> dict[str, int]:
        records = self.store.load_profile_records()
        archive_t = ARCHIVE_THRESHOLDS[mode]
        delete_t = DELETE_THRESHOLDS[mode]
        archived = deleted = deduped = 0

        # Deduplication: mark lower-quality duplicates
        seen: dict[str, str] = {}  # key -> best record_id
        for r in records:
            if r.retention_class == "protected":
                continue
            key = f"{getattr(r, 'category', '')}|{'|'.join(sorted(r.tags))}"
            if key in seen:
                # Keep the one with higher confidence
                existing = next((x for x in records if x.record_id == seen[key]), None)
                if existing and r.confidence > existing.confidence:
                    existing.status = "deleted"
                    seen[key] = r.record_id
                    deleted += 1
                else:
                    r.status = "deleted"
                    deleted += 1
                deduped += 1
            else:
                seen[key] = r.record_id

        # Score and threshold
        rtype_map = {"user_preference": "preference", "user_fact": "fact"}
        for r in records:
            if r.status in ("archived", "deleted") or r.retention_class == "protected":
                continue
            rtype_key = rtype_map.get(r.record_type, "preference")
            age = _age_days(r.last_used_at)
            pc = _build_prune_components(r, age)
            score = compute_prune_score(pc)

            if score >= delete_t[rtype_key]:
                r.status = "deleted"
                deleted += 1
            elif score >= archive_t[rtype_key]:
                r.status = "archived"
                archived += 1

        # Hard cap enforcement
        live = [r for r in records if r.status not in ("archived", "deleted")]
        prefs = [r for r in live if r.record_type == "user_preference"]
        facts = [r for r in live if r.record_type == "user_fact"]

        deleted += self._enforce_cap(prefs, STORE_CAPS["user_preference"]["hard"], records)
        deleted += self._enforce_cap(facts, STORE_CAPS["user_fact"]["hard"], records)

        self.store.rewrite_profile_store(records)
        return {"archived": archived, "deleted": deleted, "deduplicated": deduped}

    def _prune_episodes(self, mode: PruneMode) -> dict[str, int]:
        episodes = self.store.load_episodes()
        archive_t = ARCHIVE_THRESHOLDS[mode]["episode"]
        delete_t = DELETE_THRESHOLDS[mode]["episode"]
        archived = deleted = 0

        for ep in episodes:
            if ep.status in ("archived", "deleted") or ep.retention_class == "protected":
                continue
            age = _age_days(ep.last_used_at)
            pc = _build_prune_components(ep, age)
            score = compute_prune_score(pc)

            if score >= delete_t:
                ep.status = "deleted"
                deleted += 1
            elif score >= archive_t:
                ep.status = "archived"
                archived += 1

        live = [ep for ep in episodes if ep.status not in ("archived", "deleted")]
        deleted += self._enforce_cap(live, STORE_CAPS["episode"]["hard"], episodes)

        self.store.rewrite_episodic_store(episodes)
        return {"archived": archived, "deleted": deleted, "deduplicated": 0}

    def _prune_patterns(self, mode: PruneMode) -> dict[str, int]:
        patterns = self.store.load_patterns()
        archive_t = ARCHIVE_THRESHOLDS[mode]["pattern"]
        delete_t = DELETE_THRESHOLDS[mode]["pattern"]
        archived = deleted = 0

        for p in patterns:
            if p.status in ("archived", "deleted") or p.retention_class == "protected":
                continue
            age = _age_days(p.last_used_at)
            pc = _build_prune_components(p, age)
            score = compute_prune_score(pc)

            if score >= delete_t:
                p.status = "deleted"
                deleted += 1
            elif score >= archive_t:
                p.status = "archived"
                archived += 1

        live = [p for p in patterns if p.status not in ("archived", "deleted")]
        deleted += self._enforce_cap(live, STORE_CAPS["response_pattern"]["hard"], patterns)

        self.store.rewrite_patterns_store(patterns)
        return {"archived": archived, "deleted": deleted, "deduplicated": 0}

    def _prune_thread_state(self) -> None:
        thread = self.store.load_thread_state()
        if thread is None:
            return
        # Enforce open_loops hard cap
        if len(thread.open_loops) > STORE_CAPS["open_loops"]["hard"]:
            thread.open_loops = thread.open_loops[:STORE_CAPS["open_loops"]["soft"]]
            self.store.save_thread_state(thread)
            logger.debug("Trimmed open_loops to soft cap %d", STORE_CAPS["open_loops"]["soft"])

    def _enforce_cap(
        self,
        live_records: list[Any],
        hard_cap: int,
        all_records: list[Any],
    ) -> int:
        """Mark lowest-survival-score records as deleted until under hard cap."""
        if len(live_records) <= hard_cap:
            return 0

        scored = []
        for r in live_records:
            age = _age_days(getattr(r, "last_used_at", ""))
            sc = _build_survival_components(r, age)
            survival = compute_survival_score(sc)
            scored.append((survival, r))

        scored.sort(key=lambda x: x[0])
        to_delete = len(live_records) - hard_cap
        deleted = 0
        for _, r in scored[:to_delete]:
            r.status = "deleted"
            deleted += 1

        logger.debug("Hard cap enforcement: deleted %d records", deleted)
        return deleted

    @staticmethod
    def _accumulate(base: dict[str, int], extra: dict[str, int]) -> dict[str, int]:
        return {k: base.get(k, 0) + extra.get(k, 0) for k in set(base) | set(extra)}
