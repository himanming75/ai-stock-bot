import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.end_to_end_paper_cycle_certification_v83_65_68 import (
    run_end_to_end_paper_cycle_certification,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class EndToEndPaperCycleCertificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.paths = {
            name: self.root / f"{name}.json"
            for name in [
                "dispatcher", "chain", "retry", "runner",
                "completion", "recovery", "orchestrator",
                "policy", "overrides", "certificate",
                "dashboard", "result",
            ]
        }
        self.ledger = self.root / "ledger.jsonl"
        write_json(self.paths["policy"], {
            "paper_only": True,
            "automatic_execution_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })
        write_json(self.paths["overrides"], {
            "DUPLICATE_TRIGGER_BLOCKED": True,
            "DUPLICATE_DISPATCH_BLOCKED": True,
            "RUNNER_TIMEOUT_RECOVERY": True,
            "RETRY_SUCCESS": True,
            "RETRY_BUDGET_EXHAUSTED": True,
            "RESTART_RECOVERY": True,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_stage(self, **kwargs):
        return run_end_to_end_paper_cycle_certification(
            dispatcher_result_path=self.paths["dispatcher"],
            chain_result_path=self.paths["chain"],
            retry_result_path=self.paths["retry"],
            runner_result_path=self.paths["runner"],
            completion_result_path=self.paths["completion"],
            recovery_result_path=self.paths["recovery"],
            orchestrator_result_path=self.paths["orchestrator"],
            policy_path=self.paths["policy"],
            scenario_overrides_path=self.paths["overrides"],
            ledger_path=self.ledger,
            certificate_path=self.paths["certificate"],
            dashboard_path=self.paths["dashboard"],
            result_path=self.paths["result"],
            observed_at_override="2026-08-03T23:00:00+00:00",
            **kwargs,
        )

    def seed_success_and_wait(self):
        write_json(self.paths["dispatcher"], {
            "state": "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER",
        })
        write_json(self.paths["chain"], {
            "state": "TRIGGER_CHAIN_COMPLETED",
        })
        write_json(self.paths["recovery"], {
            "state": "RESTART_RECOVERY_IDLE",
        })

    def test_ready_when_all_scenarios_pass(self):
        self.seed_success_and_wait()
        result = self.run_stage()
        self.assertEqual(
            result["state"],
            "PAPER_CYCLE_CERTIFICATION_READY",
        )

    def test_certify_writes_certificate(self):
        self.seed_success_and_wait()
        result = self.run_stage(certify=True)
        self.assertEqual(
            result["state"],
            "END_TO_END_PAPER_AUTOMATION_CERTIFIED",
        )
        self.assertTrue(result["certificate_written"])

    def test_missing_normal_success_blocks(self):
        write_json(self.paths["dispatcher"], {
            "state": "LOCAL_TRIGGER_DISPATCH_WAIT_TRIGGER",
        })
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")

    def test_missing_wait_trigger_blocks(self):
        write_json(self.paths["chain"], {
            "state": "TRIGGER_CHAIN_COMPLETED",
        })
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")

    def test_failed_override_blocks(self):
        self.seed_success_and_wait()
        overrides = json.loads(self.paths["overrides"].read_text())
        overrides["DUPLICATE_DISPATCH_BLOCKED"] = False
        write_json(self.paths["overrides"], overrides)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_policy_fail_closed(self):
        self.seed_success_and_wait()
        policy = json.loads(self.paths["policy"].read_text())
        policy["broker_write_enabled"] = True
        write_json(self.paths["policy"], policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
