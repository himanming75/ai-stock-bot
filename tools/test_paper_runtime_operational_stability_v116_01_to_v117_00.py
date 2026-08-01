from __future__ import annotations

from dataclasses import dataclass
import unittest

from paper_runtime_stability import (
    OperationalStabilityConfig,
    OperationalStabilityController,
    StabilityAction,
    WatchdogStatus,
)


@dataclass
class FakeState:
    value: str


class MutableMonotonic:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


class FakeRuntime:
    def __init__(self):
        self.state = FakeState("READY")
        self.outcomes = []
        self.heartbeat_count = 0
        self.recovery_count = 0
        self.stop_count = 0
        self.recover_count = 0
        self.recover_failures = 0

    def run_cycle(self):
        outcome = self.outcomes.pop(0) if self.outcomes else True
        if isinstance(outcome, Exception):
            raise outcome
        return {"cycle_completed": bool(outcome)}

    def heartbeat(self):
        self.heartbeat_count += 1

    def save_recovery(self):
        self.recovery_count += 1

    def recover(self):
        self.recover_count += 1
        if self.recover_failures > 0:
            self.recover_failures -= 1
            raise RuntimeError("recover failed")
        self.state = FakeState("READY")

    def stop(self):
        self.stop_count += 1
        self.state = FakeState("STOPPED")


class OperationalStabilityTests(unittest.TestCase):
    def setUp(self):
        self.clock = MutableMonotonic()
        self.sleeps = []
        self.runtime = FakeRuntime()
        self.controller = OperationalStabilityController(
            runtime=self.runtime,
            config=OperationalStabilityConfig(
                cycle_timeout_seconds=10,
                heartbeat_timeout_seconds=30,
                max_consecutive_failures=3,
                max_recovery_attempts=2,
                initial_backoff_seconds=5,
                max_backoff_seconds=60,
                backoff_multiplier=3,
            ),
            monotonic=self.clock,
            sleep=self.sleeps.append,
        )

    def test_successful_cycle(self):
        result = self.controller.run_cycle()
        self.assertEqual(result.action, StabilityAction.CYCLE_COMPLETED)
        self.assertEqual(self.controller.stats.cycles_completed, 1)

    def test_failure_backoff(self):
        self.runtime.outcomes = [RuntimeError("failure")]
        result = self.controller.run_cycle()
        self.assertEqual(result.action, StabilityAction.CYCLE_FAILED)
        self.assertEqual(result.backoff_seconds, 5)
        self.assertEqual(self.sleeps, [5])

    def test_exponential_backoff(self):
        self.runtime.outcomes = [RuntimeError("one"), RuntimeError("two")]
        first = self.controller.run_cycle()
        second = self.controller.run_cycle()
        self.assertEqual(first.backoff_seconds, 5)
        self.assertEqual(second.backoff_seconds, 15)

    def test_third_failure_opens_circuit(self):
        self.runtime.outcomes = [
            RuntimeError("one"), RuntimeError("two"), RuntimeError("three")
        ]
        self.controller.run_cycle()
        self.controller.run_cycle()
        result = self.controller.run_cycle()
        self.assertEqual(result.action, StabilityAction.CIRCUIT_OPEN)
        self.assertTrue(self.controller.circuit_open)

    def test_open_circuit_blocks_cycle(self):
        self.controller.circuit_open = True
        result = self.controller.run_cycle()
        self.assertEqual(result.action, StabilityAction.CIRCUIT_OPEN)
        self.assertEqual(self.controller.stats.cycles_attempted, 0)

    def test_success_resets_failure_count(self):
        self.runtime.outcomes = [RuntimeError("one"), True]
        self.controller.run_cycle()
        self.controller.run_cycle()
        self.assertEqual(self.controller.consecutive_failures, 0)

    def test_watchdog_healthy(self):
        self.clock.advance(20)
        self.assertEqual(self.controller.check_watchdog(), WatchdogStatus.HEALTHY)

    def test_watchdog_stale(self):
        self.clock.advance(31)
        self.assertEqual(self.controller.check_watchdog(), WatchdogStatus.STALE)
        self.assertTrue(self.controller.circuit_open)

    def test_heartbeat_refreshes_watchdog(self):
        self.clock.advance(25)
        self.controller.heartbeat()
        self.clock.advance(20)
        self.assertEqual(self.controller.check_watchdog(), WatchdogStatus.HEALTHY)

    def test_recovery_success(self):
        self.controller.circuit_open = True
        result = self.controller.attempt_recovery()
        self.assertEqual(result.action, StabilityAction.RECOVERED)
        self.assertFalse(self.controller.circuit_open)

    def test_recovery_retry(self):
        self.controller.circuit_open = True
        self.runtime.recover_failures = 1
        result = self.controller.attempt_recovery()
        self.assertEqual(result.action, StabilityAction.RECOVERED)
        self.assertEqual(self.runtime.recover_count, 2)

    def test_recovery_failure_keeps_circuit_open(self):
        self.controller.circuit_open = True
        self.runtime.recover_failures = 2
        result = self.controller.attempt_recovery()
        self.assertEqual(result.action, StabilityAction.CIRCUIT_OPEN)
        self.assertTrue(self.controller.circuit_open)

    def test_graceful_shutdown(self):
        result = self.controller.graceful_shutdown()
        self.assertEqual(result.action, StabilityAction.SHUTDOWN)
        self.assertEqual(self.runtime.stop_count, 1)
        self.assertEqual(self.runtime.recovery_count, 1)

    def test_shutdown_idempotent(self):
        self.controller.graceful_shutdown()
        self.controller.graceful_shutdown()
        self.assertEqual(self.runtime.stop_count, 1)

    def test_long_run_500_cycles(self):
        for _ in range(500):
            result = self.controller.run_cycle()
            self.assertEqual(result.action, StabilityAction.CYCLE_COMPLETED)
        self.assertEqual(self.controller.stats.cycles_completed, 500)
        self.assertEqual(self.controller.stats.cycle_failures, 0)

    def test_network_and_orders_zero(self):
        self.controller.run_cycle()
        self.assertEqual(self.controller.network_requests_executed, 0)
        self.assertEqual(self.controller.write_requests_executed, 0)
        self.assertEqual(self.controller.actual_paper_orders_submitted, 0)
        self.assertEqual(self.controller.live_orders_submitted, 0)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            OperationalStabilityConfig(max_consecutive_failures=0).validate()


if __name__ == "__main__":
    unittest.main()
