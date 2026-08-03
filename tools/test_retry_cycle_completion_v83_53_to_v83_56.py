import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.retry_cycle_completion_v83_53_56 import (
    run_retry_cycle_completion,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class RetryCycleCompletionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runner = self.root / "runner.json"
        self.completion = self.root / "completion.json"
        self.recovery = self.root / "runner_recovery.json"
        self.retry_policy = self.root / "retry_policy.json"
        self.retry_plan = self.root / "retry_plan.json"
        self.original_recovery = self.root / "original_recovery.json"
        self.trigger_plan = self.root / "trigger_plan.json"
        self.policy = self.root / "policy.json"
        self.ledger = self.root / "ledger.jsonl"
        self.certificate = self.root / "certificate.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        write_json(self.policy, {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })
        write_json(self.retry_policy, {
            "attempts_used": 1,
            "max_retry_attempts": 3,
        })
        write_json(self.retry_plan, {
            "retry_plan_id": "retry-1",
            "trigger_id": "trigger-1",
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_stage(self, **kwargs):
        return run_retry_cycle_completion(
            runner_result_path=self.runner,
            runner_completion_path=self.completion,
            runner_recovery_path=self.recovery,
            retry_policy_result_path=self.retry_policy,
            retry_plan_path=self.retry_plan,
            original_recovery_path=self.original_recovery,
            trigger_plan_path=self.trigger_plan,
            policy_path=self.policy,
            completion_ledger_path=self.ledger,
            certificate_path=self.certificate,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-03T21:00:00+00:00",
            **kwargs,
        )

    def test_wait_runner_result(self):
        result = self.run_stage()
        self.assertEqual(
            result["state"],
            "RETRY_CYCLE_WAIT_RUNNER_RESULT",
        )

    def test_success_completion(self):
        write_json(self.runner, {
            "state": "SUPERVISED_REENTRY_RUNNER_COMPLETED",
            "execution_id": "execution-1",
            "return_code": 0,
        })
        result = self.run_stage(finalize=True)
        self.assertEqual(result["state"], "RETRY_CYCLE_COMPLETED")
        self.assertTrue(result["certificate_written"])

    def test_failure_retry_available(self):
        write_json(self.runner, {
            "state": "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED",
            "execution_id": "execution-1",
        })
        result = self.run_stage(finalize=True)
        self.assertEqual(
            result["state"],
            "RETRY_CYCLE_FAILED_RETRY_AVAILABLE",
        )

    def test_budget_exhaustion(self):
        write_json(self.retry_policy, {
            "attempts_used": 3,
            "max_retry_attempts": 3,
        })
        write_json(self.runner, {
            "state": "SUPERVISED_REENTRY_RUNNER_RECOVERY_REQUIRED",
        })
        result = self.run_stage(finalize=True)
        self.assertEqual(
            result["state"],
            "RETRY_CYCLE_BUDGET_EXHAUSTED",
        )
        self.assertTrue(result["manual_intervention_required"])

    def test_wait_state_cannot_finalize(self):
        result = self.run_stage(finalize=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.policy.read_text())
        policy["broker_write_enabled"] = True
        write_json(self.policy, policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
