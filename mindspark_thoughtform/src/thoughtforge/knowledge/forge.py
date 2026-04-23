"""
KnowledgeForge — the hybrid SQL + vector retrieval engine for ThoughtForge.

Implements the full sovereign RAG retrieval pipeline:
  1. SQL pre-filter (precise relational lookups via FTS5 + direct queries)
  2. Vector augmentation (semantic similarity via sentence-transformers)
  3. Score fusion (weighted combination per spec)
  4. Ranked result bundle assembly (MemoryActivationBundle)

Zero internet dependency. All knowledge is local SQLite.
"""

from __future__ import annotations

import logging
import re
import sqlite3
from pathlib import Path
from typing import Any

from thoughtforge.etl.embeddings import (
    encode_single,
    vector_search_entities,
    vector_search_reference,
)
from thoughtforge.etl.schema import get_connection
from thoughtforge.knowledge.models import ActivatedRecord, MemoryActivationBundle
from thoughtforge.knowledge.scoring import (
    MIN_MEMORY_SCORE,
    RetrievalDimensions,
    compute_recency_score,
    score_retrieval,
)
from thoughtforge.utils.paths import get_knowledge_db_path

logger = logging.getLogger(__name__)


class KnowledgeForge:
    """
    Hybrid SQL + vector retrieval engine over the ThoughtForge knowledge database.
    Fully offline — no network calls.
    """

    def __init__(
        self,
        db_path: Path | None = None,
        model_name: str = "all-MiniLM-L6-v2",
    ) -> None:
        self.db_path = db_path or get_knowledge_db_path()
        self.model_name = model_name

    # ── Primary retrieval API ──────────────────────────────────────────────────

    def retrieve(
        self,
        query: str,
        path: str = "hybrid",       # "sql" | "vector" | "hybrid"
        top_k: int = 10,
        min_score: float = MIN_MEMORY_SCORE,
        sources: list[str] | None = None,  # None = all; ["wikidata", "conceptnet", ...]
    ) -> MemoryActivationBundle:
        """
        Main retrieval entry point. Returns a MemoryActivationBundle with
        ranked records from SQL and/or vector search.

        Args:
            query:      The user's query text
            path:       "sql" | "vector" | "hybrid"
            top_k:      Max records to return in the bundle
            min_score:  Minimum composite score threshold
            sources:    Optional list of source filters
        """
        records: list[dict[str, Any]] = []

        if path in ("sql", "hybrid"):
            sql_results = self.sql_retrieve(query, top_k=top_k * 2, sources=sources)
            records.extend(sql_results)

        if path in ("vector", "hybrid"):
            vec_results = self.vector_retrieve(query, top_k=top_k, sources=sources)
            for r in vec_results:
                # Avoid duplicates from SQL pass
                if not any(x.get("qid") == r.get("qid") for x in records):
                    records.append(r)

        # Score and rank
        scored = self._score_records(records, query)
        scored = [r for r in scored if r["_composite_score"] >= min_score]
        scored.sort(key=lambda x: x["_composite_score"], reverse=True)
        scored = scored[:top_k]

        bundle = self._build_bundle(scored)
        logger.debug(
            "Retrieved %d records (path=%s, min_score=%.2f)",
            len(bundle.activated_records), path, min_score,
        )
        return bundle

    # ── SQL retrieval ──────────────────────────────────────────────────────────

    def sql_retrieve(
        self,
        query: str,
        top_k: int = 15,
        sources: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        SQL-based retrieval using FTS5 full-text search across all knowledge tables.
        Returns raw result dicts with source metadata.
        """
        results: list[dict[str, Any]] = []
        conn = get_connection(self.db_path, read_only=True)

        try:
            # Sanitize query for FTS5
            fts_query = self._to_fts5_query(query)

            # 1. Entity FTS5 search
            if not sources or "wikidata" in sources or "entities" in sources:
                try:
                    rows = conn.execute(
                        """
                        SELECT e.qid, e.label_en, e.description_en, e.popularity_score,
                               bm25(entities_fts) AS fts_score
                        FROM entities_fts
                        JOIN entities e ON e.qid = entities_fts.qid
                        WHERE entities_fts MATCH ?
                        ORDER BY fts_score
                        LIMIT ?
                        """,
                        (fts_query, top_k),
                    ).fetchall()
                    for row in rows:
                        results.append({
                            "qid": row["qid"],
                            "label_en": row["label_en"],
                            "description_en": row["description_en"],
                            "popularity_score": row["popularity_score"] or 0.0,
                            "fts_score": abs(row["fts_score"]),
                            "source": "wikidata",
                            "record_type": "entity",
                        })
                except sqlite3.OperationalError as e:
                    logger.debug("Entity FTS5 query failed: %s", e)

            # 2. Reference chunk FTS5 search
            if not sources or "reference" in sources:
                try:
                    rows = conn.execute(
                        """
                        SELECT rc.chunk_id, rc.source_file, rc.title, rc.content, rc.tags,
                               bm25(reference_fts) AS fts_score
                        FROM reference_fts
                        JOIN reference_chunks rc ON rc.rowid = reference_fts.rowid
                        WHERE reference_fts MATCH ?
                        ORDER BY fts_score
                        LIMIT ?
                        """,
                        (fts_query, top_k // 2),
                    ).fetchall()
                    for row in rows:
                        results.append({
                            "chunk_id": row["chunk_id"],
                            "source_file": row["source_file"],
                            "title": row["title"],
                            "content": row["content"][:500],
                            "tags": row["tags"],
                            "fts_score": abs(row["fts_score"]),
                            "source": "reference",
                            "record_type": "reference_chunk",
                        })
                except sqlite3.OperationalError as e:
                    logger.debug("Reference FTS5 query failed: %s", e)

            # 3. ConceptNet commonsense search
            if not sources or "conceptnet" in sources:
                terms = self._extract_key_terms(query)
                if terms:
                    placeholders = ",".join("?" for _ in terms)
                    try:
                        rows = conn.execute(
                            f"""
                            SELECT concept1, relation, concept2, weight
                            FROM conceptnet_edges
                            WHERE concept1 IN ({placeholders}) OR concept2 IN ({placeholders})
                            ORDER BY weight DESC
                            LIMIT ?
                            """,
                            terms + terms + [top_k // 3],
                        ).fetchall()
                        for row in rows:
                            results.append({
                                "content": f"{row['concept1']} {row['relation']} {row['concept2']}",
                                "label_en": row["concept1"],
                                "weight": row["weight"],
                                "fts_score": row["weight"],
                                "source": "conceptnet",
                                "record_type": "concept_edge",
                            })
                    except sqlite3.OperationalError as e:
                        logger.debug("ConceptNet query failed: %s", e)

            # 4. GeoNames location search (if query mentions places)
            if not sources or "geonames" in sources:
                terms = self._extract_key_terms(query, max_terms=3)
                if terms:
                    try:
                        term = terms[0]
                        rows = conn.execute(
                            """
                            SELECT geonames_id, name, country_code, feature_class, population
                            FROM geonames_places
                            WHERE name LIKE ?
                            ORDER BY population DESC
                            LIMIT ?
                            """,
                            (f"%{term}%", top_k // 5),
                        ).fetchall()
                        for row in rows:
                            results.append({
                                "geonames_id": row["geonames_id"],
                                "label_en": row["name"],
                                "description_en": f"{row['feature_class']} in {row['country_code']}, pop {row['population']}",
                                "fts_score": 0.5,
                                "source": "geonames",
                                "record_type": "place",
                            })
                    except sqlite3.OperationalError as e:
                        logger.debug("GeoNames query failed: %s", e)

        finally:
            conn.close()

        return results

    # ── Vector retrieval ───────────────────────────────────────────────────────

    def vector_retrieve(
        self,
        query: str,
        top_k: int = 10,
        sources: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Vector-based semantic retrieval using cosine similarity on pre-computed embeddings.
        """
        results: list[dict[str, Any]] = []

        if not sources or "wikidata" in sources or "entities" in sources:
            entity_results = vector_search_entities(
                query,
                db_path=self.db_path,
                model_name=self.model_name,
                top_k=top_k,
                min_score=0.3,
            )
            results.extend(entity_results)

        if not sources or "reference" in sources:
            ref_results = vector_search_reference(
                query,
                db_path=self.db_path,
                model_name=self.model_name,
                top_k=top_k // 2,
                min_score=0.3,
            )
            results.extend(ref_results)

        return results

    # ── Scoring ────────────────────────────────────────────────────────────────

    def _score_records(
        self,
        records: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        """
        Compute composite retrieval scores for all records using the spec formula:
          score = semantic_similarity * 0.35 + tone_similarity * 0.20 +
                  preference_relevance * 0.20 + recency * 0.10 + importance * 0.15
        """
        for record in records:
            # Semantic similarity: prefer vector score if available, fall back to FTS
            sim = record.get("similarity", 0.0)
            if sim == 0.0:
                fts = record.get("fts_score", 0.0)
                sim = min(fts / 20.0, 1.0) if fts > 0 else 0.0

            # Importance proxy: popularity for entities, weight for conceptnet
            importance = min(record.get("popularity_score", 0.0) + record.get("weight", 0.5), 1.0)

            # Recency: knowledge graph records are static; use source-based proxy
            source = record.get("source", "wikidata")
            recency = {"reference": 0.9, "wikidata": 0.7, "conceptnet": 0.8,
                       "geonames": 0.75, "dbpedia": 0.65}.get(source, 0.7)

            dims = RetrievalDimensions(
                semantic_similarity=sim,
                tone_similarity=0.5,          # neutral default — no tone metadata at DB level
                preference_relevance=0.5,      # neutral default
                recency=recency,
                importance=importance,
            )
            record["_composite_score"] = score_retrieval(dims, "user_fact")

        return records

    # ── Bundle assembly ────────────────────────────────────────────────────────

    def _build_bundle(self, scored_records: list[dict[str, Any]]) -> MemoryActivationBundle:
        """Assemble a MemoryActivationBundle from scored result dicts."""
        activated: list[ActivatedRecord] = []
        total_score = 0.0

        for record in scored_records:
            cue = self._build_cue(record)
            record_type = record.get("record_type", "entity")
            record_id = (
                record.get("qid")
                or str(record.get("chunk_id", ""))
                or record.get("label_en", "")[:16]
            )
            score = record.get("_composite_score", 0.0)
            total_score += score

            activated.append(ActivatedRecord(
                record_id=record_id,
                record_type=record_type,
                score=round(score, 4),
                cue=cue,
                raw=record,
            ))

        avg_confidence = total_score / len(activated) if activated else 0.0

        return MemoryActivationBundle(
            activated_records=activated,
            total_retrieved=len(activated),
            retrieval_confidence=round(avg_confidence, 4),
        )

    @staticmethod
    def _build_cue(record: dict[str, Any]) -> str:
        """Build a compressed 5–18 word cue from a knowledge record."""
        label = record.get("label_en") or record.get("title") or ""
        desc = record.get("description_en") or record.get("content", "")
        source = record.get("source", "")

        if desc:
            # Take first 80 chars of description, trim to word boundary
            short_desc = desc[:80].rsplit(" ", 1)[0]
            cue = f"{label}: {short_desc}" if label else short_desc
        elif label:
            cue = f"{source}/{label}" if source else label
        else:
            cue = record.get("content", "")[:80]

        # Trim to max 18 words
        words = cue.split()[:18]
        return " ".join(words)

    # ── Query helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _to_fts5_query(query: str) -> str:
        """Convert a natural language query to an FTS5-safe search string."""
        # Remove FTS5 special chars, keep alphanumeric + spaces
        clean = re.sub(r'[^\w\s]', ' ', query)
        terms = [t for t in clean.split() if len(t) > 2]
        if not terms:
            return '""'
        # Use implicit AND (FTS5 default) for precision
        return " ".join(terms[:8])

    @staticmethod
    def _extract_key_terms(query: str, max_terms: int = 5) -> list[str]:
        """Extract key noun-like terms from a query for exact-match lookups."""
        clean = re.sub(r'[^\w\s]', ' ', query.lower())
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                     "being", "have", "has", "had", "do", "does", "did", "will",
                     "would", "could", "should", "may", "might", "to", "of",
                     "and", "or", "but", "in", "on", "at", "by", "for", "with",
                     "about", "what", "who", "how", "when", "where", "why"}
        terms = [w for w in clean.split() if w not in stopwords and len(w) > 2]
        return terms[:max_terms]
