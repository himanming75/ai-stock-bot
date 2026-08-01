from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from runtime_engine import (
    Event,
    EventBus,
    HeartbeatMonitor,
    HeartbeatStatus,
    JsonRecoveryStore,
    ManualClock,
    RuntimeConfig,
    RuntimeManager,
    RuntimeState,
    Scheduler,
)


class RuntimeFoundationTests(unittest.TestCase):
    def test_event_bus_publish_and_unsubscribe(self):
        bus = EventBus()
        seen = []
        unsubscribe = bus.subscribe("x", lambda event: seen.append(event.payload["value"]))
        count = bus.publish(Event("x", {"value": 3}, datetime.now(timezone.utc)))
        self.assertEqual(count, 1)
        self.assertEqual(seen, [3])
        unsubscribe()
        self.assertEqual(bus.publish(Event("x", {"value": 4}, datetime.now(timezone.utc))), 0)

    def test_scheduler_runs_due_tasks_without_threads(self):
        clock = ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc))
        scheduler = Scheduler()
        calls = []
        scheduler.add_interval(name="sample", interval_seconds=10, first_run_at=clock.now(), callback=lambda: calls.append(1))
        self.assertEqual(scheduler.run_due(clock.now()), ["sample"])
        self.assertEqual(calls, [1])
        clock.advance(seconds=9)
        self.assertEqual(scheduler.run_due(clock.now()), [])
        clock.advance(seconds=1)
        self.assertEqual(scheduler.run_due(clock.now()), ["sample"])

    def test_scheduler_rejects_duplicates(self):
        clock = ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc))
        scheduler = Scheduler()
        scheduler.add_interval(name="x", interval_seconds=1, first_run_at=clock.now(), callback=lambda: None)
        with self.assertRaises(ValueError):
            scheduler.add_interval(name="x", interval_seconds=1, first_run_at=clock.now(), callback=lambda: None)

    def test_heartbeat_status(self):
        clock = ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc))
        monitor = HeartbeatMonitor(30)
        self.assertEqual(monitor.status(clock.now()), HeartbeatStatus.NEVER)
        monitor.beat(clock.now())
        self.assertEqual(monitor.status(clock.now()), HeartbeatStatus.HEALTHY)
        clock.advance(seconds=31)
        self.assertEqual(monitor.status(clock.now()), HeartbeatStatus.STALE)

    def test_recovery_store_round_trip(self):
        from runtime_engine import RecoverySnapshot
        with TemporaryDirectory() as temp:
            path = Path(temp) / "snapshot.json"
            store = JsonRecoveryStore(path)
            now = datetime(2026, 8, 1, tzinfo=timezone.utc)
            snapshot = RecoverySnapshot("RUNNING", now, 2, [], {"tick_count": 4})
            store.save(snapshot)
            loaded = store.load()
            self.assertEqual(loaded, snapshot)

    def test_runtime_config_blocks_write_enablement(self):
        with self.assertRaises(ValueError):
            RuntimeConfig(network_write_enabled=True).validate()
        with self.assertRaises(ValueError):
            RuntimeConfig(paper_order_submission_enabled=True).validate()
        with self.assertRaises(ValueError):
            RuntimeConfig(live_trading_enabled=True).validate()

    def test_runtime_lifecycle(self):
        with TemporaryDirectory() as temp:
            clock = ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc))
            bus = EventBus()
            manager = RuntimeManager(
                config=RuntimeConfig(),
                clock=clock,
                event_bus=bus,
                scheduler=Scheduler(),
                recovery_store=JsonRecoveryStore(Path(temp) / "recovery.json"),
            )
            manager.start()
            self.assertEqual(manager.state, RuntimeState.RUNNING)
            self.assertEqual(set(manager.tick()), {"heartbeat", "recovery_snapshot"})
            self.assertEqual(manager.health()["heartbeat_status"], "HEALTHY")
            manager.shutdown()
            self.assertEqual(manager.state, RuntimeState.STOPPED)
            topics = [event.topic for event in bus.history()]
            self.assertIn("runtime.started", topics)
            self.assertIn("runtime.stopped", topics)

    def test_runtime_repeated_ticks(self):
        with TemporaryDirectory() as temp:
            clock = ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc))
            manager = RuntimeManager(
                config=RuntimeConfig(heartbeat_interval_seconds=5, heartbeat_stale_after_seconds=15, recovery_interval_seconds=10),
                clock=clock,
                event_bus=EventBus(),
                scheduler=Scheduler(),
                recovery_store=JsonRecoveryStore(Path(temp) / "recovery.json"),
            )
            manager.start()
            manager.tick()
            clock.advance(seconds=5)
            self.assertEqual(manager.tick(), ["heartbeat"])
            clock.advance(seconds=5)
            self.assertEqual(set(manager.tick()), {"heartbeat", "recovery_snapshot"})
            self.assertEqual(manager.tick_count, 3)

    def test_shutdown_before_start_is_safe(self):
        with TemporaryDirectory() as temp:
            manager = RuntimeManager(
                config=RuntimeConfig(),
                clock=ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc)),
                event_bus=EventBus(),
                scheduler=Scheduler(),
                recovery_store=JsonRecoveryStore(Path(temp) / "recovery.json"),
            )
            manager.shutdown()
            self.assertEqual(manager.state, RuntimeState.STOPPED)

    def test_health_reports_all_safety_flags_false(self):
        with TemporaryDirectory() as temp:
            manager = RuntimeManager(
                config=RuntimeConfig(),
                clock=ManualClock(datetime(2026, 8, 1, tzinfo=timezone.utc)),
                event_bus=EventBus(),
                scheduler=Scheduler(),
                recovery_store=JsonRecoveryStore(Path(temp) / "recovery.json"),
            )
            health = manager.health()
            self.assertFalse(health["network_write_enabled"])
            self.assertFalse(health["paper_order_submission_enabled"])
            self.assertFalse(health["live_trading_enabled"])


if __name__ == "__main__":
    unittest.main()
