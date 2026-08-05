from __future__ import annotations
import unittest

from ai_monitoring_runtime.queueing import SymbolQueue, SymbolTask
from ai_monitoring_runtime.scheduler import SchedulerPreview
from ai_monitoring_runtime.workers import LoadBalancer, WorkerPool


class Tests(unittest.TestCase):
    def test_priority_queue(self):
        queue = SymbolQueue()
        queue.put(SymbolTask("1", "AAPL", 1, "s"))
        queue.put(SymbolTask("2", "MSFT", 5, "s"))
        self.assertEqual(queue.get().task_id, "2")

    def test_duplicate_task_rejected(self):
        queue = SymbolQueue()
        queue.put(SymbolTask("1", "AAPL", 1, "s"))
        with self.assertRaises(ValueError):
            queue.put(SymbolTask("1", "MSFT", 2, "s"))

    def test_worker_creates_no_order(self):
        queue = SymbolQueue()
        queue.put(SymbolTask("1", "AAPL", 1, "s"))
        result = WorkerPool(1).drain(queue)[0]
        self.assertFalse(result["order_created"])
        self.assertFalse(result["broker_network_used"])

    def test_load_balanced(self):
        queue = SymbolQueue()
        for index in range(6):
            queue.put(SymbolTask(str(index), f"S{index}", 1, "s"))
        results = WorkerPool(3).drain(queue)
        balance = LoadBalancer().summarize(
            results=results,
            worker_count=3,
        )
        self.assertTrue(balance["balanced"])

    def test_scheduler_preview_only(self):
        result = SchedulerPreview().plan(
            task_count=8,
            worker_count=3,
            interval_seconds=60,
        )
        self.assertFalse(result["automatic_scheduler_started"])
        self.assertFalse(result["actual_parallel_runtime_started"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
