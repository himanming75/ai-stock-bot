import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.full_schedule_completion_orchestrator_v83_57_60 import (
    run_full_schedule_completion_orchestrator,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class FullScheduleCompletionOrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = {
            name: self.root / f"{name}.json"
            for name in [
                "schedule", "dispatcher", "chain", "retry",
                "approval", "guard", "runner", "completion",
                "policy", "lock", "certificate", "dashboard", "result",
            ]
        }
        self.ledger = self.root / "ledger.jsonl"
        write_json(self.paths["policy"], {
            "paper_only": True,
            "automatic_stage_execution_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_stage(self, **kwargs):
        return run_full_schedule_completion_orchestrator(
            schedule_result_path=self.paths["schedule"],
            dispatcher_result_path=self.paths["dispatcher"],
            chain_result_path=self.paths["chain"],
            retry_result_path=self.paths["retry"],
            approval_result_path=self.paths["approval"],
            guard_result_path=self.paths["guard"],
            runner_result_path=self.paths["runner"],
            retry_completion_result_path=self.paths["completion"],
            policy_path=self.paths["policy"],
            cycle_lock_path=self.paths["lock"],
            ledger_path=self.ledger,
            certificate_path=self.paths["certificate"],
            dashboard_path=self.paths["dashboard"],
            result_path=self.paths["result"],
            observed_at_override="2026-08-03T22:00:00+00:00",
            **kwargs,
        )

    def test_wait_schedule(self):
        result = self.run_stage()
        self.assertEqual(result["state"], "FULL_CYCLE_WAIT_SCHEDULE")

    def test_start_cycle(self):
        result = self.run_stage(start_cycle=True)
        self.assertTrue(result["cycle_started"])
        self.assertEqual(result["status"], "PASS")

    def test_duplicate_cycle_blocked(self):
        write_json(self.paths["lock"], {
            "active": True,
            "cycle_id": "existing",
        })
        result = self.run_stage(start_cycle=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_completed_cycle_finalizes(self):
        write_json(self.paths["completion"], {
            "state": "RETRY_CYCLE_COMPLETED",
            "trigger_id": "trigger-1",
        })
        write_json(self.paths["lock"], {
            "active": True,
            "cycle_id": "cycle-1",
        })
        result = self.run_stage(finalize_cycle=True)
        self.assertEqual(result["state"], "FULL_CYCLE_COMPLETED")
        self.assertTrue(result["certificate_written"])

    def test_manual_intervention_state(self):
        write_json(self.paths["completion"], {
            "state": "RETRY_CYCLE_BUDGET_EXHAUSTED",
        })
        result = self.run_stage()
        self.assertTrue(result["manual_intervention_required"])

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.paths["policy"].read_text())
        policy["broker_write_enabled"] = True
        write_json(self.paths["policy"], policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
