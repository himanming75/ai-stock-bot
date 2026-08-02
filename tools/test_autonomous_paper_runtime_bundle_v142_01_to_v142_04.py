from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from autonomous_paper_runtime.autonomous_paper_runtime_bundle import (
    AutonomousPaperRuntimeBundle,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        release = {
            "status": "PASS",
            "state": "PAPER_PRODUCTION_RELEASE_READY",
            "paper_production_release_ready": True,
            "release_id": "paper-release-001",
            "engine_id": "engine-001",
            "safe_mode_engaged": False,
        }
        token = {
            "release_id": "paper-release-001",
            "engine_id": "engine-001",
            "paper_production_release_ready": True,
            "live_trading_enabled": False,
            "actual_submission_allowed": False,
            "broker_network_allowed": False,
        }
        policy = {
            "session_id": "session-001",
            "interval_seconds": 30,
            "max_ticks_per_run": 1,
            "unbounded_loop_enabled": False,
            "live_trading_enabled": False,
            "actual_submission_allowed": False,
            "broker_network_allowed": False,
        }
        watchdog = {
            "heartbeat_age_seconds": 5,
            "maximum_heartbeat_age_seconds": 120,
            "runtime_process_count": 1,
            "disk_free_mb": 10000,
            "minimum_disk_free_mb": 1024,
            "filesystem_writable": True,
            "system_clock_synchronized": True,
        }
        emergency = {
            "engaged": False,
            "reason": "",
        }
        return release, token, policy, watchdog, emergency

    def run_case(self, values, lock_active=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = ["release", "token", "policy", "watchdog", "emergency"]
        paths = {name: root/f"{name}.json" for name in names}

        for name, value in zip(names, values):
            if value is not None:
                self.write(paths[name], value)

        lock = root/"lock.json"
        if lock_active:
            self.write(lock, {"released": False})

        result = AutonomousPaperRuntimeBundle().run(
            release_result_path=paths["release"],
            release_token_path=paths["token"],
            runtime_policy_path=paths["policy"],
            watchdog_snapshot_path=paths["watchdog"],
            emergency_stop_path=paths["emergency"],
            runtime_lock_path=lock,
            heartbeat_path=root/"heartbeat.json",
            tick_result_path=root/"tick.json",
            runtime_token_path=root/"runtime_token.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_wait_before_release(self):
        values = list(self.data())
        values[0] = {
            "status": "PASS",
            "state": "WAIT_OPERATIONAL_STABILITY",
            "paper_production_release_ready": False,
            "safe_mode_engaged": False,
        }
        result, _ = self.run_case(values)
        self.assertEqual(result["state"], "WAIT_PAPER_PRODUCTION_RELEASE")

    def test_single_tick_runtime_ready(self):
        result, root = self.run_case(self.data())
        self.assertEqual(result["state"], "AUTONOMOUS_PAPER_RUNTIME_READY")
        self.assertTrue(result["runtime_tick_written"])
        self.assertFalse(result["continuous_loop_enabled"])
        self.assertTrue((root/"runtime_token.json").exists())

    def test_emergency_stop_blocks(self):
        values = list(self.data())
        values[4] = {"engaged": True, "reason": "manual stop"}
        result, _ = self.run_case(values)
        self.assertEqual(result["state"], "AUTONOMOUS_RUNTIME_EMERGENCY_STOP")

    def test_unbounded_loop_blocks(self):
        values = list(self.data())
        values[2] = dict(values[2])
        values[2]["unbounded_loop_enabled"] = True
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_stale_watchdog_blocks(self):
        values = list(self.data())
        values[3] = dict(values[3])
        values[3]["heartbeat_age_seconds"] = 999
        result, _ = self.run_case(values)
        self.assertEqual(result["status"], "BLOCKED")

    def test_active_lock_blocks(self):
        result, _ = self.run_case(self.data(), lock_active=True)
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
