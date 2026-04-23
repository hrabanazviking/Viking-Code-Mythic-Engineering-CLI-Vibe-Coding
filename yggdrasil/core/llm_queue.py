"""
LLM Queue - Sequential LLM Processing
=====================================

Ensures the local LLM model processes one query at a time,
maintaining stability and preventing cognitive overload.

Like Odin's ravens returning one at a time to whisper wisdom,
the queue ensures orderly communication with the oracle.
"""

import logging
import queue
import threading
import time
import hashlib
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class QueuePriority(Enum):
    """Priority levels for queued requests."""
    CRITICAL = 0   # Emergency, bypass normal queue
    HIGH = 1       # Important, execute soon
    NORMAL = 2     # Standard priority
    LOW = 3        # Background tasks
    IDLE = 4       # Execute only when nothing else pending


@dataclass
class LLMRequest:
    """A single LLM inference request."""
    id: str
    prompt: str
    priority: QueuePriority = QueuePriority.NORMAL
    realm: str = "midgard"      # Which world is requesting
    callback: Optional[Callable] = None
    timeout: float = 60.0
    
    # Tracking
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Result
    response: Optional[str] = None
    error: Optional[str] = None
    
    def wait_time(self) -> float:
        """Get time spent waiting in queue."""
        if self.started_at:
            return (self.started_at - self.queued_at).total_seconds()
        return (datetime.now() - self.queued_at).total_seconds()
    
    def execution_time(self) -> Optional[float]:
        """Get execution time if completed."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class LLMQueue:
    """
    Queue for sequential LLM processing.
    
    Ensures the local model processes one query at a time,
    like ravens returning to Odin one by one.
    
    Features:
    - Priority-based queuing
    - Thread-safe operation
    - Timeout handling
    - Request tracking and metrics
    - Callback support
    """
    
    def __init__(
        self,
        llm_callable: Callable[[str], str],
        max_queue_size: int = 100,
        default_timeout: float = 60.0
    ):
        """
        Initialize the LLM Queue.
        
        Args:
            llm_callable: Function that takes prompt and returns response
            max_queue_size: Maximum pending requests
            default_timeout: Default timeout for requests
        """
        self.llm = llm_callable
        self.max_queue_size = max_queue_size
        self.default_timeout = default_timeout
        
        # Priority queue (lower number = higher priority)
        self._queue = queue.PriorityQueue(maxsize=max_queue_size)
        self._lock = threading.Lock()
        self._processing = False
        
        # Tracking
        self._request_counter = 0
        self._completed_requests: List[LLMRequest] = []
        self._failed_requests: List[LLMRequest] = []
        self._response_cache: Dict[str, Tuple[str, float]] = {}
        self.cache_ttl_seconds = 30.0
        self.max_cache_entries = 200
        
        # Metrics
        self.total_requests = 0
        self.total_completions = 0
        self.total_failures = 0
        self.total_wait_time = 0.0
        self.total_exec_time = 0.0
        self.cache_hits = 0
        
        # Worker thread (optional async mode)
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_worker = threading.Event()
    
    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        with self._lock:
            self._request_counter += 1
            return f"llm_req_{self._request_counter}_{int(time.time())}"

    def _prompt_fingerprint(self, prompt: str, realm: str) -> str:
        """Huginn maps matching requests so ravens do not repeat flights."""
        normalized = " ".join(prompt.lower().split())
        return hashlib.sha256(f"{realm}|{normalized}".encode("utf-8")).hexdigest()

    def _prune_cache(self) -> None:
        """Keep cache compact and fresh for fast cross-system recalls."""
        now = time.time()
        expired = [key for key, (_, expiry) in self._response_cache.items() if expiry <= now]
        for key in expired:
            self._response_cache.pop(key, None)

        if len(self._response_cache) <= self.max_cache_entries:
            return

        ordered_by_expiry = sorted(self._response_cache.items(), key=lambda item: item[1][1])
        for key, _ in ordered_by_expiry[: len(self._response_cache) - self.max_cache_entries]:
            self._response_cache.pop(key, None)
    
    def enqueue(
        self,
        prompt: str,
        priority: QueuePriority = QueuePriority.NORMAL,
        realm: str = "midgard",
        callback: Optional[Callable] = None,
        timeout: Optional[float] = None
    ) -> LLMRequest:
        """
        Add a request to the queue.
        
        Args:
            prompt: The prompt to send to LLM
            priority: Priority level
            realm: Which world is requesting
            callback: Optional callback with (response, error)
            timeout: Request timeout
            
        Returns:
            LLMRequest object for tracking
        """
        prompt_key = self._prompt_fingerprint(prompt, realm)
        self._prune_cache()
        cached = self._response_cache.get(prompt_key)
        if cached:
            response, _ = cached
            request = LLMRequest(
                id=self._generate_request_id(),
                prompt=prompt,
                priority=priority,
                realm=realm,
                callback=callback,
                timeout=timeout or self.default_timeout,
                started_at=datetime.now(),
                completed_at=datetime.now(),
                response=response,
            )
            self.total_requests += 1
            self.total_completions += 1
            self.cache_hits += 1
            self._completed_requests.append(request)
            return request

        request = LLMRequest(
            id=self._generate_request_id(),
            prompt=prompt,
            priority=priority,
            realm=realm,
            callback=callback,
            timeout=timeout or self.default_timeout
        )
        setattr(request, "prompt_key", prompt_key)
        
        # Priority queue uses (priority_value, timestamp, request)
        # Lower priority value = processed first
        queue_item = (priority.value, request.queued_at.timestamp(), request)
        
        try:
            self._queue.put_nowait(queue_item)
            self.total_requests += 1
            logger.debug(f"Enqueued {request.id} from {realm} with priority {priority.name}")
            return request
        except queue.Full:
            request.error = "Queue full"
            self._failed_requests.append(request)
            self.total_failures += 1
            logger.error(f"Queue full, rejected {request.id}")
            return request
    
    def process_next(self) -> Optional[LLMRequest]:
        """
        Process the next request in queue (synchronous).
        
        Returns:
            Completed LLMRequest or None if queue empty
        """
        try:
            _, _, request = self._queue.get_nowait()
        except queue.Empty:
            return None
        
        return self._process_request(request)
    
    def process_all(self) -> List[LLMRequest]:
        """
        Process all pending requests (synchronous).
        
        Returns:
            List of completed LLMRequest objects
        """
        results = []
        while not self._queue.empty():
            result = self.process_next()
            if result:
                results.append(result)
        return results
    
    def _process_request(self, request: LLMRequest) -> LLMRequest:
        """Process a single request."""
        with self._lock:
            self._processing = True
        
        request.started_at = datetime.now()
        
        try:
            logger.debug(f"Processing {request.id} from {request.realm}")
            
            # Call the LLM
            response = self.llm(request.prompt)
            
            request.response = response
            request.completed_at = datetime.now()
            prompt_key = getattr(request, "prompt_key", self._prompt_fingerprint(request.prompt, request.realm))
            self._response_cache[prompt_key] = (response, time.time() + self.cache_ttl_seconds)
            
            # Update metrics
            self.total_completions += 1
            self.total_wait_time += request.wait_time()
            exec_time = request.execution_time()
            if exec_time:
                self.total_exec_time += exec_time
            
            self._completed_requests.append(request)
            
            # Callback if provided
            if request.callback:
                try:
                    request.callback(response, None)
                except Exception as e:
                    logger.warning(f"Callback error for {request.id}: {e}")
            
            logger.debug(f"Completed {request.id} in {exec_time:.2f}s")
            
        except Exception as e:
            request.error = str(e)
            request.completed_at = datetime.now()
            self.total_failures += 1
            self._failed_requests.append(request)
            
            if request.callback:
                try:
                    request.callback(None, str(e))
                except Exception as cb_e:
                    logger.warning(f"Callback error for {request.id}: {cb_e}")
            
            logger.error(f"Failed {request.id}: {e}")
        
        finally:
            with self._lock:
                self._processing = False
        
        return request
    
    def process_sync(self, prompt: str, realm: str = "midgard") -> Tuple[Optional[str], Optional[str]]:
        """
        Synchronous single-shot processing.
        
        Args:
            prompt: The prompt to process
            realm: Requesting realm
            
        Returns:
            (response, error) tuple
        """
        request = self.enqueue(prompt, realm=realm)
        
        if request.error:
            return None, request.error

        if request.response is not None and request.completed_at is not None:
            return request.response, None
        
        # Process immediately
        result = self.process_next()
        
        if result:
            return result.response, result.error
        return None, "Processing failed"
    
    # ========================================================================
    # ASYNC WORKER MODE
    # ========================================================================
    
    def start_worker(self):
        """Start background worker thread for async processing."""
        if self._worker_thread and self._worker_thread.is_alive():
            return
        
        self._stop_worker.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("LLM Queue worker started")
    
    def stop_worker(self):
        """Stop background worker thread."""
        self._stop_worker.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5.0)
            logger.info("LLM Queue worker stopped")
    
    def _worker_loop(self):
        """Background worker loop."""
        while not self._stop_worker.is_set():
            try:
                # Wait for item with timeout
                _, _, request = self._queue.get(timeout=0.5)
                self._process_request(request)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker error: {e}")
    
    # ========================================================================
    # METRICS AND STATUS
    # ========================================================================
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self._queue.qsize()
    
    def is_processing(self) -> bool:
        """Check if currently processing a request."""
        return self._processing
    
    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return self._queue.empty()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get queue metrics."""
        avg_wait = self.total_wait_time / max(1, self.total_completions)
        avg_exec = self.total_exec_time / max(1, self.total_completions)
        
        return {
            "total_requests": self.total_requests,
            "total_completions": self.total_completions,
            "total_failures": self.total_failures,
            "queue_size": self.get_queue_size(),
            "is_processing": self.is_processing(),
            "cache_hits": self.cache_hits,
            "avg_wait_time": round(avg_wait, 3),
            "avg_exec_time": round(avg_exec, 3),
            "success_rate": round(self.total_completions / max(1, self.total_requests) * 100, 1),
        }
    
    def get_recent_completions(self, limit: int = 10) -> List[Dict]:
        """Get recent completed requests."""
        return [
            {
                "id": r.id,
                "realm": r.realm,
                "wait_time": r.wait_time(),
                "exec_time": r.execution_time(),
                "prompt_preview": r.prompt[:50] + "..." if len(r.prompt) > 50 else r.prompt,
            }
            for r in self._completed_requests[-limit:]
        ]
    
    def get_recent_failures(self, limit: int = 10) -> List[Dict]:
        """Get recent failed requests."""
        return [
            {
                "id": r.id,
                "realm": r.realm,
                "error": r.error,
                "prompt_preview": r.prompt[:50] + "..." if len(r.prompt) > 50 else r.prompt,
            }
            for r in self._failed_requests[-limit:]
        ]
    
    def clear_history(self):
        """Clear completed and failed request history."""
        self._completed_requests.clear()
        self._failed_requests.clear()


class MockLLM:
    """Mock LLM for testing."""
    
    def __init__(self, delay: float = 0.1, responses: Dict[str, str] = None):
        self.delay = delay
        self.responses = responses or {}
        self.call_count = 0
    
    def __call__(self, prompt: str) -> str:
        self.call_count += 1
        time.sleep(self.delay)
        
        # Check for specific responses
        for key, response in self.responses.items():
            if key.lower() in prompt.lower():
                return response
        
        return f"Mock response #{self.call_count} for: {prompt[:50]}..."
