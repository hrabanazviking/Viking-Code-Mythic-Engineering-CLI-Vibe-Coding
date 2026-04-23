"""
Norse Saga Engine - Bidirectional Message Queue System

Implements thread-safe message queues for all 12 communication pathways
"""

import threading
from collections import deque
from typing import Any, Dict

class MessageQueue:
    """Thread-safe bidirectional message queue"""
    def __init__(self):
        self.queue = deque()
        self.lock = threading.Lock()
        self.condition = threading.Condition(self.lock)
    
    def enqueue(self, message: Dict[str, Any]):
        """Add message to queue"""
        with self.lock:
            self.queue.append(message)
            self.condition.notify_all()
    
    def dequeue(self) -> Dict[str, Any]:
        """Remove and return next message from queue"""
        with self.lock:
            while not self.queue:
                # Timeout prevents deadlock in single-threaded game loop.
                timed_out = not self.condition.wait(timeout=5.0)
                if timed_out:
                    return {}
            return self.queue.popleft()
    
    def size(self) -> int:
        """Get current queue size"""
        with self.lock:
            return len(self.queue)

# Create queues for all 12 pathways
PATHWAY_QUEUES = {
    "odin_wyrd": MessageQueue(),
    "freyja_dreams": MessageQueue(),
    "norns_wyrd": MessageQueue(),
    "saga_story": MessageQueue(),
    "saga_odin": MessageQueue(),
    "norns_fate": MessageQueue(),
    "dreams_wyrd": MessageQueue(),
    "freyja_wyrd": MessageQueue(),
    "asgard_wyrd": MessageQueue(),
    "midgard_wyrd": MessageQueue(),
    "alfheim_wyrd": MessageQueue(),
    "helheim_wyrd": MessageQueue()
}

def get_queue(pathway_name: str) -> MessageQueue:
    """Get message queue for specified pathway, auto-registering new ones."""
    if pathway_name not in PATHWAY_QUEUES:
        PATHWAY_QUEUES[pathway_name] = MessageQueue()
    return PATHWAY_QUEUES[pathway_name]