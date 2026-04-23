#!/usr/bin/env python3
"""
RAG System for Norse Saga Engine
================================

Retrieval-Augmented Generation using chart data.
Indexes all chart files and provides relevant context for AI responses.

Features:
- BM25 ranking for relevance scoring
- Automatic chunking of large content
- Source attribution for retrieved content
- Caching for fast startup
- Integration with prompt builder
"""

import json
import yaml
import importlib
import importlib.util
import math
import re
import hashlib
import pickle
import logging
from threading import RLock
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """A searchable chunk of content from chart data."""
    id: str
    source_file: str
    source_type: str  # 'entry', 'section', 'item'
    title: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class SearchResult:
    """A search result with relevance score."""
    chunk: Chunk
    score: float
    matched_terms: List[str] = field(default_factory=list)


class BM25Index:
    """
    BM25 ranking algorithm for text retrieval.
    
    BM25 is a bag-of-words retrieval function that ranks documents
    based on query terms appearing in each document.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        """
        Initialize BM25 index.
        
        Args:
            k1: Term frequency saturation parameter (1.2-2.0 typical)
            b: Length normalization parameter (0.75 typical)
        """
        self.k1 = k1
        self.b = b
        
        # Index structures
        self.documents: List[Chunk] = []
        self.doc_lengths: List[int] = []
        self.avg_doc_length: float = 0.0
        self.doc_freqs: Dict[str, int] = defaultdict(int)  # term -> doc count
        self.term_freqs: List[Dict[str, int]] = []  # doc_id -> term -> count
        self.inverted_index: Dict[str, List[int]] = defaultdict(list)  # term -> doc_ids
        
        self._indexed = False
    
    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text into terms."""
        # Lowercase and split on non-alphanumeric
        text = text.lower()
        tokens = re.findall(r'\b[a-z0-9]+\b', text)
        # Remove very short tokens and stopwords
        stopwords = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                     'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
                     'would', 'could', 'should', 'may', 'might', 'must', 'shall',
                     'can', 'need', 'dare', 'ought', 'used', 'to', 'of', 'in',
                     'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into',
                     'through', 'during', 'before', 'after', 'above', 'below',
                     'between', 'under', 'again', 'further', 'then', 'once',
                     'here', 'there', 'when', 'where', 'why', 'how', 'all',
                     'each', 'few', 'more', 'most', 'other', 'some', 'such',
                     'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                     'too', 'very', 'just', 'and', 'but', 'if', 'or', 'because',
                     'until', 'while', 'this', 'that', 'these', 'those', 'it',
                     'its', 'they', 'them', 'their', 'what', 'which', 'who'}
        return [t for t in tokens if len(t) > 2 and t not in stopwords]
    
    def add_document(self, chunk: Chunk):
        """Add a document to the index."""
        doc_id = len(self.documents)
        self.documents.append(chunk)
        
        # Combine title and content for indexing
        text = f"{chunk.title} {chunk.content}"
        tokens = self._tokenize(text)
        
        self.doc_lengths.append(len(tokens))
        
        # Count term frequencies for this document
        term_freq = defaultdict(int)
        seen_terms = set()
        
        for token in tokens:
            term_freq[token] += 1
            if token not in seen_terms:
                self.doc_freqs[token] += 1
                seen_terms.add(token)
            self.inverted_index[token].append(doc_id)
        
        self.term_freqs.append(dict(term_freq))
        self._indexed = False
    
    def build_index(self):
        """Finalize the index after adding all documents."""
        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)
        self._indexed = True
        logger.info(f"BM25 index built: {len(self.documents)} documents, {len(self.doc_freqs)} unique terms")
    
    def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """
        Search for documents matching the query.
        
        Args:
            query: Search query string
            top_k: Number of results to return
            
        Returns:
            List of SearchResult objects sorted by relevance
        """
        if not self._indexed:
            self.build_index()
        
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        n_docs = len(self.documents)
        scores = defaultdict(float)
        matched_terms = defaultdict(list)
        
        for term in query_tokens:
            if term not in self.inverted_index:
                continue
            
            # IDF calculation
            df = self.doc_freqs[term]
            idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
            
            # Score each document containing this term
            for doc_id in set(self.inverted_index[term]):
                tf = self.term_freqs[doc_id].get(term, 0)
                doc_len = self.doc_lengths[doc_id]
                
                # BM25 formula
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (1 - self.b + self.b * doc_len / self.avg_doc_length)
                score = idf * (numerator / denominator)
                
                scores[doc_id] += score
                if term not in matched_terms[doc_id]:
                    matched_terms[doc_id].append(term)
        
        # Sort by score and return top_k
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        
        results = []
        for doc_id, score in sorted_docs:
            results.append(SearchResult(
                chunk=self.documents[doc_id],
                score=score,
                matched_terms=matched_terms[doc_id]
            ))
        
        return results


