import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.automation_foundation import (
    PaperPilotAutomationFoundation,
)


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def data(self):
        policy = {
            "paper_only": True,
            "single_cycle_only": True,
            "continuous_loop_enabled": False,
            "windows_task_install_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "maximum_steps_per_cycle": 4,
        }
        foundation = {
            "pilot_started": True,
            "pilot_id": "pilot-1",
            "session_id": "session-1",
            "open_order_count": 0,
            "recovery_required": False,
        }
        monitor = {
            "state": "PAPER_SESSION_HEALTHY",
            "health_status": "HEALTHY",
            "controlled_stop_required": False,
        }
        performance = {"state": "PAPER_PERFORMANCE_READY"}
        risk = {
            "state": "PAPER_RISK_HEALTHY",
            "emergency_stop_required": False,
        }
        snapshot = {
            "status": "PASS",
            "snapshot_written": True,
            "safe_mode_engaged": False,
        }
        return policy, foundation, monitor, performance, risk, snapshot

    def run_case(self, values, authorize=False):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        names = ["policy", "foundation", "monitor", "performance", "risk", "snapshot"]
        paths = {name: root/f"{name}.json" for name in names}
        for name, value in zip(names, values):
            self.write(paths[name], value)

        result = PaperPilotAutomationFoundation().run(
            policy_path=paths["policy"],
            foundation_result_path=paths["foundation"],
            session_monitor_result_path=paths["monitor"],
            performance_result_path=paths["performance"],
            risk_result_path=paths["risk"],
            snapshot_collector_result_path=paths["snapshot"],
            cycle_plan_path=root/"plan.json",
            recovery_gate_path=root/"gate.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
            execute_cycle=authorize,
        )
        return result, root

    def test_ready_preview(self):
        result, _ = self.run_case(self.data())
        self.assertEqual(result["state"], "PILOT_AUTOMATION_READY")
        self.assertTrue(result["cycle_ready"])
        self.assertFalse(result["cycle_authorized"])

    def test_authorized_cycle_is_local_only(self):
        result, _ = self.run_case(self.data(), authorize=True)
        self.assertEqual(result["state"], "PILOT_AUTOMATION_CYCLE_AUTHORIZED")
        self.assertTrue(result["cycle_authorized"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)

    def test_wait_before_pilot_start(self):
        values = list(self.data())
        values[1] = {"pilot_started": False}
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "WAIT_PILOT_START")

    def test_open_orders_block_recovery_gate(self):
        values = list(self.data())
        values[1] = dict(values[1])
        values[1]["open_order_count"] = 2
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["state"], "PILOT_AUTOMATION_RECOVERY_BLOCKED")
        self.assertIn("OPEN_ORDERS_PRESENT", result["recovery_reasons"])

    def test_emergency_stop_blocks(self):
        values = list(self.data())
        values[4] = {
            "state": "EMERGENCY_STOP_REQUIRED",
            "emergency_stop_required": True,
        }
        result, _ = self.run_case(tuple(values))
        self.assertIn("EMERGENCY_STOP_REQUIRED", result["recovery_reasons"])

    def test_continuous_loop_policy_blocks(self):
        values = list(self.data())
        values[0] = dict(values[0])
        values[0]["continuous_loop_enabled"] = True
        result, _ = self.run_case(tuple(values))
        self.assertEqual(result["status"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
