from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import unittest

from continuous_paper_runtime import (
    ContinuousPaperRuntime,
    ContinuousRuntimeAction,
    ContinuousRuntimeConfig,
    ContinuousRuntimeState,
)
from paper_runtime_stability import StabilityAction, WatchdogStatus
from paper_scheduler import (
    MarketSessionPhase,
    SchedulerAction,
    SchedulerDecision,
)


class FakeScheduler:
    def __init__(self, actions):
        self.actions = list(actions)
        self.recover_action = SchedulerAction.RECOVER_SESSION
        self.tick_count = 0
        self.recover_count = 0

    def tick(self):
        self.tick_count += 1
        action = self.actions.pop(0) if self.actions else SchedulerAction.WAIT
        return SchedulerDecision(
            decided_at=datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
            phase=(
                MarketSessionPhase.AFTER_HOURS
                if action == SchedulerAction.CLOSE_SESSION
                else MarketSessionPhase.REGULAR
            ),
            action=action,
            reason="test",
            session_date=date(2026, 8, 3),
            next_wakeup_seconds=1,
        )

    def recover(self):
        self.recover_count += 1
        return SchedulerDecision(
            decided_at=datetime(2026, 8, 3, 13, 30, tzinfo=timezone.utc),
            phase=MarketSessionPhase.REGULAR,
            action=self.recover_action,
            reason="recover",
            session_date=date(2026, 8, 3),
            next_wakeup_seconds=1,
        )


class FakeIntegrationResult:
    def __init__(self, detail="ok"):
        self.detail = detail


class FakeIntegration:
    def __init__(self):
        self.actions = []

    def handle(self, decision):
        self.actions.append(decision.action)
        return FakeIntegrationResult(decision.action.value.lower())


@dataclass
class FakeStabilityResult:
    action: StabilityAction


class FakeStability:
    def __init__(self):
        self.watchdog_statuses = []
        self.cycle_actions = []
        self.heartbeat_count = 0
        self.watchdog_count = 0
        self.recovery_count = 0
        self.shutdown_count = 0
        self.network_requests_executed = 0
        self.write_requests_executed = 0
        self.actual_paper_orders_submitted = 0
        self.live_orders_submitted = 0

    def check_watchdog(self):
        self.watchdog_count += 1
        return self.watchdog_statuses.pop(0) if self.watchdog_statuses else WatchdogStatus.HEALTHY

    def heartbeat(self):
        self.heartbeat_count += 1
        return WatchdogStatus.HEALTHY

    def run_cycle(self):
        action = self.cycle_actions.pop(0) if self.cycle_actions else StabilityAction.CYCLE_COMPLETED
        return FakeStabilityResult(action)

    def attempt_recovery(self):
        self.recovery_count += 1
        return FakeStabilityResult(StabilityAction.RECOVERED)

    def graceful_shutdown(self):
        self.shutdown_count += 1
        return FakeStabilityResult(StabilityAction.SHUTDOWN)


