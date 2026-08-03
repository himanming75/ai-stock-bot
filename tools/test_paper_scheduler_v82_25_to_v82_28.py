
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from paper_runtime.scheduler_v82_25_28 import (
    run_paper_trading_scheduler,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def policy(self):
        return {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "continuous_loop_enabled": False,
            "windows_task_install_enabled": False,
            "interval_seconds": 300,
            "heartbeat_timeout_seconds": 900,
            "maximum_lateness_seconds": 120,
        }

    def run_case(
        self,
        *,
        session_running=True,
        started_minutes_ago=4,
        heartbeat_minutes_ago=None,
        authorize=False,
        complete=False,
        write_heartbeat=False,
        active_tick=False,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        now = datetime(2026, 8, 3, 17, 0, tzinfo=timezone.utc)

        self.write(root / "session.json", {
            "state": (
                "PAPER_SESSION_RUNNING"
                if session_running
                else "PAPER_SESSION_READY_TO_START"
            ),
            "session_active": session_running,
            "session_id": "paper-session-test",
            "started_at": (
                now - timedelta(minutes=started_minutes_ago)
            ).isoformat(),
            "observed_at": now.isoformat(),
        })
        self.write(root / "policy.json", self.policy())

        if heartbeat_minutes_ago is not None:
            self.write(root / "heartbeat.json", {
                "last_heartbeat_at": (
                    now - timedelta(minutes=heartbeat_minutes_ago)
                ).isoformat(),
                "last_tick_completed_at": (
                    now - timedelta(minutes=started_minutes_ago)
                ).isoformat(),
            })

        if active_tick:
            self.write(root / "lock.json", {
                "active": True,
                "tick_id": "paper-tick-existing",
                "session_id": "paper-session-test",
            })

        result = run_paper_trading_scheduler(
            session_result_path=root / "session.json",
            policy_path=root / "policy.json",
            heartbeat_path=root / "heartbeat.json",
            tick_lock_path=root / "lock.json",
            tick_ledger_path=root / "ledger.jsonl",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            write_heartbeat=write_heartbeat,
            authorize_tick=authorize,
            complete_tick=complete,
            observed_at=now,
        )
        return result, root

    def test_wait_session(self):
        result, _ = self.run_case(session_running=False)
        self.assertEqual(result["state"], "WAIT_PAPER_SESSION_RUNNING")

    def test_wait_interval(self):
        result, _ = self.run_case(started_minutes_ago=4)
        self.assertEqual(result["state"], "PAPER_SCHEDULER_WAIT_INTERVAL")

    def test_tick_due(self):
        result, _ = self.run_case(started_minutes_ago=6)
        self.assertEqual(result["state"], "PAPER_SCHEDULER_TICK_DUE")

    def test_authorize_tick(self):
        result, root = self.run_case(
            started_minutes_ago=6,
            authorize=True,
        )
        self.assertTrue(result["tick_authorized"])
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_tick_blocked(self):
        result, _ = self.run_case(
            started_minutes_ago=6,
            authorize=True,
            active_tick=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_complete_tick(self):
        result, _ = self.run_case(
            started_minutes_ago=6,
            complete=True,
            active_tick=True,
        )
        self.assertTrue(result["tick_completed"])
        self.assertEqual(
            result["state"],
            "PAPER_SCHEDULER_TICK_COMPLETED",
        )

    def test_heartbeat_write(self):
        result, root = self.run_case(write_heartbeat=True)
        self.assertTrue(result["heartbeat_written"])
        self.assertTrue((root / "heartbeat.json").exists())

    def test_heartbeat_timeout(self):
        result, _ = self.run_case(
            heartbeat_minutes_ago=16,
        )
        self.assertTrue(result["heartbeat_timeout"])
        self.assertEqual(
            result["state"],
            "PAPER_SCHEDULER_HEARTBEAT_TIMEOUT",
        )

    def test_tick_late(self):
        result, _ = self.run_case(started_minutes_ago=8)
        self.assertEqual(result["state"], "PAPER_SCHEDULER_TICK_LATE")

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
