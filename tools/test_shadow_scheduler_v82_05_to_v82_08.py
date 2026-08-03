
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from shadow_runtime.scheduler_v82_05_08 import run_shadow_scheduler


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        cycle_ready=True,
        write_heartbeat=False,
        authorize=False,
        active_lock=False,
        last_cycle_minutes_ago=20,
        heartbeat_minutes_ago=None,
        max_lateness=10,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        now = datetime(2026, 8, 3, 16, 0, tzinfo=timezone.utc)

        self.write(root / "policy.json", {
            "shadow_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "windows_task_install_enabled": False,
            "interval_minutes": 15,
            "heartbeat_timeout_minutes": 30,
            "maximum_lateness_minutes": max_lateness,
        })
        self.write(root / "cycle.json", {
            "state": (
                "AUTONOMOUS_SHADOW_CYCLE_READY"
                if cycle_ready
                else "WAIT_SHADOW_FOUNDATION"
            ),
            "observed_at": (
                now - timedelta(minutes=last_cycle_minutes_ago)
            ).isoformat(),
        })
        if heartbeat_minutes_ago is not None:
            self.write(root / "heartbeat.json", {
                "last_heartbeat_at": (
                    now - timedelta(minutes=heartbeat_minutes_ago)
                ).isoformat()
            })
        if active_lock:
            self.write(root / "lock.json", {
                "active": True,
                "scheduler_id": "existing",
            })

        result = run_shadow_scheduler(
            cycle_result_path=root / "cycle.json",
            policy_path=root / "policy.json",
            heartbeat_path=root / "heartbeat.json",
            scheduler_lock_path=root / "lock.json",
            scheduler_ledger_path=root / "ledger.jsonl",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            write_heartbeat=write_heartbeat,
            authorize_next_cycle=authorize,
            now=now,
        )
        return result, root

    def test_wait_cycle_foundation(self):
        result, _ = self.run_case(cycle_ready=False)
        self.assertEqual(result["state"], "WAIT_AUTONOMOUS_SHADOW_CYCLE")

    def test_write_heartbeat(self):
        result, root = self.run_case(write_heartbeat=True)
        self.assertTrue(result["heartbeat_written"])
        self.assertTrue((root / "heartbeat.json").exists())

    def test_wait_interval(self):
        result, _ = self.run_case(last_cycle_minutes_ago=5)
        self.assertEqual(result["state"], "SHADOW_SCHEDULER_WAIT_INTERVAL")

    def test_cycle_due(self):
        result, _ = self.run_case(last_cycle_minutes_ago=20)
        self.assertEqual(result["state"], "SHADOW_SCHEDULER_CYCLE_DUE")

    def test_authorize_cycle(self):
        result, root = self.run_case(
            last_cycle_minutes_ago=20,
            authorize=True,
        )
        self.assertTrue(result["next_cycle_authorized"])
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_scheduler_blocked(self):
        result, _ = self.run_case(
            last_cycle_minutes_ago=20,
            authorize=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_heartbeat_timeout(self):
        result, _ = self.run_case(heartbeat_minutes_ago=31)
        self.assertTrue(result["heartbeat_timeout"])
        self.assertEqual(
            result["state"],
            "SHADOW_SCHEDULER_HEARTBEAT_TIMEOUT",
        )

    def test_cycle_late(self):
        result, _ = self.run_case(
            last_cycle_minutes_ago=40,
            max_lateness=10,
        )
        self.assertEqual(
            result["state"],
            "SHADOW_SCHEDULER_CYCLE_LATE",
        )

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
