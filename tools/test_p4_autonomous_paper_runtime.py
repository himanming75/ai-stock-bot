from __future__ import annotations
import tempfile
import unittest
from pathlib import Path

from broker_integration.p4_lock import (
    RuntimeLockError,
    acquire_lock,
    release_lock,
)
from broker_integration.p4_offline_cycle import OfflineCanonicalCycle
from broker_integration.p4_runtime import AutonomousPaperRuntime
from broker_integration.p4_runtime_models import RuntimePolicy


def paths(base: Path):
    return {
        "lock": base / "lock.json",
        "heartbeat": base / "heartbeat.json",
        "cycle_registry": base / "cycles.json",
        "cycle_ledger": base / "cycles.jsonl",
        "checkpoint": base / "checkpoint.json",
    }


def policy(cycles=2):
    return RuntimePolicy(
        cycle_interval_seconds=1,
        maximum_cycles_per_session=cycles,
        require_market_open=True,
        require_p2_actual_validation=False,
        require_p3_actual_validation=False,
        fail_closed=True,
    )


class Tests(unittest.TestCase):
    def test_lock_blocks_second_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "lock.json"
            acquire_lock(path, "one")
            with self.assertRaises(RuntimeLockError):
                acquire_lock(path, "two")
            release_lock(path, "one")

    def test_healthy_runtime_completes_cycles(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = AutonomousPaperRuntime(
                root=base,
                policy=policy(3),
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="healthy",
            ).run()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["completed_cycle_count"], 3)

    def test_kill_switch_blocks_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = AutonomousPaperRuntime(
                root=base,
                policy=policy(),
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": True
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="blocked-kill",
            ).run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("kill_switch_inactive", result["blockers"])

    def test_market_closed_blocks_runtime(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = AutonomousPaperRuntime(
                root=base,
                policy=policy(),
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": False},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="blocked-market",
            ).run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("market_condition", result["blockers"])

    def test_actual_validation_required(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            actual_policy = RuntimePolicy(
                cycle_interval_seconds=1,
                maximum_cycles_per_session=1,
                require_market_open=True,
                require_p2_actual_validation=True,
                require_p3_actual_validation=True,
                fail_closed=True,
            )
            result = AutonomousPaperRuntime(
                root=base,
                policy=actual_policy,
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="validation-required",
            ).run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("p2_actual_validation", result["blockers"])
        self.assertIn("p3_actual_validation", result["blockers"])

    def test_fail_closed_cycle_result(self):
        class FailingCycle:
            def __call__(self, context):
                return {
                    "stage": "P4",
                    "status": "PASS",
                    "reconciliation_passed": False,
                    "new_order_submission_allowed": False,
                    "blockers": ["P3_RECONCILIATION_FAILED"],
                }

        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = AutonomousPaperRuntime(
                root=base,
                policy=policy(),
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=FailingCycle(),
                sleeper=lambda _: None,
                runtime_id="fail-closed",
            ).run()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("P3_RECONCILIATION_FAILED", result["blockers"])

    def test_lock_released_after_session(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            mapping = paths(base)
            AutonomousPaperRuntime(
                root=base,
                policy=policy(1),
                paths=mapping,
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="release-test",
            ).run()
            self.assertFalse(mapping["lock"].exists())

    def test_zero_order_design(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            result = AutonomousPaperRuntime(
                root=base,
                policy=policy(1),
                paths=paths(base),
                market_clock_reader=lambda: {"is_open": True},
                kill_switch_reader=lambda: {
                    "kill_switch_active": False
                },
                validation_reader=lambda: {
                    "p2_actual_validated": False,
                    "p3_actual_validated": False,
                },
                cycle_executor=OfflineCanonicalCycle(),
                sleeper=lambda _: None,
                runtime_id="zero-order",
            ).run()
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
