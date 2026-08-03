import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.operator_control_center_v83_69_72 import (
    run_operator_control_center,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class OperatorControlCenterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = {
            name: self.root / f"{name}.json"
            for name in [
                "certification", "orchestrator", "recovery",
                "retry", "approval", "guard", "runner",
                "policy", "lock", "request", "dashboard", "result",
            ]
        }
        self.ledger = self.root / "ledger.jsonl"
        write_json(self.paths["policy"], {
            "paper_only": True,
            "automatic_control_execution_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_stage(self, **kwargs):
        return run_operator_control_center(
            certification_result_path=self.paths["certification"],
            orchestrator_result_path=self.paths["orchestrator"],
            recovery_result_path=self.paths["recovery"],
            retry_result_path=self.paths["retry"],
            approval_result_path=self.paths["approval"],
            guard_result_path=self.paths["guard"],
            runner_result_path=self.paths["runner"],
            policy_path=self.paths["policy"],
            control_lock_path=self.paths["lock"],
            control_request_path=self.paths["request"],
            control_ledger_path=self.ledger,
            unified_dashboard_path=self.paths["dashboard"],
            result_path=self.paths["result"],
            observed_at_override="2026-08-04T01:00:00+00:00",
            **kwargs,
        )

    def test_dashboard_ready(self):
        result = self.run_stage()
        self.assertEqual(
            result["state"],
            "OPERATOR_CONTROL_CENTER_READY",
        )

    def test_pause_request_written(self):
        result = self.run_stage(action="PAUSE", note="operator test")
        self.assertEqual(result["state"], "OPERATOR_ACTION_PENDING")
        self.assertTrue(result["request_written"])

    def test_disallowed_action_blocked(self):
        result = self.run_stage(action="DELETE_ALL")
        self.assertEqual(result["status"], "BLOCKED")

    def test_duplicate_request_blocked(self):
        write_json(self.paths["lock"], {
            "active": True,
            "request_id": "existing",
        })
        result = self.run_stage(action="RESUME")
        self.assertEqual(result["status"], "BLOCKED")

    def test_attention_detection(self):
        write_json(self.paths["recovery"], {
            "state": "RESTART_RECOVERY_MANUAL_INTERVENTION",
        })
        result = self.run_stage()
        self.assertTrue(result["requires_operator_attention"])

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.paths["policy"].read_text())
        policy["broker_write_enabled"] = True
        write_json(self.paths["policy"], policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
