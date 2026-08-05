from pathlib import Path
import tempfile
import unittest

from live_runtime.cycle_registry import (
    DuplicateLiveCycleError,
    LiveCycleRegistry,
)
from live_runtime.lock import (
    LiveRuntimeAlreadyRunning,
    LiveRuntimeLock,
)
from live_runtime.models import LiveRuntimePolicy
from live_runtime.runtime import run_offline_live_runtime


class Tests(unittest.TestCase):
    def test_policy(self):
        result = LiveRuntimePolicy(
            cycle_interval_seconds=60,
            maximum_cycles_per_session=390,
            require_market_open=True,
            fail_closed=True,
            require_l1=True,
            require_l2_actual=True,
            require_l3_actual=True,
            require_l4_actual=True,
            require_p5_actual=True,
        ).evaluate()
        self.assertTrue(result["valid"])

    def test_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            lock = LiveRuntimeLock(Path(directory) / "lock.json")
            lock.acquire("a")
            with self.assertRaises(LiveRuntimeAlreadyRunning):
                lock.acquire("b")
            lock.release()

    def test_duplicate_cycle(self):
        with tempfile.TemporaryDirectory() as directory:
            registry = LiveCycleRegistry(
                Path(directory) / "cycles.json"
            )
            registry.reserve("c1")
            with self.assertRaises(DuplicateLiveCycleError):
                registry.reserve("c1")

    def test_three_cycle_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_offline_live_runtime(
                root=Path(directory),
                runtime_id="test",
                cycles=3,
                market_open=True,
            )
        self.assertEqual(result["completed_cycle_count"], 3)
        self.assertFalse(result["actual_live_runtime_allowed"])

    def test_market_closed_blocks(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_offline_live_runtime(
                root=Path(directory),
                runtime_id="test",
                cycles=3,
                market_open=False,
            )
        self.assertEqual(result["completed_cycle_count"], 0)
        self.assertEqual(
            result["state"],
            "LIVE_RUNTIME_BLOCKED_MARKET_CLOSED",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
