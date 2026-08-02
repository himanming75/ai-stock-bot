import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.pilot_foundation import (
    ControlledPaperPilotFoundation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "pilot_name": "controlled-paper-pilot",
            "paper_only": True,
            "single_pilot_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "automatic_order_submission_enabled": False,
            "require_zero_open_orders": True,
            "maximum_pilot_days": 20,
        }
        snapshot = {
            "snapshot_type": "ACTUAL_ALPACA_PAPER_READ_ONLY",
            "paper_only": True,
            "read_only": True,
            "observed_at": "2026-08-02T00:00:00+00:00",
            "account": {
                "status": "ACTIVE",
                "account_blocked": False,
                "trading_blocked": False,
            },
            "positions": [],
            "open_orders": [],
        }
        lifecycle = {
            "recovery_required": False,
            "order_status": "filled",
        }
        runtime = {
            "safe_mode_engaged": False,
            "issues": [],
        }
        return policy, snapshot, lifecycle, runtime

    def run_case(self, values, start_pilot=False):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        names = [
            "policy", "snapshot", "lifecycle", "runtime"
        ]
        paths = {
            name: root/f"{name}.json"
            for name in names
        }
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = ControlledPaperPilotFoundation().run(
            policy_path=paths["policy"],
            current_snapshot_path=paths["snapshot"],
            lifecycle_result_path=paths["lifecycle"],
            limited_runtime_result_path=paths["runtime"],
            pilot_registry_path=root/"registry.json",
            pilot_lock_path=root/"lock.json",
            pilot_session_path=root/"session.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            start_pilot=start_pilot,
        )
        return result, root

    def test_preview_ready_without_start(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(
            result["state"],
            "CONTROLLED_PAPER_PILOT_READY",
        )
        self.assertFalse(result["pilot_started"])
        self.assertEqual(result["write_requests_executed"], 0)

    def test_start_creates_lock_session_registry(self):
        result, root = self.run_case(
            self.data(),
            start_pilot=True,
        )
        self.assertEqual(
            result["state"],
            "CONTROLLED_PAPER_PILOT_RUNNING",
        )
        self.assertTrue((root/"lock.json").exists())
        self.assertTrue((root/"session.json").exists())
        self.assertTrue((root/"registry.json").exists())

    def test_open_orders_wait(self):
        values = list(self.data())
        values[1] = dict(values[1])
        values[1]["open_orders"] = [{"id": "open-1"}]
        result, _ = self.run_case(
            tuple(values),
            start_pilot=True,
        )
        self.assertEqual(
            result["state"],
            "WAIT_OPEN_ORDERS_CLEARANCE",
        )
        self.assertFalse(result["pilot_started"])

    def test_recovery_wait(self):
        values = list(self.data())
        values[2] = {
            "recovery_required": True,
            "order_status": "accepted",
        }
        result, _ = self.run_case(
            tuple(values),
            start_pilot=True,
        )
        self.assertEqual(
            result["state"],
            "WAIT_ORDER_RECOVERY",
        )

    def test_emergency_stop_blocks(self):
        values = list(self.data())
        values[3] = {
            "safe_mode_engaged": True,
            "issues": [{
                "code": "EMERGENCY_STOP",
                "blocking": True,
            }],
        }
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_pilot_blocks(self):
        values = self.data()
        result, root = self.run_case(
            values,
            start_pilot=True,
        )
        self.assertTrue(result["pilot_started"])

        second = ControlledPaperPilotFoundation().run(
            policy_path=root/"policy.json",
            current_snapshot_path=root/"snapshot.json",
            lifecycle_result_path=root/"lifecycle.json",
            limited_runtime_result_path=root/"runtime.json",
            pilot_registry_path=root/"registry.json",
            pilot_lock_path=root/"lock.json",
            pilot_session_path=root/"session.json",
            dashboard_state_path=root/"dashboard2.json",
            result_path=root/"result2.json",
            start_pilot=True,
        )
        self.assertEqual(second["status"], "BLOCKED")
        self.assertTrue(second["duplicate_pilot"])


if __name__ == "__main__":
    unittest.main()
