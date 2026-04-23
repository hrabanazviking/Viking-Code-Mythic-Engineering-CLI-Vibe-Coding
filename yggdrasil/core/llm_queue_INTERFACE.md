# llm_queue.py — INTERFACE.md

## Class: `QueuePriority`

Priority levels for queued requests.

## Class: `LLMRequest`

A single LLM inference request.

### `wait_time()`
Get time spent waiting in queue.

### `execution_time()`
Get execution time if completed.

## Class: `LLMQueue`

Queue for sequential LLM processing.

Ensures the local model processes one query at a time,
like ravens returning to Odin one by one.

Features:
- Priority-based queuing
- Thread-safe operation
- Timeout handling
- Request tracking and metrics
- Callback support

### `enqueue(prompt, priority, realm, callback, timeout)`
Add a request to the queue.

Args:
    prompt: The prompt to send to LLM
    priority: Priority level
    realm: Which world is requesting
    callback: Optional callback with (response, error)
    timeout: Request timeout
    
Returns:
    LLMRequest object for tracking

### `process_next()`
Process the next request in queue (synchronous).

Returns:
    Completed LLMRequest or None if queue empty

### `process_all()`
Process all pending requests (synchronous).

Returns:
    List of completed LLMRequest objects

### `process_sync(prompt, realm)`
Synchronous single-shot processing.

Args:
    prompt: The prompt to process
    realm: Requesting realm
    
Returns:
    (response, error) tuple

### `start_worker()`
Start background worker thread for async processing.

### `stop_worker()`
Stop background worker thread.

### `get_queue_size()`
Get current queue size.

### `is_processing()`
Check if currently processing a request.

### `is_empty()`
Check if queue is empty.

### `get_metrics()`
Get queue metrics.

### `get_recent_completions(limit)`
Get recent completed requests.

### `get_recent_failures(limit)`
Get recent failed requests.

### `clear_history()`
Clear completed and failed request history.

## Class: `MockLLM`

Mock LLM for testing.

---
**Contract Version**: 1.0 | v8.0.0
