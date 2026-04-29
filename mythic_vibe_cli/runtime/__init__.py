"""Runtime primitives for Mythic Vibe CLI workflow execution.

Currently exposes:

- ``file_mutation_queue`` — per-path serialization for mutation operations.
"""

from .file_mutation_queue import file_mutation_queue, with_file_mutation_queue

__all__ = ["file_mutation_queue", "with_file_mutation_queue"]