class ContinuousPaperRuntimeTests(unittest.TestCase):
    def make_runtime(self, actions, **config_overrides):
        scheduler = FakeScheduler(actions)
        integration = FakeIntegration()
        stability = FakeStability()
        sleeps = []
        config = {
            "max_ticks": 20,
            "heartbeat_every_ticks": 1,
            "stop_on_session_close": True,
            "stop_on_skip_day": True,
            "recover_on_circuit_open": True,
        }
        config.update(config_overrides)
        runtime = ContinuousPaperRuntime(
            scheduler=scheduler,
            integration=integration,
            stability=stability,
            config=ContinuousRuntimeConfig(**config),
            sleep=sleeps.append,
        )
        return runtime, scheduler, integration, stability, sleeps

    def test_start(self):
        runtime, *_ = self.make_runtime([])
        result = runtime.start()
        self.assertEqual(result.action, ContinuousRuntimeAction.STARTED)
        self.assertEqual(runtime.state, ContinuousRuntimeState.RUNNING)

    def test_start_invalid_state(self):
        runtime, *_ = self.make_runtime([])
        runtime.start()
        with self.assertRaises(RuntimeError):
            runtime.start()

    def test_prepare_wait_tick(self):
        runtime, _, integration, _, sleeps = self.make_runtime([SchedulerAction.PREPARE])
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.WAITED)
        self.assertEqual(integration.actions, [SchedulerAction.PREPARE])
        self.assertEqual(sleeps, [1])

    def test_cycle_tick(self):
        runtime, _, integration, _, _ = self.make_runtime([SchedulerAction.RUN_CYCLE])
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.TICK_COMPLETED)
        self.assertEqual(runtime.stats.cycles_completed, 1)
        self.assertEqual(integration.actions, [SchedulerAction.RUN_CYCLE])

    def test_cycle_failure_waits(self):
        runtime, _, integration, stability, _ = self.make_runtime([SchedulerAction.RUN_CYCLE])
        stability.cycle_actions = [StabilityAction.CYCLE_FAILED]
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.WAITED)
        self.assertEqual(integration.actions, [])

    def test_circuit_open_recovers(self):
        runtime, _, _, stability, _ = self.make_runtime([SchedulerAction.RUN_CYCLE])
        stability.cycle_actions = [StabilityAction.CIRCUIT_OPEN]
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.RECOVERED)
        self.assertEqual(stability.recovery_count, 1)

    def test_watchdog_stale_recovers(self):
        runtime, _, _, stability, _ = self.make_runtime([SchedulerAction.WAIT])
        stability.watchdog_statuses = [WatchdogStatus.STALE]
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.RECOVERED)
        self.assertEqual(runtime.stats.recoveries_completed, 1)

    def test_close_requests_stop(self):
        runtime, _, _, _, _ = self.make_runtime([SchedulerAction.CLOSE_SESSION])
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.SESSION_CLOSED)
        self.assertTrue(runtime.stop_requested)

    def test_skip_requests_stop(self):
        runtime, _, _, _, _ = self.make_runtime([SchedulerAction.SKIP_DAY])
        runtime.start()
        result = runtime.tick()
        self.assertEqual(result.action, ContinuousRuntimeAction.SKIPPED)
        self.assertTrue(runtime.stop_requested)

    def test_request_stop_idempotent(self):
        runtime, *_ = self.make_runtime([])
        runtime.start()
        runtime.request_stop()
        runtime.request_stop()
        self.assertEqual(runtime.stats.stop_requests, 1)

    def test_run_stops_on_close(self):
        runtime, _, _, stability, _ = self.make_runtime([
            SchedulerAction.PREPARE,
            SchedulerAction.START_SESSION,
            SchedulerAction.RUN_CYCLE,
            SchedulerAction.CLOSE_SESSION,
        ])
        runtime.start()
        result = runtime.run()
        self.assertEqual(result.action, ContinuousRuntimeAction.STOPPED)
        self.assertEqual(runtime.stats.cycles_completed, 1)
        self.assertEqual(stability.shutdown_count, 1)

    def test_max_ticks_shutdown(self):
        runtime, _, _, stability, _ = self.make_runtime(
            [SchedulerAction.WAIT] * 3,
            max_ticks=3,
            stop_on_session_close=False,
            stop_on_skip_day=False,
        )
        runtime.start()
        runtime.run()
        self.assertEqual(runtime.stats.ticks_started, 3)
        self.assertEqual(stability.shutdown_count, 1)

    def test_restart(self):
        runtime, scheduler, integration, stability, _ = self.make_runtime([])
        runtime.state = ContinuousRuntimeState.STOPPED
        result = runtime.restart()
        self.assertEqual(result.action, ContinuousRuntimeAction.RECOVERED)
        self.assertEqual(scheduler.recover_count, 1)
        self.assertEqual(integration.actions, [SchedulerAction.RECOVER_SESSION])
        self.assertEqual(stability.recovery_count, 1)

    def test_shutdown_idempotent(self):
        runtime, _, _, stability, _ = self.make_runtime([])
        runtime.start()
        runtime.shutdown()
        runtime.shutdown()
        self.assertEqual(stability.shutdown_count, 1)

    def test_heartbeat_each_tick(self):
        runtime, _, _, stability, _ = self.make_runtime([
            SchedulerAction.WAIT,
            SchedulerAction.WAIT,
            SchedulerAction.WAIT,
        ])
        runtime.start()
        for _ in range(3):
            runtime.tick()
        self.assertEqual(stability.heartbeat_count, 3)

    def test_heartbeat_cadence(self):
        runtime, _, _, stability, _ = self.make_runtime(
            [SchedulerAction.WAIT] * 4,
            heartbeat_every_ticks=2,
        )
        runtime.start()
        for _ in range(4):
            runtime.tick()
        self.assertEqual(stability.heartbeat_count, 2)

    def test_network_and_orders_zero(self):
        runtime, *_ = self.make_runtime([SchedulerAction.RUN_CYCLE])
        runtime.start()
        runtime.tick()
        self.assertEqual(runtime.network_requests_executed, 0)
        self.assertEqual(runtime.write_requests_executed, 0)
        self.assertEqual(runtime.actual_paper_orders_submitted, 0)
        self.assertEqual(runtime.live_orders_submitted, 0)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            ContinuousRuntimeConfig(max_ticks=0).validate()


if __name__ == "__main__":
    unittest.main()
