import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.trigger_chain_retry_policy_v83_37_40 import (
    run_trigger_chain_retry_policy,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class TriggerChainRetryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.chain = self.root / "chain.json"
        self.plan = self.root / "plan.json"
        self.trigger_lock = self.root / "trigger.lock.json"
        self.recovery = self.root / "recovery.json"
        self.policy = self.root / "policy.json"
        self.retry_lock = self.root / "retry.lock.json"
        self.ledger = self.root / "ledger.jsonl"
        self.retry_plan = self.root / "retry_plan.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        write_json(self.policy, {
            "paper_only": True,
            "max_retry_attempts": 3,
            "base_backoff_seconds": 60,
            "max_backoff_seconds": 600,
            "retry_timeout_failures": True,
            "retryable_return_codes": [2, 5],
            "automatic_retry_execution_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "continuous_loop_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_policy(self, **kwargs):
        return run_trigger_chain_retry_policy(
            chain_result_path=self.chain,
            trigger_plan_path=self.plan,
            trigger_lock_path=self.trigger_lock,
            recovery_snapshot_path=self.recovery,
            policy_path=self.policy,
            retry_lock_path=self.retry_lock,
            retry_ledger_path=self.ledger,
            retry_plan_path=self.retry_plan,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-03T20:00:00+00:00",
            **kwargs,
        )

    def set_retryable_failure(self, return_code=5, timed_out=False):
        write_json(self.plan, {
            "trigger_id": "local-trigger-test",
            "paper_only": True,
        })
        write_json(self.recovery, {
            "state": "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED",
            "trigger_id": "local-trigger-test",
            "return_code": return_code,
            "timed_out": timed_out,
        })

    def test_wait_failure_passes(self):
        result = self.run_policy()
        self.assertEqual(result["state"], "TRIGGER_RETRY_WAIT_FAILURE")
        self.assertEqual(result["status"], "PASS")

    def test_retryable_failure_is_ready(self):
        self.set_retryable_failure()
        result = self.run_policy()
        self.assertEqual(result["state"], "TRIGGER_RETRY_READY")

    def test_plan_retry_writes_backoff_plan(self):
        self.set_retryable_failure()
        result = self.run_policy(plan_retry=True)
        self.assertEqual(result["state"], "TRIGGER_RETRY_PLANNED")
        self.assertTrue(result["retry_plan_written"])
        self.assertEqual(result["attempts_used"], 1)

    def test_duplicate_retry_is_blocked(self):
        self.set_retryable_failure()
        write_json(self.retry_lock, {
            "active": True,
            "retry_plan_id": "existing",
        })
        result = self.run_policy(plan_retry=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_budget_exhaustion_blocks_plan(self):
        self.set_retryable_failure()
        rows = []
        for attempt in range(1, 4):
            rows.append(json.dumps({
                "event": "TRIGGER_RETRY_PLANNED",
                "trigger_id": "local-trigger-test",
                "attempt_number": attempt,
            }))
        self.ledger.write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = self.run_policy(plan_retry=True)
        self.assertEqual(result["state"], "TRIGGER_RETRY_BUDGET_EXHAUSTED")

    def test_nonretryable_code_blocks_plan(self):
        self.set_retryable_failure(return_code=9)
        result = self.run_policy(plan_retry=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.policy.read_text())
        policy["broker_write_enabled"] = True
        write_json(self.policy, policy)
        result = self.run_policy()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
