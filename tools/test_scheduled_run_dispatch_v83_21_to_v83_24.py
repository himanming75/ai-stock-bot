
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from paper_runtime.scheduled_run_dispatch_v83_21_24 import (
    run_scheduled_dispatch,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        execute=False,
        dry_run=False,
        clear=False,
        valid_authorization=True,
        active_schedule=True,
        active_dispatch=False,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "authorization.json", {
            "authorization_id": (
                "scheduled-auth-test"
                if valid_authorization else ""
            ),
            "execute_supervised_runner": valid_authorization,
        })
        self.write(root / "schedule.lock.json", {
            "active": active_schedule,
            "authorization_id": "scheduled-auth-test",
        })
        self.write(root / "supervised.json", {
            "status": "PASS",
            "state": "SUPERVISED_RUNNER_COMPLETE",
            "runner_completed": True,
            "runner_id": "runner-test",
        })
        self.write(root / "policy.json", {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "windows_task_install_enabled": False,
            "continuous_loop_enabled": False,
            "max_dispatches_per_authorization": 1,
            "timeout_seconds": 10,
        })
        if active_dispatch:
            self.write(root / "dispatch.lock.json", {
                "active": True,
                "authorization_id": "scheduled-auth-test",
            })

        result = run_scheduled_dispatch(
            repository_root=root,
            schedule_authorization_path=root / "authorization.json",
            schedule_lock_path=root / "schedule.lock.json",
            supervised_result_path=root / "supervised.json",
            policy_path=root / "policy.json",
            dispatch_lock_path=root / "dispatch.lock.json",
            dispatch_ledger_path=root / "ledger.jsonl",
            execution_report_path=root / "report.json",
            recovery_path=root / "recovery.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_dispatch=execute,
            dry_run=dry_run,
            clear_dispatch_lock=clear,
        )
        return result, root

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "SCHEDULED_DISPATCH_READY")

    def test_wait_authorization(self):
        result, _ = self.run_case(
            valid_authorization=False,
            active_schedule=False,
        )
        self.assertEqual(
            result["state"],
            "WAIT_SCHEDULED_RUN_AUTHORIZATION",
        )

    def test_dry_run(self):
        result, root = self.run_case(
            execute=True,
            dry_run=True,
        )
        self.assertEqual(
            result["state"],
            "SCHEDULED_DISPATCH_DRY_RUN_COMPLETE",
        )
        self.assertTrue((root / "report.json").exists())

    def test_duplicate_dispatch(self):
        result, _ = self.run_case(
            execute=True,
            active_dispatch=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    @patch("paper_runtime.scheduled_run_dispatch_v83_21_24.subprocess.run")
    def test_successful_dispatch(self, mocked_run):
        mocked_run.return_value = Mock(
            returncode=0,
            stdout="PASS",
            stderr="",
        )
        result, root = self.run_case(execute=True)
        self.assertTrue(result["dispatch_succeeded"])
        self.assertTrue(result["schedule_lock_completed"])
        lock = json.loads(
            (root / "schedule.lock.json").read_text(encoding="utf-8")
        )
        self.assertFalse(lock["active"])

    @patch("paper_runtime.scheduled_run_dispatch_v83_21_24.subprocess.run")
    def test_nonzero_dispatch(self, mocked_run):
        mocked_run.return_value = Mock(
            returncode=2,
            stdout="",
            stderr="failed",
        )
        result, _ = self.run_case(execute=True)
        self.assertEqual(result["state"], "SCHEDULED_DISPATCH_FAILED")

    @patch("paper_runtime.scheduled_run_dispatch_v83_21_24.subprocess.run")
    def test_result_verification_failure(self, mocked_run):
        mocked_run.return_value = Mock(
            returncode=0,
            stdout="PASS",
            stderr="",
        )
        result, root = self.run_case(execute=False)
        self.write(root / "supervised.json", {
            "status": "PASS",
            "state": "SUPERVISED_RUNNER_READY",
            "runner_completed": False,
        })
        result = run_scheduled_dispatch(
            repository_root=root,
            schedule_authorization_path=root / "authorization.json",
            schedule_lock_path=root / "schedule.lock.json",
            supervised_result_path=root / "supervised.json",
            policy_path=root / "policy.json",
            dispatch_lock_path=root / "dispatch.lock.json",
            dispatch_ledger_path=root / "ledger.jsonl",
            execution_report_path=root / "report.json",
            recovery_path=root / "recovery.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_dispatch=True,
        )
        self.assertFalse(result["dispatch_succeeded"])

    def test_clear_lock(self):
        result, _ = self.run_case(
            clear=True,
            active_dispatch=True,
        )
        self.assertEqual(
            result["state"],
            "SCHEDULED_DISPATCH_LOCK_CLEARED",
        )

    def test_dashboard_written(self):
        result, root = self.run_case()
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_safety_contract(self):
        result, _ = self.run_case(
            execute=True,
            dry_run=True,
        )
        self.assertEqual(result["max_dispatches_per_authorization"], 1)
        self.assertFalse(result["windows_task_install_enabled"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
