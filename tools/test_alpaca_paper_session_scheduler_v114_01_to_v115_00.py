from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from paper_scheduler import (
    AlpacaPaperSessionScheduler,
    AtomicSchedulerStateStore,
    MarketSessionPhase,
    SchedulerAction,
    SchedulerState,
    SessionSchedulerConfig,
    TradingCalendarPolicy,
)


class MutableClock:
    def __init__(self, moment):
        self.moment = moment

    def now(self):
        return self.moment


class AlpacaPaperSessionSchedulerTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.path = Path(self.temp.name) / "scheduler.json"
        self.clock = MutableClock(datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc))
        self.calendar = TradingCalendarPolicy(
            holidays=frozenset({date(2026, 12, 25)})
        )

    def tearDown(self):
        self.temp.cleanup()

    def scheduler(self):
        return AlpacaPaperSessionScheduler(
            calendar=self.calendar,
            store=AtomicSchedulerStateStore(self.path),
            config=SessionSchedulerConfig(
                cycle_interval_seconds=60,
                heartbeat_interval_seconds=30,
                closed_poll_seconds=300,
                pre_market_poll_seconds=60,
            ),
            now=self.clock.now,
        )

    def set_et(self, hour, minute=0, *, day=3, month=8):
        # August is EDT, so ET = UTC-4.
        self.clock.moment = datetime(2026, month, day, hour, minute, tzinfo=timezone.utc) + timedelta(hours=4)

    def test_pre_market_prepare(self):
        self.set_et(8, 0)
        decision = self.scheduler().tick()
        self.assertEqual(decision.phase, MarketSessionPhase.PRE_MARKET)
        self.assertEqual(decision.action, SchedulerAction.PREPARE)

    def test_regular_start_then_cycle(self):
        self.set_et(9, 30)
        scheduler = self.scheduler()
        first = scheduler.tick()
        second = scheduler.tick()
        self.assertEqual(first.action, SchedulerAction.START_SESSION)
        self.assertEqual(second.action, SchedulerAction.RUN_CYCLE)
        self.assertEqual(scheduler.state.cycle_count, 1)

    def test_after_hours_closes_active_session(self):
        self.set_et(9, 30)
        scheduler = self.scheduler()
        scheduler.tick()
        self.set_et(16, 30)
        decision = scheduler.tick()
        self.assertEqual(decision.action, SchedulerAction.CLOSE_SESSION)
        self.assertFalse(scheduler.state.session_active)

    def test_weekend_skip(self):
        self.set_et(10, 0, day=1)
        decision = self.scheduler().tick()
        self.assertEqual(decision.phase, MarketSessionPhase.WEEKEND)
        self.assertEqual(decision.action, SchedulerAction.SKIP_DAY)

    def test_holiday_skip(self):
        self.clock.moment = datetime(2026, 12, 25, 15, 0, tzinfo=timezone.utc)
        decision = self.scheduler().tick()
        self.assertEqual(decision.phase, MarketSessionPhase.HOLIDAY)
        self.assertEqual(decision.action, SchedulerAction.SKIP_DAY)

    def test_state_persists(self):
        self.set_et(9, 30)
        scheduler = self.scheduler()
        scheduler.tick()
        loaded = AtomicSchedulerStateStore(self.path).load()
        self.assertTrue(loaded.session_active)

    def test_restart_recovers_active_regular_session(self):
        self.set_et(9, 30)
        scheduler = self.scheduler()
        scheduler.tick()
        restarted = self.scheduler()
        decision = restarted.recover()
        self.assertEqual(decision.action, SchedulerAction.RECOVER_SESSION)
        self.assertEqual(restarted.state.restart_count, 1)

    def test_restart_closes_stale_active_session(self):
        store = AtomicSchedulerStateStore(self.path)
        state = SchedulerState(
            session_active=True,
            session_date=date(2026, 8, 3),
        )
        store.save(state)
        self.set_et(17, 0)
        scheduler = self.scheduler()
        decision = scheduler.recover()
        self.assertEqual(decision.action, SchedulerAction.CLOSE_SESSION)
        self.assertTrue(scheduler.state.session_closed)

    def test_new_day_resets_cycle_count(self):
        self.set_et(9, 30)
        scheduler = self.scheduler()
        scheduler.tick()
        scheduler.tick()
        self.set_et(9, 30, day=4)
        scheduler.tick()
        self.assertEqual(scheduler.state.cycle_count, 0)

    def test_closed_market_wait(self):
        self.set_et(21, 0)
        decision = self.scheduler().tick()
        self.assertEqual(decision.action, SchedulerAction.WAIT)

    def test_network_and_orders_remain_zero(self):
        scheduler = self.scheduler()
        scheduler.tick()
        self.assertEqual(scheduler.network_requests_executed, 0)
        self.assertEqual(scheduler.write_requests_executed, 0)
        self.assertEqual(scheduler.actual_paper_orders_submitted, 0)
        self.assertEqual(scheduler.live_orders_submitted, 0)

    def test_config_validation(self):
        with self.assertRaises(ValueError):
            SessionSchedulerConfig(cycle_interval_seconds=0).validate()

    def test_naive_datetime_rejected(self):
        self.clock.moment = datetime(2026, 8, 3, 9, 30)
        with self.assertRaises(ValueError):
            self.scheduler().tick()


if __name__ == "__main__":
    unittest.main()
