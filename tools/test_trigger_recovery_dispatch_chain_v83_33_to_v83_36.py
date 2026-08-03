import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.trigger_recovery_dispatch_chain_v83_33_36 import (
    run_trigger_recovery_dispatch_chain,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class TriggerRecoveryDispatchChainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.plan = self.root / "plan.json"
        self.trigger_lock = self.root / "trigger.lock.json"
        self.dispatch_lock = self.root / "dispatch.lock.json"
        self.dispatcher_result = self.root / "dispatcher.json"
        self.recovery_snapshot = self.root / "recovery.json"
        self.completion = self.root / "completion.json"
        self.recovery_lock = self.root / "recovery.lock.json"
        self.ledger = self.root / "ledger.jsonl"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        self.policy = self.root / "policy.json"
        write_json(self.policy, {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "windows_task_install_enabled": False,
            "continuous_loop_enabled": False,
            "automatic_dispatch_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_chain(self, **kwargs):
        return run_trigger_recovery_dispatch_chain(
            trigger_plan_path=self.plan,
            trigger_lock_path=self.trigger_lock,
            dispatch_lock_path=self.dispatch_lock,
            dispatcher_result_path=self.dispatcher_result,
            recovery_snapshot_path=self.recovery_snapshot,
            completion_result_path=self.completion,
            recovery_lock_path=self.recovery_lock,
            chain_ledger_path=self.ledger,
            dashboard_path=self.dashboard,
            result_path=self.result,
            policy_path=self.policy,
            observed_at_override="2026-08-03T19:00:00+00:00",
            **kwargs,
        )

    def valid_plan(self):
        return {
            "trigger_id": "local-trigger-test",
            "trading_date": "2026-08-03",
            "action": "AUTHORIZE_SCHEDULED_SUPERVISED_RUN",
            "target_script": (
                "RUN_V83_17_TO_V83_20_"
                "SCHEDULED_SUPERVISED_RUNNER.ps1"
            ),
            "target_arguments": ["-AuthorizeRun"],
            "paper_only": True,
        }

    def test_wait_trigger_passes(self):
        result = self.run_chain()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["state"], "TRIGGER_CHAIN_WAIT_TRIGGER")

    def test_dispatch_ready(self):
        write_json(self.plan, self.valid_plan())
        write_json(self.trigger_lock, {
            "active": True,
            "trigger_id": "local-trigger-test",
        })
        result = self.run_chain()
        self.assertEqual(result["state"], "TRIGGER_CHAIN_DISPATCH_READY")

    def test_dispatch_running(self):
        write_json(self.dispatch_lock, {
            "active": True,
            "dispatch_id": "dispatch-test",
        })
        result = self.run_chain()
        self.assertEqual(result["state"], "TRIGGER_CHAIN_DISPATCH_RUNNING")

    def test_completion_detected(self):
        write_json(self.completion, {
            "state": "LOCAL_TRIGGER_COMPLETED_BY_DISPATCHER",
        })
        result = self.run_chain()
        self.assertEqual(result["state"], "TRIGGER_CHAIN_COMPLETED")

    def test_recovery_restores_trigger_lock(self):
        write_json(self.plan, self.valid_plan())
        write_json(self.recovery_snapshot, {
            "state": "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED",
            "trigger_id": "local-trigger-test",
        })
        result = self.run_chain(recover_trigger=True)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["trigger_lock_restored"])
        self.assertTrue(json.loads(self.trigger_lock.read_text())["active"])

    def test_duplicate_recovery_blocked(self):
        write_json(self.plan, self.valid_plan())
        write_json(self.recovery_snapshot, {
            "state": "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED",
            "trigger_id": "local-trigger-test",
        })
        write_json(self.recovery_lock, {
            "active": True,
            "recovery_id": "existing",
        })
        result = self.run_chain(recover_trigger=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_policy_fail_closed(self):
        policy = json.loads(self.policy.read_text())
        policy["broker_write_enabled"] = True
        write_json(self.policy, policy)
        result = self.run_chain()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
