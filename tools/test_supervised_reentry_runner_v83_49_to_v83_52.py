import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from paper_runtime.supervised_reentry_runner_v83_49_52 import (
    run_supervised_reentry_runner,
)

def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")

class SupervisedReentryRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1").write_text(
            "Write-Host test", encoding="utf-8"
        )
        self.guard = self.root / "guard.json"
        self.plan = self.root / "plan.json"
        self.exec_lock = self.root / "exec.lock.json"
        self.approval_lock = self.root / "approval.lock.json"
        self.retry_lock = self.root / "retry.lock.json"
        self.policy = self.root / "policy.json"
        self.runner_lock = self.root / "runner.lock.json"
        self.ledger = self.root / "ledger.jsonl"
        self.recovery = self.root / "recovery.json"
        self.completion = self.root / "completion.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        write_json(self.policy, {
            "paper_only": True,
            "timeout_seconds": 10,
            "allowed_return_codes": [0],
            "automatic_execution_enabled": False,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
        })

    def tearDown(self):
        self.temp.cleanup()

    def valid(self):
        write_json(self.guard, {
            "state": "REENTRY_EXECUTION_DRY_RUN_READY",
            "guard_id": "g1",
        })
        write_json(self.plan, {
            "action": "RUN_SUPERVISED_REENTRY_RUNNER",
            "guard_id": "g1",
            "retry_plan_id": "r1",
        })
        write_json(self.exec_lock, {
            "active": True,
            "guard_id": "g1",
            "retry_plan_id": "r1",
        })
        write_json(self.approval_lock, {
            "active": True,
            "approval_id": "a1",
            "retry_plan_id": "r1",
        })
        write_json(self.retry_lock, {
            "active": True,
            "retry_plan_id": "r1",
        })

    def run_stage(self, **kwargs):
        return run_supervised_reentry_runner(
            repository_root=self.root,
            guard_result_path=self.guard,
            execution_plan_path=self.plan,
            execution_lock_path=self.exec_lock,
            approval_lock_path=self.approval_lock,
            retry_lock_path=self.retry_lock,
            policy_path=self.policy,
            runner_lock_path=self.runner_lock,
            audit_ledger_path=self.ledger,
            recovery_snapshot_path=self.recovery,
            completion_result_path=self.completion,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-03T20:00:00+00:00",
            **kwargs,
        )

    def test_wait_plan(self):
        result = self.run_stage()
        self.assertEqual(
            result["state"],
            "SUPERVISED_REENTRY_RUNNER_WAIT_PLAN",
        )

    def test_dry_run(self):
        self.valid()
        result = self.run_stage(execute=True, dry_run=True)
        self.assertEqual(
            result["state"],
            "SUPERVISED_REENTRY_RUNNER_DRY_RUN_COMPLETE",
        )

    def test_success(self):
        self.valid()
        def fake(command, *, cwd, timeout_seconds):
            return subprocess.CompletedProcess(command, 0, "ok", "")
        result = self.run_stage(
            execute=True,
            dry_run=False,
            executor=fake,
        )
        self.assertEqual(
            result["state"],
            "SUPERVISED_REENTRY_RUNNER_COMPLETED",
        )
        self.assertTrue(result["completion_written"])

    def test_timeout(self):
        self.valid()
        def fake(command, *, cwd, timeout_seconds):
            raise subprocess.TimeoutExpired(command, timeout_seconds)
        result = self.run_stage(
            execute=True,
            dry_run=False,
            executor=fake,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["recovery_snapshot_written"])

    def test_duplicate(self):
        self.valid()
        write_json(self.runner_lock, {
            "active": True,
            "execution_id": "existing",
        })
        result = self.run_stage(execute=True)
        self.assertEqual(result["status"], "BLOCKED")

    def test_broker_fail_closed(self):
        policy = json.loads(self.policy.read_text())
        policy["broker_write_enabled"] = True
        write_json(self.policy, policy)
        result = self.run_stage()
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
