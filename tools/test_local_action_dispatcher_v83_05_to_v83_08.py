
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock

from paper_runtime.local_action_dispatcher_v83_05_08 import (
    ALLOWED_ACTIONS,
    run_local_action_dispatcher,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        action="START_PAPER_SESSION",
        execute=False,
        dry_run=False,
        clear=False,
        active_dispatch=False,
        active_orchestrator=True,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "plan.json", {
            "action_id": "action-test",
            "action": action,
        })
        self.write(root / "orchestrator.lock.json", {
            "active": active_orchestrator,
            "action_id": "action-test",
            "action": action,
        })
        self.write(root / "policy.json", {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "continuous_loop_enabled": False,
            "broker_command_execution_enabled": False,
            "timeout_seconds": 10,
        })

        if active_dispatch:
            self.write(root / "dispatch.lock.json", {
                "active": True,
                "action_id": "action-test",
            })

        result = run_local_action_dispatcher(
            repository_root=root,
            action_plan_path=root / "plan.json",
            action_lock_path=root / "orchestrator.lock.json",
            policy_path=root / "policy.json",
            dispatch_lock_path=root / "dispatch.lock.json",
            dispatch_ledger_path=root / "ledger.jsonl",
            execution_report_path=root / "report.json",
            recovery_path=root / "recovery.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_action=execute,
            dry_run=dry_run,
            clear_dispatch_lock=clear,
        )
        return result, root

    def test_allowlist_contains_core_actions(self):
        self.assertIn("START_PAPER_SESSION", ALLOWED_ACTIONS)
        self.assertIn("EXECUTE_INTRADAY_LOOP", ALLOWED_ACTIONS)
        self.assertIn("CERTIFY_TRADING_DAY", ALLOWED_ACTIONS)

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "LOCAL_ACTION_READY")

    def test_wait_authorization(self):
        result, _ = self.run_case(active_orchestrator=False)
        self.assertEqual(
            result["state"],
            "WAIT_AUTHORIZED_ORCHESTRATOR_ACTION",
        )

    def test_unknown_action_blocked(self):
        result, _ = self.run_case(action="BROKER_BUY_ORDER")
        self.assertEqual(result["status"], "BLOCKED")

    def test_dry_run(self):
        result, root = self.run_case(
            execute=True,
            dry_run=True,
        )
        self.assertEqual(
            result["state"],
            "LOCAL_ACTION_DRY_RUN_COMPLETE",
        )
        self.assertTrue((root / "report.json").exists())
        self.assertFalse(result["dispatch_started"])

    def test_duplicate_dispatch_blocked(self):
        result, _ = self.run_case(
            execute=True,
            active_dispatch=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    @patch("paper_runtime.local_action_dispatcher_v83_05_08.subprocess.run")
    def test_successful_dispatch(self, mocked_run):
        mocked_run.return_value = Mock(
            returncode=0,
            stdout="PASS",
            stderr="",
        )
        result, root = self.run_case(execute=True)
        self.assertTrue(result["dispatch_succeeded"])
        self.assertTrue(result["orchestrator_lock_completed"])
        lock = json.loads(
            (root / "orchestrator.lock.json").read_text(encoding="utf-8")
        )
        self.assertFalse(lock["active"])

    @patch("paper_runtime.local_action_dispatcher_v83_05_08.subprocess.run")
    def test_failed_dispatch(self, mocked_run):
        mocked_run.return_value = Mock(
            returncode=2,
            stdout="",
            stderr="failed",
        )
        result, root = self.run_case(execute=True)
        self.assertEqual(
            result["state"],
            "LOCAL_ACTION_DISPATCH_FAILED",
        )
        self.assertTrue((root / "recovery.json").exists())

    def test_clear_lock(self):
        result, _ = self.run_case(clear=True, active_dispatch=True)
        self.assertEqual(
            result["state"],
            "LOCAL_DISPATCH_LOCK_CLEARED",
        )

    def test_read_only_broker_contract(self):
        result, _ = self.run_case(
            execute=True,
            dry_run=True,
        )
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertFalse(result["broker_command_execution_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
