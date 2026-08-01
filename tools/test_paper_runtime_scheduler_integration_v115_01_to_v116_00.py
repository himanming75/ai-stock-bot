from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import unittest

from paper_runtime_scheduler import (
    IntegrationEventType,
    PaperRuntimeSchedulerIntegration,
    RuntimeSchedulerIntegrationConfig,
)
from paper_scheduler import (
    MarketSessionPhase,
    SchedulerAction,
    SchedulerDecision,
)


@dataclass
class FakeState:
    value: str


class FakeRuntime:
    def __init__(self):
        self.state = FakeState("CREATED")
        self.prepare_count = 0
        self.start_count = 0
        self.cycle_count = 0
        self.recover_count = 0
        self.stop_count = 0
        self.recovery_count = 0
        self.fail_cycle = False

    def prepare(self):
        self.prepare_count += 1
        self.state = FakeState("READY")

    def start(self):
        self.start_count += 1
        self.state = FakeState("READY")

    def run_cycle(self):
        if self.fail_cycle:
            raise RuntimeError("cycle failure")
        self.cycle_count += 1
        self.state = FakeState("RUNNING")
        return {"cycle_completed": True}

    def recover(self):
        self.recover_count += 1
        self.state = FakeState("READY")

    def save_recovery(self):
        self.recovery_count += 1

    def stop(self):
        self.stop_count += 1
        self.state = FakeState("STOPPED")


def decision(action):
    return SchedulerDecision(
        decided_at=datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
        phase=MarketSessionPhase.REGULAR,
        action=action,
        reason="test",
        session_date=date(2026, 8, 3),
        next_wakeup_seconds=60,
    )


class PaperRuntimeSchedulerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeRuntime()
        self.integration = PaperRuntimeSchedulerIntegration(
            runtime=self.runtime,
            config=RuntimeSchedulerIntegrationConfig(),
            now=lambda: datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
        )

    def test_prepare(self):
        result = self.integration.handle(decision(SchedulerAction.PREPARE))
        self.assertEqual(result.event_type, IntegrationEventType.PREPARED)
        self.assertEqual(self.runtime.prepare_count, 1)

    def test_start(self):
        result = self.integration.handle(decision(SchedulerAction.START_SESSION))
        self.assertEqual(result.event_type, IntegrationEventType.SESSION_STARTED)
        self.assertEqual(self.runtime.start_count, 1)

    def test_cycle(self):
        self.runtime.state = FakeState("READY")
        result = self.integration.handle(decision(SchedulerAction.RUN_CYCLE))
        self.assertTrue(result.cycle_completed)
        self.assertTrue(result.recovery_saved)
        self.assertEqual(self.runtime.cycle_count, 1)
        self.assertEqual(self.runtime.recovery_count, 1)

    def test_recover(self):
        result = self.integration.handle(decision(SchedulerAction.RECOVER_SESSION))
        self.assertEqual(result.event_type, IntegrationEventType.SESSION_RECOVERED)
        self.assertEqual(self.runtime.recover_count, 1)

    def test_close(self):
        self.runtime.state = FakeState("RUNNING")
        result = self.integration.handle(decision(SchedulerAction.CLOSE_SESSION))
        self.assertEqual(result.event_type, IntegrationEventType.SESSION_CLOSED)
        self.assertEqual(self.runtime.stop_count, 1)
        self.assertEqual(self.runtime.recovery_count, 1)

    def test_wait(self):
        result = self.integration.handle(decision(SchedulerAction.WAIT))
        self.assertEqual(result.event_type, IntegrationEventType.WAITING)

    def test_skip(self):
        result = self.integration.handle(decision(SchedulerAction.SKIP_DAY))
        self.assertEqual(result.event_type, IntegrationEventType.SKIPPED)

    def test_start_invalid_state(self):
        self.runtime.state = FakeState("RUNNING")
        with self.assertRaises(RuntimeError):
            self.integration.handle(decision(SchedulerAction.START_SESSION))

    def test_cycle_invalid_state(self):
        self.runtime.state = FakeState("STOPPED")
        with self.assertRaises(RuntimeError):
            self.integration.handle(decision(SchedulerAction.RUN_CYCLE))

    def test_cycle_failure_counted(self):
        self.runtime.state = FakeState("READY")
        self.runtime.fail_cycle = True
        with self.assertRaises(RuntimeError):
            self.integration.handle(decision(SchedulerAction.RUN_CYCLE))
        self.assertEqual(self.integration.stats.failures, 1)

    def test_stats_sequence(self):
        self.integration.handle(decision(SchedulerAction.PREPARE))
        self.integration.handle(decision(SchedulerAction.START_SESSION))
        self.integration.handle(decision(SchedulerAction.RUN_CYCLE))
        self.integration.handle(decision(SchedulerAction.RECOVER_SESSION))
        self.integration.handle(decision(SchedulerAction.CLOSE_SESSION))
        stats = self.integration.stats
        self.assertEqual(stats.scheduler_decisions_received, 5)
        self.assertEqual(stats.prepares, 1)
        self.assertEqual(stats.sessions_started, 1)
        self.assertEqual(stats.cycles_completed, 1)
        self.assertEqual(stats.sessions_recovered, 1)
        self.assertEqual(stats.sessions_closed, 1)

    def test_events_recorded(self):
        self.integration.handle(decision(SchedulerAction.PREPARE))
        self.assertEqual(len(self.integration.events), 1)

    def test_network_and_orders_zero(self):
        self.integration.handle(decision(SchedulerAction.PREPARE))
        self.assertEqual(self.integration.network_requests_executed, 0)
        self.assertEqual(self.integration.write_requests_executed, 0)
        self.assertEqual(self.integration.actual_paper_orders_submitted, 0)
        self.assertEqual(self.integration.live_orders_submitted, 0)

    def test_config_validation(self):
        RuntimeSchedulerIntegrationConfig().validate()


if __name__ == "__main__":
    unittest.main()
