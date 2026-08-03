import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from paper_runtime.local_trigger_dispatcher_v83_29_32 import (
    run_local_trigger_dispatcher,
)


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


class LocalTriggerDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1").write_text(
            "Write-Host test", encoding="utf-8"
        )
        self.plan = self.root / "plan.json"
        self.trigger_lock = self.root / "trigger.lock.json"
        self.dispatch_lock = self.root / "dispatch.lock.json"
        self.ledger = self.root / "ledger.jsonl"
        self.recovery = self.root / "recovery.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        self.policy = self.root / "policy.json"
        self.completion = self.root / "completion.json"

        write_json(self.plan, {
            "trigger_id": "local-trigger-test",
            "action": "AUTHORIZE_SCHEDULED_SUPERVISED_RUN",
            "target_script": "RUN_V83_17_TO_V83_20_SCHEDULED_SUPERVISED_RUNNER.ps1",
            "target_arguments": ["-AuthorizeRun"],
            "paper_only": True,
        })
        write_json(self.trigger_lock, {
            "active": True,
            "trigger_id": "local-trigger-test",
            "paper_only": True,
        })
        write_json(self.policy, {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "windows_task_install_enabled": False,
            "continuous_loop_enabled": False,
            "timeout_seconds": 10,
            "allowed_return_codes": [0],
        })

    def tearDown(self):
        self.temp.cleanup()

    def run_dispatcher(self, **kwargs):
        return run_local_trigger_dispatcher(
            repository_root=self.root,
            trigger_plan_path=self.plan,
            trigger_lock_path=self.trigger_lock,
            dispatch_lock_path=self.dispatch_lock,
            dispatch_ledger_path=self.ledger,
            recovery_snapshot_path=self.recovery,
            dashboard_path=self.dashboard,
            result_path=self.result,
            policy_path=self.policy,
            trigger_completion_result_path=self.completion,
            observed_at_override="2026-08-03T18:30:00+00:00",
            **kwargs,
        )

    def test_dry_run_does_not_execute_or_complete_trigger(self):
        result = self.run_dispatcher(dispatch=True, dry_run=True)
        self.assertEqual(result["state"], "LOCAL_TRIGGER_DISPATCH_DRY_RUN_COMPLETE")
        self.assertFalse(result["trigger_lock_completed"])
        self.assertTrue(json.loads(self.trigger_lock.read_text())["active"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)

    def test_success_completes_trigger_lock(self):
        def fake_executor(command, *, cwd, timeout_seconds):
            return subprocess.CompletedProcess(command, 0, "authorized", "")

        result = self.run_dispatcher(
            dispatch=True,
            dry_run=False,
            executor=fake_executor,
        )
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["return_code"], 0)
        self.assertTrue(result["trigger_lock_completed"])
        self.assertFalse(json.loads(self.trigger_lock.read_text())["active"])
        self.assertTrue(self.completion.exists())

    def test_duplicate_dispatch_lock_is_blocked(self):
        write_json(self.dispatch_lock, {
            "active": True,
            "dispatch_id": "existing",
            "trigger_id": "local-trigger-test",
        })
        result = self.run_dispatcher(dispatch=True, dry_run=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["duplicate_dispatch"])

    def test_disallowed_command_is_blocked(self):
        write_json(self.plan, {
            "trigger_id": "local-trigger-test",
            "action": "RUN_ARBITRARY_COMMAND",
            "target_script": "evil.ps1",
            "target_arguments": ["-Force"],
        })
        result = self.run_dispatcher(dispatch=True, dry_run=False)
        self.assertEqual(result["status"], "BLOCKED")
        codes = {item["code"] for item in result["issues"]}
        self.assertIn("DISALLOWED_TRIGGER_ACTION", codes)
        self.assertIn("DISALLOWED_TARGET_SCRIPT", codes)

    def test_nonzero_return_code_writes_recovery_snapshot(self):
        def fake_executor(command, *, cwd, timeout_seconds):
            return subprocess.CompletedProcess(command, 5, "", "failed")

        result = self.run_dispatcher(
            dispatch=True,
            dry_run=False,
            executor=fake_executor,
        )
        self.assertEqual(result["status"], "BLOCKED")
        self.assertTrue(result["recovery_snapshot_written"])
        self.assertTrue(self.recovery.exists())
        self.assertTrue(json.loads(self.trigger_lock.read_text())["active"])

    def test_timeout_writes_recovery_snapshot(self):
        def fake_executor(command, *, cwd, timeout_seconds):
            raise subprocess.TimeoutExpired(command, timeout_seconds)

        result = self.run_dispatcher(
            dispatch=True,
            dry_run=False,
            executor=fake_executor,
        )
        self.assertTrue(result["timed_out"])
        self.assertEqual(
            result["state"],
            "LOCAL_TRIGGER_DISPATCH_RECOVERY_REQUIRED",
        )

    def test_broker_write_policy_is_fail_closed(self):
        policy = json.loads(self.policy.read_text())
        policy["broker_write_enabled"] = True
        write_json(self.policy, policy)
        result = self.run_dispatcher(dispatch=True, dry_run=False)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