class ChartRAGSystem:
    """
    RAG system for Norse Saga Engine chart data.
    
    Indexes all chart files and provides context retrieval for AI prompts.
    """
    
    CACHE_VERSION = "1.0"
    # Cache the computed cache-key for up to _CACHE_KEY_TTL seconds so that
    # the O(n) stat() loop over all chart files does not fire on every search.
    _cache_key_value: str = ""
    _cache_key_ts: float = 0.0
    _CACHE_KEY_TTL: float = 60.0  # seconds

    def __init__(self, charts_path: str = "data/charts", cache_path: str = "data/rag_cache"):
        """
        Initialize the RAG system.
        
        Args:
            charts_path: Path to chart files directory
            cache_path: Path for caching index
        """
        self.charts_path = Path(charts_path)
        self.cache_path = Path(cache_path)
        self.cache_path.mkdir(parents=True, exist_ok=True)
        
        self.index = BM25Index()
        self.chunks: Dict[str, Chunk] = {}  # id -> chunk
        self.source_files: List[str] = []
        
        self._loaded = False
        self._lock = RLock()
    
    def _get_cache_key(self) -> str:
        """Generate cache key based on chart files, with a 60-second TTL to avoid per-search stat() calls."""
        import time as _time
        now = _time.monotonic()
        if ChartRAGSystem._cache_key_value and (now - ChartRAGSystem._cache_key_ts) < ChartRAGSystem._CACHE_KEY_TTL:
            return ChartRAGSystem._cache_key_value
        files_info = []
        for f in sorted(self.charts_path.iterdir()):
            if f.suffix.lower() in ['.json', '.jsonl', '.yaml', '.yml', '.csv', '.cvs', '.txt', '.md', '.html', '.htm', '.xml', '.pdf']:
                try:
                    stat = f.stat()
                    files_info.append(f"{f.name}:{stat.st_size}:{stat.st_mtime}")
                except OSError:
                    # File may have been deleted or locked mid-scan — skip gracefully
                    files_info.append(f"{f.name}:unavailable:0")
        content = "|".join(files_info)
        ChartRAGSystem._cache_key_value = hashlib.md5(content.encode()).hexdigest()
        ChartRAGSystem._cache_key_ts = now
        return ChartRAGSystem._cache_key_value
    
    def _load_cache(self) -> bool:
        """Try to load index from cache."""
        cache_file = self.cache_path / "rag_index.pkl"
        cache_meta = self.cache_path / "rag_meta.json"
        
        if not cache_file.exists() or not cache_meta.exists():
            return False
        
        try:
            with open(cache_meta, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            if meta.get('version') != self.CACHE_VERSION:
                return False
            if meta.get('cache_key') != self._get_cache_key():
                return False
            
            with open(cache_file, 'rb') as f:
                data = pickle.load(f)
            
            self.index = data['index']
            self.chunks = data['chunks']
            self.source_files = data['source_files']
            self._loaded = True
            
            logger.info(f"RAG index loaded from cache: {len(self.chunks)} chunks")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to load RAG cache: {e}")
            return False
    
    def _save_cache(self):
        """Save index to cache."""
        try:
            cache_file = self.cache_path / "rag_index.pkl"
            cache_meta = self.cache_path / "rag_meta.json"
            
            data = {
                'index': self.index,
                'chunks': self.chunks,
                'source_files': self.source_files
            }
            
            with open(cache_file, 'wb') as f:
                pickle.dump(data, f)
            
            meta = {
                'version': self.CACHE_VERSION,
                'cache_key': self._get_cache_key(),
                'chunk_count': len(self.chunks),
                'source_count': len(self.source_files)
            }
            
            with open(cache_meta, 'w', encoding='utf-8') as f:
                json.dump(meta, f, indent=2)
            
            logger.info("RAG index saved to cache")
            
        except Exception as e:
            logger.warning(f"Failed to save RAG cache: {e}")
    
    def _chunk_text(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Split text into chunks of reasonable size."""
        if len(text) <= max_chunk_size:
            return [text]
        
        # Split on sentence boundaries
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chunk_size:
                current_chunk += " " + sentence if current_chunk else sentence
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text[:max_chunk_size]]
    
    def _extract_chunks_from_list(self, data: List, source_file: str) -> List[Chunk]:
        """Extract chunks from a list-based chart file (including JSONL training data)."""
        chunks = []
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                continue
            
            # Try various common field names for title
            title = (item.get('theme') or item.get('name') or item.get('title') or 
                    item.get('term') or item.get('id') or item.get('topic') or
                    item.get('category') or f"Entry {i+1}")
            
            # Build content from various fields
            content_parts = []
            
            # Value/description fields (standard chart format)
            for field in ['value', 'description', 'content', 'text', 'definition',
                         'meaning', 'interpretation', 'details', 'summary']:
                if field in item and item[field]:
                    content_parts.append(str(item[field]))
            
            # JSONL training data formats
            # Format 1: instruction/output (Alpaca style)
            if 'instruction' in item:
                content_parts.append(f"Q: {item['instruction']}")
                if 'input' in item and item['input']:
                    content_parts.append(f"Context: {item['input']}")
                if 'output' in item:
                    content_parts.append(f"A: {item['output']}")
            
            # Format 2: prompt/response
            if 'prompt' in item:
                content_parts.append(f"Q: {item['prompt']}")
            if 'response' in item:
                content_parts.append(f"A: {item['response']}")
            
            # Format 3: question/answer
            if 'question' in item:
                content_parts.append(f"Q: {item['question']}")
            if 'answer' in item:
                content_parts.append(f"A: {item['answer']}")
            
            # Format 4: human/assistant (ShareGPT style - direct)
            if 'human' in item:
                content_parts.append(f"Q: {item['human']}")
            if 'assistant' in item:
                content_parts.append(f"A: {item['assistant']}")
            
            # Handle nested conversations array (ShareGPT style)
            if 'conversations' in item and isinstance(item['conversations'], list):
                for conv in item['conversations']:
                    if isinstance(conv, dict):
                        # Try various role field names
                        role = conv.get('from') or conv.get('role') or conv.get('speaker') or ''
                        value = conv.get('value') or conv.get('content') or conv.get('text') or ''
                        
                        if role.lower() in ['human', 'user', 'question']:
                            content_parts.append(f"Q: {value}")
                        elif role.lower() in ['assistant', 'gpt', 'bot', 'answer']:
                            content_parts.append(f"A: {value}")
                        elif value:
                            content_parts.append(value)
            
            # Handle do/don't lists
            for field in ['do', 'dont', 'examples', 'methods', 'practices']:
                if field in item and isinstance(item[field], list):
                    content_parts.append(f"{field.title()}: " + "; ".join(str(x) for x in item[field][:5]))
            
            if not content_parts:
                # Use all string values as fallback
                for k, v in item.items():
                    if isinstance(v, str) and k not in ['id', 'name', 'title', 'theme']:
                        content_parts.append(f"{k}: {v}")
            
            content = " ".join(content_parts)
            if not content:
                continue
            
            # Chunk if too large
            text_chunks = self._chunk_text(content)
            
            for j, chunk_text in enumerate(text_chunks):
                chunk_id = f"{source_file}:{i}:{j}"
                chunk = Chunk(
                    id=chunk_id,
                    source_file=source_file,
                    source_type='entry',
                    title=str(title),
                    content=chunk_text,
                    metadata={'index': i, 'chunk': j}
                )
                chunks.append(chunk)
        
        return chunks
    
    def _extract_chunks_from_dict(self, data: Dict, source_file: str, prefix: str = "") -> List[Chunk]:
        """Extract chunks from a dict-based chart file."""
        chunks = []
        
        def process_dict(d: Dict, path: str = ""):
            for key, value in d.items():
                # Ensure key is a string
                key_str = str(key)
                current_path = f"{path}.{key_str}" if path else key_str
                
                if isinstance(value, str) and len(value) > 20:
                    # This is content
                    chunk_id = f"{source_file}:{current_path}"
                    text_chunks = self._chunk_text(value)
                    
                    for j, chunk_text in enumerate(text_chunks):
                        chunk = Chunk(
                            id=f"{chunk_id}:{j}",
                            source_file=source_file,
                            source_type='section',
                            title=key_str.replace('_', ' ').title(),
                            content=chunk_text,
                            metadata={'path': current_path, 'chunk': j}
                        )
                        chunks.append(chunk)
                
                elif isinstance(value, list):
                    # Process list items
                    for i, item in enumerate(value):
                        if isinstance(item, dict):
                            # Named item with fields
                            item_name = item.get('name') or item.get('title') or item.get('id') or f"{key_str}_{i}"
                            
                            content_parts = []
                            for field in ['description', 'purpose', 'meaning', 'value', 'text']:
                                if field in item:
                                    content_parts.append(str(item[field]))
                            
                            # Handle nested lists like 'methods'
                            for nested_key in ['methods', 'practices', 'examples']:
                                if nested_key in item and isinstance(item[nested_key], list):
                                    for nested_item in item[nested_key]:
                                        if isinstance(nested_item, dict):
                                            if 'name' in nested_item:
                                                content_parts.append(f"{nested_item['name']}")
                                            if 'description' in nested_item:
                                                content_parts.append(nested_item['description'])
                                        elif isinstance(nested_item, str):
                                            content_parts.append(nested_item)
                            
                            if content_parts:
                                content = " ".join(content_parts)
                                text_chunks = self._chunk_text(content)
                                
                                for j, chunk_text in enumerate(text_chunks):
                                    chunk = Chunk(
                                        id=f"{source_file}:{current_path}.{i}:{j}",
                                        source_file=source_file,
                                        source_type='item',
                                        title=str(item_name),
                                        content=chunk_text,
                                        metadata={'path': current_path, 'index': i, 'chunk': j}
                                    )
                                    chunks.append(chunk)
                        
                        elif isinstance(item, str) and len(item) > 20:
                            chunk = Chunk(
                                id=f"{source_file}:{current_path}.{i}",
                                source_file=source_file,
                                source_type='item',
                                title=f"{key_str} {i+1}",
                                content=item,
                                metadata={'path': current_path, 'index': i}
                            )
                            chunks.append(chunk)
                
                elif isinstance(value, dict):
                    # Recurse into nested dicts
                    process_dict(value, current_path)
        
        process_dict(data, prefix)
        return chunks
    
    def _load_file(self, filepath: Path) -> Optional[Any]:
        """Load a supported chart file format into a structured payload."""
        try:
            suffix = filepath.suffix.lower()
            if suffix == '.pdf':
                return {'content': self._extract_pdf_text(filepath)}

            with open(filepath, 'r', encoding='utf-8') as f:
                if suffix == '.json':
                    return json.load(f)
                elif suffix == '.jsonl':
                    # JSONL: one JSON object per line
                    entries = []
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            entries.append(entry)
                        except json.JSONDecodeError as e:
                            logger.debug(f"Skipping invalid JSON at {filepath}:{line_num}: {e}")
                    return entries
                elif suffix in {'.csv', '.cvs'}:
                    # CSV: convert to list of dicts using header row
                    import csv
                    reader = csv.DictReader(f)
                    entries = []
                    for row in reader:
                        # Clean up the row - remove empty values
                        clean_row = {k: v for k, v in row.items() if v and k}
                        if clean_row:
                            entries.append(clean_row)
                    return entries
                elif suffix in {'.txt', '.md', '.html', '.htm', '.xml'}:
                    text = f.read()
                    if suffix in {'.html', '.htm', '.xml'}:
                        text = re.sub(r"<[^>]+>", " ", text)
                    return {'content': text}
                else:
                    return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Error loading {filepath}: {e}")
            return None
    
    def _extract_pdf_text(self, filepath: Path) -> str:
        module_name = 'pypdf' if importlib.util.find_spec('pypdf') else 'PyPDF2'
        if not importlib.util.find_spec(module_name):
            logger.warning('No PDF reader installed; skipping RAG PDF source: %s', filepath)
            return ''
        pdf_module = importlib.import_module(module_name)
        reader = pdf_module.PdfReader(str(filepath))
        return "\n".join((page.extract_text() or '') for page in reader.pages)

    def build_index(self, force_rebuild: bool = False):
        """
        Build the RAG index from all chart files.

        Args:
            force_rebuild: Force rebuild even if cache exists
        """
        with self._lock:
            if not force_rebuild and self._load_cache():
                return

            logger.info("Building RAG index from chart files...")

            self.index = BM25Index()
            self.chunks = {}
            self.source_files = []

            if not self.charts_path.exists():
                logger.warning(f"Charts path not found: {self.charts_path}")
                return

            for filepath in sorted(self.charts_path.iterdir()):
                if filepath.suffix.lower() not in ['.json', '.jsonl', '.yaml', '.yml', '.csv', '.cvs', '.txt', '.md', '.html', '.htm', '.xml', '.pdf']:
                    continue
                if filepath.name.startswith('_'):
                    continue  # Skip example files

                data = self._load_file(filepath)
                if data is None:
                    continue

                source_name = filepath.stem
                self.source_files.append(source_name)

                # Extract chunks based on data type
                if isinstance(data, list):
                    file_chunks = self._extract_chunks_from_list(data, source_name)
                elif isinstance(data, dict):
                    file_chunks = self._extract_chunks_from_dict(data, source_name)
                else:
                    continue

                # Add to index
                for chunk in file_chunks:
                    self.chunks[chunk.id] = chunk
                    self.index.add_document(chunk)

                logger.debug(f"Indexed {source_name}: {len(file_chunks)} chunks")

            self.index.build_index()
            self._loaded = True

            logger.info(
                f"RAG index built: {len(self.chunks)} chunks from {len(self.source_files)} files"
            )

            # Save to cache
            self._save_cache()

    def _self_heal_if_needed(self):
        """Rebuild index if not loaded or structurally empty."""
        if self._loaded and self.chunks and self.index.documents:
            return

        logger.warning("RAG index unhealthy. Rebuilding for self-healing.")
        self.build_index(force_rebuild=False)
    
    def search(self, query: str, top_k: int = 10, min_score: float = 0.5) -> List[SearchResult]:
        """
        Search for relevant content.
        
        Args:
            query: Search query
            top_k: Maximum results to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of SearchResult objects
        """
        self._self_heal_if_needed()

        try:
            results = self.index.search(query, top_k=top_k * 2)
            filtered = [r for r in results if r.score >= min_score]
            return filtered[:top_k]
        except Exception as exc:
            logger.warning(f"Search failed, attempting self-heal rebuild: {exc}")
            self.build_index(force_rebuild=True)
            retry_results = self.index.search(query, top_k=top_k * 2)
            return [r for r in retry_results if r.score >= min_score][:top_k]

    def search_multi_query(
        self,
        queries: List[str],
        top_k: int = 16,
        min_score: float = 0.25,
        max_workers: int = 6,
    ) -> List[SearchResult]:
        """Run retrieval in parallel across many query signals and merge scores."""
        normalized_queries = [q.strip() for q in queries if q and q.strip()]
        if not normalized_queries:
            return []

        self._self_heal_if_needed()
        max_workers = max(1, min(max_workers, len(normalized_queries)))
        merged_scores: Dict[str, float] = defaultdict(float)
        merged_terms: Dict[str, set] = defaultdict(set)
        chunk_lookup: Dict[str, Chunk] = {}

        # Muninn gathers many memory-paths in parallel.
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.search, query, top_k, min_score): query
                for query in normalized_queries
            }
            for future in as_completed(futures):
                for result in future.result():
                    cid = result.chunk.id
                    chunk_lookup[cid] = result.chunk
                    merged_scores[cid] += result.score
                    merged_terms[cid].update(result.matched_terms)

        sorted_chunks = sorted(merged_scores.items(), key=lambda item: item[1], reverse=True)
        deduped_results: List[SearchResult] = []
        for chunk_id, score in sorted_chunks[:top_k]:
            deduped_results.append(
                SearchResult(
                    chunk=chunk_lookup[chunk_id],
                    score=score,
                    matched_terms=sorted(merged_terms[chunk_id]),
                )
            )
        return deduped_results
    
    def get_context_for_query(self, query: str, max_tokens: int = 1500) -> str:
        """
        Get formatted context string for a query.
        
        Args:
            query: The query to find context for
            max_tokens: Approximate maximum tokens for context
            
        Returns:
            Formatted context string for inclusion in prompts
        """
        results = self.search(query, top_k=16, min_score=0.3)
        
        if not results:
            return ""
        
        # Build context string
        context_parts = []
        total_length = 0
        max_chars = max_tokens * 4  # Rough token-to-char ratio
        
        for result in results:
            chunk = result.chunk
            
            # Format this result
            part = f"[{chunk.source_file}] {chunk.title}:\n{chunk.content}\n"
            
            if total_length + len(part) > max_chars:
                break
            
            context_parts.append(part)
            total_length += len(part)
        
        if not context_parts:
            return ""
        
        header = "=== RELEVANT NORSE LORE (from chart data) ===\n"
        footer = "\n=== END LORE ===\n"
        
        return header + "\n".join(context_parts) + footer
    
    def get_context_for_topics(self, topics: List[str], max_tokens: int = 1500) -> str:
        """
        Get context for multiple topics.
        
        Args:
            topics: List of topic strings to search for
            max_tokens: Approximate maximum tokens
            
        Returns:
            Formatted context string
        """
        # Combine topics into single search
        combined_query = " ".join(topics)
        return self.get_context_for_query(combined_query, max_tokens)

    def get_context_for_topic_mesh(
        self, topics: List[str], max_tokens: int = 1500, per_query_top_k: int = 10
    ) -> str:
        """Build a broader context by searching each topic and merged combinations."""
        topics = [topic.strip() for topic in topics if topic and topic.strip()]
        if not topics:
            return ""

        combined_queries = topics[:]
        if len(topics) > 1:
            combined_queries.append(" ".join(topics))
            combined_queries.extend(
                [f"{topics[0]} {topic}" for topic in topics[1:4]]
            )

        results = self.search_multi_query(
            queries=combined_queries,
            top_k=max(8, per_query_top_k * 2),
            min_score=0.2,
        )

        if not results:
            return ""

        context_parts: List[str] = []
        total_length = 0
        max_chars = max_tokens * 4
        used_sources: set = set()

        for result in results:
            chunk = result.chunk
            source_prefix = f"[{chunk.source_file}]"
            part = f"{source_prefix} {chunk.title}:\n{chunk.content}\n"
            if total_length + len(part) > max_chars:
                continue
            if chunk.source_file in used_sources and len(context_parts) > 8:
                continue

            context_parts.append(part)
            total_length += len(part)
            used_sources.add(chunk.source_file)

            if total_length >= max_chars:
                break

        if not context_parts:
            return ""

        header = "=== RELEVANT NORSE LORE (multi-threaded topic mesh) ===\n"
        footer = "\n=== END LORE ===\n"
        return header + "\n".join(context_parts) + footer
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the RAG index."""
        if not self._loaded:
            return {'loaded': False}
        
        return {
            'loaded': True,
            'total_chunks': len(self.chunks),
            'source_files': len(self.source_files),
            'sources': self.source_files,
            'unique_terms': len(self.index.doc_freqs),
            'avg_chunk_length': self.index.avg_doc_length
        }


# Singleton instance for easy access
_rag_instance: Optional[ChartRAGSystem] = None


def get_rag_system(charts_path: str = "data/charts") -> ChartRAGSystem:
    """Get or create the RAG system instance."""
    global _rag_instance
    if _rag_instance is None:
        _rag_instance = ChartRAGSystem(charts_path)
    return _rag_instance


def search_charts(query: str, top_k: int = 10) -> List[SearchResult]:
    """Convenience function to search charts."""
    rag = get_rag_system()
    if not rag._loaded:
        rag.build_index()
    return rag.search(query, top_k)


def get_chart_context(
    query: str,
    max_tokens: int = 1500,
    max_chars: Optional[int] = None,
) -> str:
    """Convenience function to get context for a query.

    max_chars is accepted for legacy callers and converted to an
    approximate token budget when provided.
    """
    rag = get_rag_system()
    if not rag._loaded:
        rag.build_index()
    safe_tokens = int(max_tokens)
    if max_chars is not None:
        try:
            safe_tokens = max(1, int(max_chars) // 4)
        except Exception:
            safe_tokens = int(max_tokens)
    return rag.get_context_for_query(query, safe_tokens)
