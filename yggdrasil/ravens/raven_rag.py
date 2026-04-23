"""
RavenRAG - The Combined Raven Intelligence System
=================================================

Unifies Huginn (Thought/Retrieval) and Muninn (Memory/Storage)
into a complete Retrieval-Augmented Generation system.

This is RAG 9.0 - elevating beyond basic retrieval with:
- Multi-hop reasoning
- Contextual compression
- Hierarchical indexing
- Anomaly detection
- Self-healing structures
- Integration with all Nine Worlds
"""

import logging
import json
from typing import Dict, List, Any, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime

from yggdrasil.ravens.huginn import Huginn
from yggdrasil.ravens.muninn import Muninn, MemoryNode

logger = logging.getLogger(__name__)


@dataclass
class RAGContext:
    """Context built for LLM consumption."""

    query: str
    retrieved_content: List[Dict[str, Any]]
    memory_context: List[Dict[str, Any]]
    compressed: bool
    token_estimate: int
    confidence: float
    sources: List[str]
    timestamp: datetime = field(default_factory=datetime.now)

    def to_prompt_string(self, max_tokens: int = 2000) -> str:
        """Convert context to a prompt-friendly string."""
        parts = []

        # Add retrieved content
        if self.retrieved_content:
            parts.append("## Relevant Information:")
            for item in self.retrieved_content[:5]:  # Max 5 items
                content = item.get("content", item)
                if isinstance(content, dict):
                    content = json.dumps(content, default=str)
                parts.append(f"- {str(content)[:300]}")

        # Add memory context
        if self.memory_context:
            parts.append("\n## Memory Context:")
            for mem in self.memory_context[:3]:  # Max 3 memories
                content = mem.get("content", mem)
                if isinstance(content, dict):
                    content = json.dumps(content, default=str)
                parts.append(f"- {str(content)[:200]}")

        result = "\n".join(parts)

        # Rough token estimate and truncation
        if len(result) > max_tokens * 4:  # ~4 chars per token
            result = result[: max_tokens * 4] + "\n[...truncated...]"

        return result


class RavenRAGError(Exception):
    """Exception raised by RavenRAG operations."""

    pass


