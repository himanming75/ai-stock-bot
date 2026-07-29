import importlib.util
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("broker_session_manager_v35_0.py")
SPEC = importlib.util.spec_from_file_location(
    "broker_session_manager_v35_0",
    MODULE_PATH,
)
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = MOD
SPEC.loader.exec_module(MOD)


class BrokerSessionManagerV350Tests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 1, 1, tzinfo=timezone.utc)

    def test_paper_session_becomes_ready(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.PAPER,
            MOD.SessionMode.PAPER,
        )
        session.start(self.now)
        snapshot = session.snapshot(self.now)
        self.assertEqual(snapshot.state, "ready")
        self.assertTrue(snapshot.connected)
        self.assertTrue(snapshot.authenticated)
        self.assertFalse(snapshot.network_transport_enabled)

    def test_external_session_remains_disconnected(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.IBKR,
            MOD.SessionMode.LIVE,
        )
        session.start(self.now)
        snapshot = session.snapshot(self.now)
        self.assertEqual(snapshot.state, "disconnected")
        self.assertFalse(snapshot.connected)
        self.assertFalse(snapshot.authenticated)

    def test_timeout_expires_session(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.PAPER,
            MOD.SessionMode.PAPER,
            heartbeat_timeout_seconds=10,
        )
        session.start(self.now)
        event = session.evaluate_timeout(
            self.now + timedelta(seconds=11)
        )
        self.assertIsNotNone(event)
        self.assertEqual(session.state, MOD.SessionState.EXPIRED)

    def test_heartbeat_keeps_session_ready(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.PAPER,
            MOD.SessionMode.PAPER,
            heartbeat_timeout_seconds=10,
        )
        session.start(self.now)
        session.heartbeat(self.now + timedelta(seconds=5))
        event = session.evaluate_timeout(
            self.now + timedelta(seconds=12)
        )
        self.assertIsNone(event)
        self.assertEqual(session.state, MOD.SessionState.READY)

    def test_reconnect_backoff(self):
        policy = MOD.ReconnectPolicy(
            enabled=True,
            max_attempts=5,
            base_delay_seconds=2,
            max_delay_seconds=10,
        )
        self.assertEqual(policy.delay_for_attempt(1), 2)
        self.assertEqual(policy.delay_for_attempt(2), 4)
        self.assertEqual(policy.delay_for_attempt(3), 8)
        self.assertEqual(policy.delay_for_attempt(4), 10)

    def test_external_reconnect_never_uses_transport(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.ALPACA,
            MOD.SessionMode.LIVE,
        )
        session.start(self.now)
        event = session.request_reconnect(self.now)
        self.assertEqual(session.state, MOD.SessionState.DISCONNECTED)
        self.assertFalse(event.network_used)
        self.assertIn("transport is disabled", event.message)

    def test_audit_events_have_hashes(self):
        session = MOD.BrokerSession(
            MOD.BrokerName.PAPER,
            MOD.SessionMode.PAPER,
        )
        session.start(self.now)
        events = session.audit_log()
        self.assertGreaterEqual(len(events), 2)
        self.assertTrue(all(len(event.event_sha256) == 64 for event in events))

    def test_manager_dashboard(self):
        manager = MOD.BrokerSessionManager()
        paper = manager.create_session(
            MOD.BrokerName.PAPER,
            MOD.SessionMode.PAPER,
        )
        paper.start(self.now)
        dashboard = manager.dashboard()
        self.assertEqual(dashboard["status"], "PASS")
        self.assertEqual(dashboard["session_count"], 1)
        self.assertEqual(dashboard["ready_session_count"], 1)
        self.assertFalse(dashboard["network_transport_enabled"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
