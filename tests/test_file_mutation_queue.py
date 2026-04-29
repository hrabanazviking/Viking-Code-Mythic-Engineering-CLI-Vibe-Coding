# Spec ported from badlogic/pi-mono (packages/coding-agent/test/file-mutation-queue.test.ts).
# Upstream project: pi (pi-coding-agent), licensed under the MIT License.
# Copyright (c) 2025 Mario Zechner.
# The Python implementation under test (mythic_vibe_cli.runtime.file_mutation_queue)
# is licensed under the Apache License, Version 2.0.
"""Tests for the Pi-derived file mutation queue, ported to a synchronous
threading model in Python."""

from __future__ import annotations

import threading
import time
import unittest
from pathlib import Path
import tempfile

import importlib

from mythic_vibe_cli.runtime.file_mutation_queue import (
    file_mutation_queue,
    with_file_mutation_queue,
)

fmq_module = importlib.import_module("mythic_vibe_cli.runtime.file_mutation_queue")


class FileMutationQueueTests(unittest.TestCase):
    def test_serializes_operations_for_same_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "same.txt"
            order: list[str] = []
            order_lock = threading.Lock()

            def task(label: str, hold_seconds: float) -> None:
                with file_mutation_queue(target):
                    with order_lock:
                        order.append(f"{label}:start")
                    time.sleep(hold_seconds)
                    with order_lock:
                        order.append(f"{label}:end")

            t1 = threading.Thread(target=task, args=("first", 0.05))
            t2 = threading.Thread(target=task, args=("second", 0.0))
            t1.start()
            time.sleep(0.01)
            t2.start()
            t1.join()
            t2.join()

            self.assertEqual(order, ["first:start", "first:end", "second:start", "second:end"])

    def test_different_files_proceed_in_parallel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            file_a = Path(tmp) / "a.txt"
            file_b = Path(tmp) / "b.txt"
            order: list[str] = []
            order_lock = threading.Lock()

            def task(label: str, file: Path) -> None:
                with file_mutation_queue(file):
                    with order_lock:
                        order.append(f"{label}:start")
                    time.sleep(0.05)
                    with order_lock:
                        order.append(f"{label}:end")

            t_a = threading.Thread(target=task, args=("a", file_a))
            t_b = threading.Thread(target=task, args=("b", file_b))
            t_a.start()
            t_b.start()
            t_a.join()
            t_b.join()

            self.assertLess(order.index("a:start"), order.index("a:end"))
            self.assertLess(order.index("b:start"), order.index("b:end"))
            # b started before a finished proves parallelism
            self.assertLess(order.index("b:start"), order.index("a:end"))

    def test_uses_same_queue_for_symlink_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "target.txt"
            target.write_text("hello\n", encoding="utf-8")
            alias = Path(tmp) / "alias.txt"
            try:
                alias.symlink_to(target)
            except (OSError, NotImplementedError):
                self.skipTest("symlink creation not permitted on this platform")

            order: list[str] = []
            order_lock = threading.Lock()

            def task(label: str, file: Path, hold_seconds: float) -> None:
                with file_mutation_queue(file):
                    with order_lock:
                        order.append(f"{label}:start")
                    time.sleep(hold_seconds)
                    with order_lock:
                        order.append(f"{label}:end")

            t_target = threading.Thread(target=task, args=("target", target, 0.05))
            t_alias = threading.Thread(target=task, args=("alias", alias, 0.0))
            t_target.start()
            time.sleep(0.01)
            t_alias.start()
            t_target.join()
            t_alias.join()

            self.assertEqual(order, ["target:start", "target:end", "alias:start", "alias:end"])

    def test_with_file_mutation_queue_function_form_returns_callable_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "func.txt"
            calls: list[int] = []

            def task() -> str:
                calls.append(1)
                return "result"

            result = with_file_mutation_queue(target, task)

            self.assertEqual(result, "result")
            self.assertEqual(calls, [1])

    def test_lock_entry_is_dropped_after_last_waiter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cleanup.txt"
            key = fmq_module._mutation_queue_key(target)

            with file_mutation_queue(target):
                self.assertIn(key, fmq_module._locks)
                self.assertEqual(fmq_module._locks[key].refcount, 1)

            self.assertNotIn(key, fmq_module._locks)

    def test_lock_entry_persists_while_other_waiters_remain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "survives.txt"
            key = fmq_module._mutation_queue_key(target)
            checkpoint = threading.Event()
            release = threading.Event()

            def slow_task() -> None:
                with file_mutation_queue(target):
                    checkpoint.set()
                    release.wait(timeout=2.0)

            slow = threading.Thread(target=slow_task)
            slow.start()
            self.assertTrue(checkpoint.wait(timeout=1.0))
            self.assertEqual(fmq_module._locks[key].refcount, 1)

            release.set()
            slow.join(timeout=2.0)
            self.assertNotIn(key, fmq_module._locks)


if __name__ == "__main__":
    unittest.main()
