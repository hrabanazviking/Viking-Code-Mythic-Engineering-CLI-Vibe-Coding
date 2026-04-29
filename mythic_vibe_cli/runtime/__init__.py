"""Runtime primitives for Mythic Vibe CLI workflow execution.

Currently exposes:

- ``file_mutation_queue`` — per-path serialization for mutation operations.
- ``output_guard`` — stdout cleanliness for protocol-output modes.
"""

from .file_mutation_queue import file_mutation_queue, with_file_mutation_queue
from .output_guard import (
    flush_raw_stdout,
    is_stdout_taken_over,
    restore_stdout,
    take_over_stdout,
    write_raw_stdout,
)

__all__ = [
    "file_mutation_queue",
    "with_file_mutation_queue",
    "take_over_stdout",
    "restore_stdout",
    "is_stdout_taken_over",
    "write_raw_stdout",
    "flush_raw_stdout",
]
