"""
Huginn - The Thought Raven
==========================

Odin's raven of Thought. Flies ahead to scout and retrieve,
bringing back only what is needed for the current query.

Huginn provides the FOCUS. By acting as the scout, he prevents
the main model from getting "distracted" by the entire world.
He only brings back the specific "eye-witness" data needed
for the current thought.

Features:
- Dynamic query routing
- Hierarchical retrieval
- Context compression
- Multi-hop reasoning
- Adaptive search
"""

import logging
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Result from a Huginn retrieval flight."""
    query: str
    results: List[Dict[str, Any]]
    relevance_scores: List[float]
    source_realm: str
    retrieval_time: float
    compressed: bool
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class Huginn:
    """
    The Thought Raven - Dynamic Querying and Retrieval.
    
    Huginn scouts ahead through the branches of Yggdrasil,
    bringing back only the relevant information needed
    for the current thought/query.
    
    Features:
    - Query analysis and routing
    - Hierarchical index traversal
    - Context compression for token efficiency
    - Multi-hop reasoning chains
    - Adaptive retrieval strategies
    """
    
    def __init__(
        self,
        muninn: "Muninn" = None,
        helheim: "Helheim" = None,
        vectorizer: Any = None
    ):
        """
        Initialize Huginn.
        
        Args:
            muninn: Reference to Muninn for coordinated retrieval
            helheim: Reference to Helheim memory world
            vectorizer: Optional vectorizer for semantic search
        """
        self.muninn = muninn
        self.helheim = helheim
        self.vectorizer = vectorizer
        
        # Flight history
        self._flight_history: List[RetrievalResult] = []
        
        # Route cache to avoid redundant flights
        self._route_cache: Dict[str, str] = {}
        
        # Import optional vectorizer
        self._tfidf = None
        self._cosine = None
        self.max_results_cap = 50
        self.max_query_chars = 1000
        self._try_import_vectorizer()

    def _normalize_query(self, query: str) -> str:
        """Normalize incoming query text to a safe bounded string."""
        return (query or "").strip()[:self.max_query_chars]
    
    def _try_import_vectorizer(self):
        """Try to import TF-IDF vectorizer."""
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity
            self._tfidf = TfidfVectorizer(max_features=1000)
            self._cosine = cosine_similarity
            logger.debug("Huginn: TF-IDF vectorizer available")
        except ImportError:
            logger.debug("Huginn: TF-IDF not available, using keyword matching")
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a query to determine retrieval strategy.
        
        Args:
            query: The query to analyze
            
        Returns:
            Analysis dict with strategy recommendations
        """
        safe_query = self._normalize_query(query)
        query_lower = safe_query.lower()
        words = query_lower.split()
        
        # Identify query type
        query_type = "factual"  # Default
        
        if any(w in query_lower for w in ["why", "how", "explain"]):
            query_type = "explanatory"
        elif any(w in query_lower for w in ["find", "search", "where"]):
            query_type = "search"
        elif any(w in query_lower for w in ["list", "all", "show"]):
            query_type = "enumeration"
        elif any(w in query_lower for w in ["compare", "difference", "vs"]):
            query_type = "comparison"
        
        # Identify key terms
        stopwords = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                    "being", "have", "has", "had", "do", "does", "did", "will",
                    "would", "could", "should", "may", "might", "must", "shall",
                    "can", "to", "of", "in", "for", "on", "with", "at", "by",
                    "from", "as", "into", "through", "during", "before", "after",
                    "above", "below", "between", "under", "again", "further",
                    "then", "once", "here", "there", "when", "where", "why", "how"}
        
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        # Determine best retrieval strategy
        if query_type == "comparison":
            strategy = "multi_hop"
            hop_count = 2
        elif query_type == "enumeration":
            strategy = "broad"
            hop_count = 1
        elif len(key_terms) > 3:
            strategy = "focused"
            hop_count = 1
        else:
            strategy = "standard"
            hop_count = 1
        
        return {
            "query_type": query_type,
            "key_terms": key_terms,
            "strategy": strategy,
            "recommended_hops": hop_count,
            "word_count": len(words),
        }
    
    def route_query(self, query: str) -> str:
        """
        Determine which realm/source to query.
        
        Args:
            query: The query
            
        Returns:
            Realm name to route to
        """
        safe_query = self._normalize_query(query)
        if not safe_query:
            return "helheim"

        # Check cache
        cache_key = hashlib.sha256(safe_query.encode()).hexdigest()[:16]
        if cache_key in self._route_cache:
            return self._route_cache[cache_key]
        
        query_lower = safe_query.lower()
        
        # Route based on keywords
        routing_rules = [
            (["calculate", "compute", "math", "number"], "jotunheim"),
            (["remember", "history", "past", "previous"], "helheim"),
            (["verify", "check", "validate", "confirm"], "niflheim"),
            (["create", "generate", "build", "forge"], "svartalfheim"),
            (["plan", "strategy", "approach", "design"], "asgard"),
            (["transform", "convert", "refine", "improve"], "muspelheim"),
            (["route", "path", "choose", "select"], "alfheim"),
            (["resource", "allocate", "balance"], "vanaheim"),
        ]
        
        for keywords, realm in routing_rules:
            if any(kw in query_lower for kw in keywords):
                self._route_cache[cache_key] = realm
                if len(self._route_cache) > 500:
                    self._route_cache = dict(list(self._route_cache.items())[-250:])
                return realm
        
        # Default to helheim for general retrieval
        self._route_cache[cache_key] = "helheim"
        if len(self._route_cache) > 500:
            self._route_cache = dict(list(self._route_cache.items())[-250:])
        return "helheim"
    
    def fly(
        self,
        query: str,
        max_results: int = 5,
        compress: bool = True
    ) -> RetrievalResult:
        """
        Send Huginn flying to retrieve relevant information.
        
        Args:
            query: What to search for
            max_results: Maximum results to return
            compress: Whether to compress results for token efficiency
            
        Returns:
            RetrievalResult with findings
        """
        import time
        start_time = time.time()

        safe_query = self._normalize_query(query)
        bounded_results = max(1, min(int(max_results), self.max_results_cap))
        flight_error = None

        try:
            # Analyze query
            analysis = self.analyze_query(safe_query)

            # Route query
            source_realm = self.route_query(safe_query)

            # Retrieve from appropriate source
            results = []
            scores = []

            if self.helheim and source_realm == "helheim":
                # Search in Helheim's memory
                memories = self.helheim.search(
                    query=safe_query,
                    limit=bounded_results
                )

                for mem in memories:
                    results.append({
                        "content": getattr(mem, "content", ""),
                        "type": getattr(mem, "memory_type", "fact"),
                        "source": getattr(mem, "realm_source", "helheim"),
                        "importance": getattr(mem, "importance", 5),
                    })
                    scores.append(min(1.0, max(0.0, getattr(mem, "importance", 5) / 10.0)))

            elif self.muninn:
                # Use Muninn's retrieval
                retrieved = self.muninn.retrieve(safe_query, top_k=bounded_results)
                results = [
                    r.to_dict() if hasattr(r, "to_dict") else r
                    for r in (retrieved or [])
                    if isinstance(r, dict) or hasattr(r, "to_dict")
                ]
                scores = [0.5] * len(results)  # Default scores

            # Compress if requested
            if compress:
                results = self._compress_results(results, analysis.get("key_terms", []))
        except Exception as exc:
            logger.warning("Huginn flight failed for query '%s': %s", safe_query, exc)
            analysis = self.analyze_query("")
            source_realm = "helheim"
            results = []
            scores = []
            flight_error = str(exc)
        
        # Create result
        retrieval = RetrievalResult(
            query=query,
            results=results,
            relevance_scores=scores,
            source_realm=source_realm,
            retrieval_time=time.time() - start_time,
            compressed=compress,
            error=flight_error,
        )
        
        # Record flight
        self._flight_history.append(retrieval)
        
        # Trim history
        if len(self._flight_history) > 100:
            self._flight_history = self._flight_history[-50:]
        
        logger.debug(f"Huginn returned from {source_realm} with {len(results)} results")
        
        return retrieval
    
    def multi_hop_retrieve(
        self,
        initial_query: str,
        hop_count: int = 2,
        max_results_per_hop: int = 3
    ) -> List[RetrievalResult]:
        """
        Perform multi-hop retrieval, chaining queries.
        
        Args:
            initial_query: Starting query
            hop_count: Number of hops to perform
            max_results_per_hop: Results per hop
            
        Returns:
            List of RetrievalResults from each hop
        """
        all_results = []
        current_query = self._normalize_query(initial_query)
        bounded_hops = max(1, min(int(hop_count), 5))
        bounded_per_hop = max(1, min(int(max_results_per_hop), self.max_results_cap))

        for hop in range(bounded_hops):
            # Fly with current query
            result = self.fly(current_query, max_results=bounded_per_hop)
            all_results.append(result)
            
            # Generate next query from results
            if result.results:
                # Extract key concepts from results
                concepts = self._extract_concepts(result.results)
                if concepts:
                    current_query = f"{initial_query} {' '.join(concepts[:3])}"
                else:
                    break
            else:
                break
        
        return all_results
    
    def _compress_results(
        self,
        results: List[Dict],
        key_terms: List[str]
    ) -> List[Dict]:
        """Compress results to reduce token usage."""
        compressed = []
        
        for result in results:
            comp = {}
            
            for key, value in result.items():
                if isinstance(value, str):
                    # Truncate long strings
                    if len(value) > 200:
                        # Keep key term regions
                        value = value[:200] + "..."
                    comp[key] = value
                elif isinstance(value, (int, float, bool)):
                    comp[key] = value
                elif isinstance(value, list) and len(value) > 5:
                    comp[key] = value[:5]
                else:
                    comp[key] = value
            
            compressed.append(comp)
        
        return compressed
    
    def _extract_concepts(self, results: List[Dict]) -> List[str]:
        """Extract key concepts from results for follow-up queries."""
        concepts = set()
        
        for result in results:
            content = result.get("content", "")
            if isinstance(content, str):
                # Simple word extraction
                words = content.lower().split()
                for word in words:
                    if len(word) > 4 and word.isalpha():
                        concepts.add(word)
        
        return list(concepts)[:10]
    
    def semantic_search(
        self,
        query: str,
        documents: List[str],
        top_k: int = 3
    ) -> List[Tuple[int, float]]:
        """
        Perform semantic search using TF-IDF.
        
        Args:
            query: Query string
            documents: List of documents to search
            top_k: Number of results
            
        Returns:
            List of (index, score) tuples
        """
        if not self._tfidf or not documents:
            return []
        
        try:
            # Fit and transform
            tfidf_matrix = self._tfidf.fit_transform(documents + [query])
            
            # Get query vector (last row)
            query_vec = tfidf_matrix[-1]
            doc_vectors = tfidf_matrix[:-1]
            
            # Calculate similarities
            similarities = self._cosine(query_vec, doc_vectors).flatten()
            
            # Get top-k indices
            bounded_k = max(1, min(int(top_k), len(documents)))
            top_indices = similarities.argsort()[::-1][:bounded_k]
            
            return [(int(idx), float(similarities[idx])) for idx in top_indices]
        
        except Exception as e:
            logger.warning(f"Semantic search failed: {e}")
            return []
    
    # ── SRD condition-awareness ────────────────────────────────────────────

    # Known SRD condition names — used to detect condition queries
    _SRD_CONDITIONS = frozenset({
        "blinded", "charmed", "deafened", "exhaustion", "frightened",
        "grappled", "incapacitated", "invisible", "paralyzed", "petrified",
        "poisoned", "prone", "restrained", "stunned", "unconscious",
    })

    def analyze_query(self, query: str) -> Dict[str, Any]:  # type: ignore[override]
        """Analyze query; extends base routing to detect SRD condition queries."""
        safe_query = self._normalize_query(query)
        # Call super-style: re-run the analysis inline
        result = self._analyze_query_base(safe_query)
        # Detect condition query
        query_lower = safe_query.lower()
        matched_conditions = [c for c in self._SRD_CONDITIONS if c in query_lower]
        if matched_conditions:
            result["query_type"] = "condition_event"
            result["condition_tags"] = matched_conditions
            result["strategy"] = "focused"
        return result

    def _analyze_query_base(self, safe_query: str) -> Dict[str, Any]:
        """Original query analysis logic (extracted for reuse)."""
        query_lower = safe_query.lower()
        words = query_lower.split()
        query_type = "factual"
        if any(w in query_lower for w in ["why", "how", "explain"]):
            query_type = "explanatory"
        elif any(w in query_lower for w in ["find", "search", "where"]):
            query_type = "search"
        elif any(w in query_lower for w in ["list", "all", "show"]):
            query_type = "enumeration"
        elif any(w in query_lower for w in ["compare", "difference", "vs"]):
            query_type = "comparison"
        stopwords = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "could",
            "should", "may", "might", "must", "shall", "can", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into", "through",
            "during", "before", "after", "above", "below", "between", "under",
            "again", "further", "then", "once", "here", "there", "when", "where",
            "why", "how",
        }
        key_terms = [w for w in words if w not in stopwords and len(w) > 2]
        if query_type == "comparison":
            strategy, hop_count = "multi_hop", 2
        elif query_type == "enumeration":
            strategy, hop_count = "broad", 1
        elif len(key_terms) > 3:
            strategy, hop_count = "focused", 1
        else:
            strategy, hop_count = "standard", 1
        return {
            "query_type": query_type,
            "key_terms": key_terms,
            "strategy": strategy,
            "recommended_hops": hop_count,
            "word_count": len(words),
        }

    def get_srd_condition_context(self, conditions: List[str]) -> str:
        """Return a compact SRD mechanical summary for a list of conditions.

        Huginn uses this to attach authoritative condition mechanics to retrieved
        memory results — so the AI always knows what "paralyzed" actually does.
        """
        try:
            from systems.conditions_system import ConditionsSystem
            cs = ConditionsSystem()
            block = cs.apply_condition_modifiers(conditions)
            parts: List[str] = []
            if not block.can_take_actions:
                parts.append("no actions")
            if not block.can_move:
                parts.append("no movement")
            if block.attack_disadvantage:
                parts.append("attack disadvantage")
            if block.auto_crit_melee:
                parts.append("auto-crit melee")
            if block.save_auto_fail_str_dex:
                parts.append("auto-fail STR/DEX saves")
            if block.speed_zero:
                parts.append("speed 0")
            if not parts:
                return ""
            cond_str = ", ".join(str(c) for c in conditions)
            return f"[SRD: {cond_str} → {'; '.join(parts)}]"
        except Exception as exc:
            logger.debug("get_srd_condition_context failed: %s", exc)
            return ""

    def get_flight_stats(self) -> Dict[str, Any]:
        """Get statistics about Huginn's flights."""
        if not self._flight_history:
            return {"total_flights": 0}
        
        total_time = sum(f.retrieval_time for f in self._flight_history)
        total_results = sum(len(f.results) for f in self._flight_history)
        
        realm_counts = {}
        for flight in self._flight_history:
            realm = flight.source_realm
            realm_counts[realm] = realm_counts.get(realm, 0) + 1
        
        return {
            "total_flights": len(self._flight_history),
            "total_results_retrieved": total_results,
            "total_flight_time": total_time,
            "avg_flight_time": total_time / len(self._flight_history),
            "avg_results_per_flight": total_results / len(self._flight_history),
            "realm_visits": realm_counts,
        }
