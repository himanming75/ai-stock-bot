import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.paper_autonomous_mode_v83_73_76 import (
    run_paper_autonomous_mode,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class PaperAutonomousModeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = {
            name: self.root / f"{name}.json"
            for name in [
                "control", "certification", "orchestrator", "recovery",
                "policy", "lock", "plan", "dashboard", "result",
            ]
        }
        self.ledger = self.root / "ledger.jsonl"
        write_json(self.paths["policy"], {
            "paper_only": True,
            "continuous_loop_enabled": False,
            "windows_task_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })
        self.seed_ready()

    def tearDown(self):
        self.temp.cleanup()

    def seed_ready(self):
        write_json(self.paths["control"], {
            "state": "OPERATOR_CONTROL_CENTER_READY",
            "requires_operator_attention": False,
        })
        write_json(self.paths["certification"], {
            "state": "PAPER_CYCLE_CERTIFICATION_READY",
        })
        write_json(self.paths["orchestrator"], {
            "state": "FULL_CYCLE_OBSERVING",
        })
        write_json(self.paths["recovery"], {
            "state": "RESTART_RECOVERY_IDLE",
        })

    def run_stage(self, **kwargs):
        return run_paper_autonomous_mode(
            control_center_result_path=self.paths["control"],
            certification_result_path=self.paths["certification"],
            orchestrator_result_path=self.paths["orchestrator"],
            recovery_result_path=self.paths["recovery"],
            policy_path=self.paths["policy"],
            autonomous_lock_path=self.paths["lock"],
            autonomous_plan_path=self.paths["plan"],
            autonomous_ledger_path=self.ledger,
            dashboard_path=self.paths["dashboard"],
            result_path=self.paths["result"],
            observed_at_override="2026-08-04T02:00:00+00:00",
            **kwargs,
        )

    def test_ready(self):
        result = self.run_stage()
        self.assertEqual(result["state"], "PAPER_AUTONOMOUS_CYCLE_READY")

    def test_authorize_single_cycle(self):
        result = self.run_stage(authorize_autonomous_cycle=True)
        self.assertEqual(
            result["state"],
            "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
        )
        self.assertTrue(result["plan_written"])

    def test_duplicate_cycle_blocked(self):
        write_json(self.paths["lock"], {
            "active": True,
            "cycle_id": "existing",
        })
        result = self.run_stage(authorize_autonomous_cycle=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_operator_attention_blocks(self):
        write_json(self.paths["control"], {
            "state": "OPERATOR_CONTROL_CENTER_READY",
            "requires_operator_attention": True,
        })
        result = self.run_stage(authorize_autonomous_cycle=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_complete_active_cycle(self):
        write_json(self.paths["lock"], {
            "active": True,
            "cycle_id": "cycle-1",
        })
        result = self.run_stage(complete_cycle=True)
        self.assertEqual(
            result["state"],
            "PAPER_AUTONOMOUS_CYCLE_COMPLETED",
        )

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.paths["policy"].read_text())
        policy["broker_write_enabled"] = True
        write_json(self.paths["policy"], policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