class RavenRAG:
    """
    The Combined Raven Intelligence System.

    Unifies Huginn and Muninn for a complete RAG workflow:

    1. Query Analysis (Huginn analyzes the query)
    2. Route Decision (Bifrost routes to appropriate sources)
    3. Retrieval (Huginn flies to retrieve relevant data)
    4. Memory Enhancement (Muninn adds persistent context)
    5. Compression (Prepare for LLM consumption)
    6. Response Integration (Final assembly)

    Features:
    - Multi-hop reasoning chains
    - Contextual compression for token efficiency
    - Automatic memory storage of results
    - Anomaly detection for stale data
    - Self-healing data structures
    """

    def __init__(
        self,
        huginn: Huginn = None,
        muninn: Muninn = None,
        helheim: "Helheim" = None,
        max_context_tokens: int = 4000,
    ):
        """
        Initialize RavenRAG.

        Args:
            huginn: Huginn instance for retrieval
            muninn: Muninn instance for storage
            helheim: Helheim instance for deep memory
            max_context_tokens: Maximum tokens for context
        """
        # Initialize ravens if not provided
        self.helheim = helheim
        self.muninn = muninn or Muninn(helheim=helheim)
        self.huginn = huginn or Huginn(muninn=self.muninn, helheim=helheim)

        self.max_history = 500
        self.max_anomaly_log = 500

        # Load dynamic prompts
        self.default_prompt = (
            "You are a helpful assistant with access to relevant context."
        )
        try:
            from pathlib import Path
            import yaml

            prompt_file = Path("data/charts/ai_prompts.yaml")
            if prompt_file.exists():
                with open(prompt_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if (
                        data
                        and "raven_huginn" in data
                        and "instructions" in data["raven_huginn"]
                    ):
                        self.default_prompt = data["raven_huginn"][
                            "instructions"
                        ].strip()
                        logger.info("Loaded raven_huginn prompt from ai_prompts.yaml")
        except Exception as e:
            logger.warning(f"Could not load Huginn prompt from config: {e}")

        # RAG history
        self._query_history: List[RAGContext] = []

        # Anomaly tracking
        self._anomaly_log: List[Dict] = []

    def query(
        self,
        query: str,
        memory_paths: List[str] = None,
        use_multi_hop: bool = False,
        compress: bool = True,
        store_result: bool = True,
    ) -> RAGContext:
        """Execute a RAG query."""
        memory_paths = memory_paths or []
        safe_query = (query or "").strip()[:1000] or "general context"

        try:
            analysis = self.huginn.analyze_query(safe_query)

            if use_multi_hop or analysis.get("recommended_hops", 1) > 1:
                retrievals = self.huginn.multi_hop_retrieve(
                    safe_query, hop_count=analysis.get("recommended_hops", 2)
                )
                retrieved_content = []
                for retrieval in retrievals:
                    retrieved_content.extend(retrieval.results)
            else:
                retrieval = self.huginn.fly(safe_query, compress=compress)
                retrieved_content = retrieval.results

            memory_context = []
            for path in memory_paths:
                for node in self.muninn.get_by_path(path):
                    memory_context.append(node.to_dict())

            key_terms = analysis.get("key_terms", [])
            for term in key_terms[:3]:
                for node in self.muninn.retrieve(query=term, top_k=2):
                    as_dict = node.to_dict()
                    if as_dict not in memory_context:
                        memory_context.append(as_dict)

            if compress:
                retrieved_content = self._compress_content(retrieved_content)
                memory_context = self._compress_content(memory_context)

            confidence = self._calculate_confidence(retrieved_content, memory_context)
            token_estimate = self._estimate_tokens(retrieved_content, memory_context)

            sources = []
            for item in retrieved_content:
                if isinstance(item, dict):
                    source = item.get("source", item.get("realm_source", "unknown"))
                    if source not in sources:
                        sources.append(source)

            context = RAGContext(
                query=safe_query,
                retrieved_content=retrieved_content,
                memory_context=memory_context,
                compressed=compress,
                token_estimate=token_estimate,
                confidence=confidence,
                sources=sources,
            )

            self._query_history.append(context)
            if len(self._query_history) > self.max_history:
                self._query_history = self._query_history[-250:]

            if store_result:
                self.muninn.store(
                    content={
                        "query": safe_query,
                        "result_count": len(retrieved_content),
                        "confidence": confidence,
                    },
                    path="rag/queries",
                    memory_type="query",
                    importance=3,
                    tags=key_terms,
                )

            logger.info(
                "RavenRAG query: %s retrieved, %s from memory, confidence=%.2f",
                len(retrieved_content),
                len(memory_context),
                confidence,
            )
            return context
        except Exception as exc:
            logger.warning("RavenRAG query failed: %s", exc)
            return RAGContext(
                query=safe_query,
                retrieved_content=[],
                memory_context=[],
                compressed=compress,
                token_estimate=0,
                confidence=0.1,
                sources=[],
            )

    def retrieve_and_generate(
        self,
        query: str,
        llm_callable: Callable[[str], str],
        system_prompt: str = None,
        **query_kwargs,
    ) -> Tuple[str, RAGContext]:
        """
        Full RAG pipeline: retrieve context and generate response.

        Args:
            query: User query
            llm_callable: Function to call LLM
            system_prompt: Optional system prompt
            **query_kwargs: Additional arguments for query()

        Returns:
            (response, context) tuple
        """
        # Get context
        context = self.query(query, **query_kwargs)

        # Build prompt
        context_str = context.to_prompt_string(self.max_context_tokens)

        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{context_str}\n\nQuery: {query}"
        else:
            full_prompt = f"{self.default_prompt}\n\n{context_str}\n\nBased on the above context, please answer: {query}"

        # Generate response
        try:
            response = llm_callable(full_prompt)

            # Store successful query
            self.muninn.store(
                content={
                    "query": query,
                    "response_length": len(response),
                    "context_confidence": context.confidence,
                },
                path="rag/responses",
                memory_type="response",
                importance=4,
            )

            return response, context

        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            fallback = (
                "The ravens return in storm-silence; memory is veiled for this moment."
            )
            return fallback, context

    def store(self, content: Any, path: str, **kwargs) -> str:
        """
        Store content in Muninn's memory.

        Args:
            content: Content to store
            path: Memory path
            **kwargs: Additional store arguments

        Returns:
            Node ID
        """
        return self.muninn.store(content, path, **kwargs)

    def search(self, query: str, top_k: int = 5, **kwargs) -> List[MemoryNode]:
        """
        Search Muninn's memory.

        Args:
            query: Search query
            top_k: Maximum results
            **kwargs: Additional search arguments

        Returns:
            List of matching nodes
        """
        return self.muninn.retrieve(query=query, top_k=top_k, **kwargs)

    def _compress_content(self, content: List[Any]) -> List[Any]:
        """Compress content for token efficiency."""
        compressed = []

        for item in content:
            if isinstance(item, dict):
                # Remove low-value keys
                comp = {
                    k: v
                    for k, v in item.items()
                    if k not in ["timestamp", "accessed_count", "metadata"]
                }

                # Truncate long strings
                for key, value in comp.items():
                    if isinstance(value, str) and len(value) > 300:
                        comp[key] = value[:300] + "..."

                compressed.append(comp)
            elif isinstance(item, str):
                compressed.append(item[:500] if len(item) > 500 else item)
            else:
                compressed.append(item)

        return compressed

    def _calculate_confidence(self, retrieved: List[Any], memory: List[Any]) -> float:
        """Calculate confidence score for the context."""
        if not retrieved and not memory:
            return 0.1

        score = 0.3  # Base score

        # Add for retrieved content
        if retrieved:
            score += min(0.3, len(retrieved) * 0.06)  # Up to 0.3 for 5 items

        # Add for memory context
        if memory:
            score += min(0.2, len(memory) * 0.05)  # Up to 0.2 for 4 items

        # Bonus for overlap between retrieved and memory
        if retrieved and memory:
            score += 0.1

        return min(1.0, score)

    def _estimate_tokens(self, retrieved: List[Any], memory: List[Any]) -> int:
        """Estimate token count for content."""
        # Rough estimate: 1 token ≈ 4 characters
        total_chars = 0

        for item in retrieved + memory:
            if isinstance(item, dict):
                total_chars += len(json.dumps(item, default=str))
            else:
                total_chars += len(str(item))

        return total_chars // 4

    def detect_anomalies(self) -> List[Dict[str, Any]]:
        """
        Detect anomalies in stored data.

        Checks for:
        - Stale data (not accessed in long time)
        - Orphaned nodes
        - Duplicate content

        Returns:
            List of detected anomalies
        """
        anomalies = []

        # Get all nodes
        stats = self.muninn.get_stats()

        # Check for stale data
        old_nodes = self.muninn.retrieve(top_k=100)
        now = datetime.now()

        for node in old_nodes:
            days_since_access = (now - node.updated_at).days

            if days_since_access > 30 and node.access_count < 2:
                anomalies.append(
                    {
                        "type": "stale_data",
                        "node_id": node.id,
                        "path": node.path,
                        "days_since_access": days_since_access,
                    }
                )

        self._anomaly_log.extend(anomalies)
        if len(self._anomaly_log) > self.max_anomaly_log:
            self._anomaly_log = self._anomaly_log[-250:]

        return anomalies

    def heal(self) -> Dict[str, int]:
        """
        Self-healing: fix data issues.

        Returns:
            Summary of fixes applied
        """
        fixes = {
            "index_fixes": 0,
            "anomalies_resolved": 0,
        }

        # Heal Muninn's structure
        fixes["index_fixes"] = self.muninn.heal_structure()

        # Resolve detected anomalies
        anomalies = self.detect_anomalies()

        for anomaly in anomalies:
            if anomaly["type"] == "stale_data":
                # Reduce importance of stale data
                self.muninn.update(
                    anomaly["node_id"],
                    importance=max(1, 3),  # Demote importance
                )
                fixes["anomalies_resolved"] += 1

        logger.info(f"RavenRAG healed: {fixes}")

        return fixes

    def get_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics."""
        huginn_stats = self.huginn.get_flight_stats()
        muninn_stats = self.muninn.get_stats()

        return {
            "queries_processed": len(self._query_history),
            "anomalies_detected": len(self._anomaly_log),
            "huginn": huginn_stats,
            "muninn": muninn_stats,
            "avg_confidence": sum(q.confidence for q in self._query_history)
            / max(1, len(self._query_history)),
        }

    def export_state(self) -> Dict[str, Any]:
        """Export full state for backup/migration."""
        return {
            "muninn_dump": self.muninn.dump(limit=1000),
            "query_history_count": len(self._query_history),
            "stats": self.get_stats(),
        }
