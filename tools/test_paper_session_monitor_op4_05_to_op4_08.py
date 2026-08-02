import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.session_monitor import (
    PaperPilotSessionMonitor,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "paper_only": True,
            "read_only_monitor": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "heartbeat_interval_seconds": 10,
            "heartbeat_warning_seconds": 30,
            "session_timeout_seconds": 60,
        }
        foundation = {
            "pilot_started": True,
            "pilot_id": "pilot-1",
            "session_id": "session-1",
            "duplicate_pilot": False,
            "emergency_stop_engaged": False,
        }
        lock = {
            "pilot_id": "pilot-1",
            "session_id": "session-1",
            "active": True,
        }
        session = {
            "pilot_id": "pilot-1",
            "session_id": "session-1",
            "status": "RUNNING",
        }
        return policy, foundation, lock, session

    def run_case(
        self,
        values,
        *,
        heartbeat=False,
        stop=False,
        observed_at="2026-08-02T08:00:00+00:00",
        heartbeat_payload=None,
    ):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "foundation", "lock", "session"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)
        if heartbeat_payload is not None:
            self.write(root/"heartbeat.json", heartbeat_payload)

        result = PaperPilotSessionMonitor().run(
            policy_path=paths["policy"],
            foundation_result_path=paths["foundation"],
            pilot_lock_path=paths["lock"],
            pilot_session_path=paths["session"],
            heartbeat_path=root/"heartbeat.json",
            health_path=root/"health.json",
            controlled_stop_path=root/"stop.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            write_heartbeat=heartbeat,
            request_controlled_stop=stop,
            observed_at=observed_at,
        )
        return result, root

    def test_heartbeat_written(self):
        result, root = self.run_case(
            self.data(), heartbeat=True
        )
        self.assertTrue(result["heartbeat_written"])
        self.assertEqual(result["health_status"], "HEALTHY")
        self.assertTrue((root/"heartbeat.json").exists())

    def test_timeout_detected(self):
        result, _ = self.run_case(
            self.data(),
            heartbeat_payload={
                "observed_at": "2026-08-02T07:58:00+00:00",
                "tick_number": 1,
            },
        )
        self.assertTrue(result["timeout_detected"])
        self.assertTrue(result["controlled_stop_required"])

    def test_manual_controlled_stop(self):
        result, root = self.run_case(
            self.data(),
            heartbeat=True,
            stop=True,
        )
        self.assertTrue(result["controlled_stop_written"])
        self.assertIn(
            "MANUAL_CONTROLLED_STOP",
            result["stop_reasons"],
        )
        self.assertTrue((root/"stop.json").exists())

    def test_wait_before_pilot_start(self):
        values = list(self.data())
        values[1] = {
            "pilot_started": False,
            "pilot_id": "",
            "session_id": "",
        }
        values[2] = {}
        values[3] = {}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PILOT_START")
        self.assertFalse(result["heartbeat_written"])

    def test_identity_mismatch_blocks(self):
        values = list(self.data())
        values[2] = dict(values[2])
        values[2]["session_id"] = "wrong"
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")

    def test_read_only_contract(self):
        result, _ = self.run_case(
            self.data(), heartbeat=True
        )
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
