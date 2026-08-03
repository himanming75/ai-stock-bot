
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.controlled_automation_cycle_v83_09_12 import (
    run_controlled_automation_cycle,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        ready=True,
        execute=False,
        resume=False,
        clear=False,
        active_lock=False,
        dispatcher_success=True,
        callbacks=None,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "orchestrator.json", {
            "state": (
                "ORCHESTRATOR_ACTION_READY"
                if ready else "AUTOMATED_ORCHESTRATOR_WAIT"
            ),
            "recommended_action": (
                "START_PAPER_SESSION" if ready else "WAIT"
            ),
            "action_ready": ready,
        })
        self.write(root / "dispatcher.json", {
            "state": (
                "LOCAL_ACTION_DISPATCH_COMPLETE"
                if dispatcher_success else "LOCAL_ACTION_DISPATCH_FAILED"
            ),
            "dispatch_succeeded": dispatcher_success,
            "return_code": 0 if dispatcher_success else 2,
        })
        self.write(root / "plan.json", {
            "action_id": "action-test",
            "action": "START_PAPER_SESSION",
        })
        self.write(root / "action.lock.json", {
            "active": True,
            "action_id": "action-test",
            "action": "START_PAPER_SESSION",
        })
        self.write(root / "policy.json", {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "continuous_loop_enabled": False,
            "broker_command_execution_enabled": False,
            "max_actions_per_cycle": 1,
        })

        if active_lock:
            self.write(root / "cycle.lock.json", {
                "active": True,
                "completed": False,
                "cycle_id": "cycle-existing",
                "recommended_action": "START_PAPER_SESSION",
                "last_completed_stage": "ORCHESTRATOR_AUTHORIZE",
                "started_at": "2026-08-03T00:00:00+00:00",
            })

        result = run_controlled_automation_cycle(
            orchestrator_result_path=root / "orchestrator.json",
            dispatcher_result_path=root / "dispatcher.json",
            orchestrator_action_plan_path=root / "plan.json",
            orchestrator_action_lock_path=root / "action.lock.json",
            policy_path=root / "policy.json",
            cycle_lock_path=root / "cycle.lock.json",
            cycle_ledger_path=root / "ledger.jsonl",
            cycle_report_path=root / "report.json",
            recovery_path=root / "recovery.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_cycle=execute,
            resume_cycle=resume,
            clear_cycle_lock=clear,
            stage_callbacks=callbacks,
        )
        return result, root

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "CONTROLLED_CYCLE_READY")

    def test_wait_gates(self):
        result, _ = self.run_case(ready=False)
        self.assertEqual(
            result["state"],
            "CONTROLLED_CYCLE_WAIT_GATES",
        )

    def test_complete_cycle(self):
        result, root = self.run_case(execute=True)
        self.assertTrue(result["cycle_completed"])
        self.assertEqual(result["stage_count"], 4)
        self.assertTrue((root / "ledger.jsonl").exists())
        self.assertTrue((root / "report.json").exists())

    def test_duplicate_cycle_blocked(self):
        result, _ = self.run_case(
            execute=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_dispatcher_failure_recovery(self):
        result, root = self.run_case(
            execute=True,
            dispatcher_success=False,
        )
        self.assertEqual(
            result["state"],
            "CONTROLLED_CYCLE_RECOVERY_REQUIRED",
        )
        self.assertTrue((root / "recovery.json").exists())

    def test_callback_failure_recovery(self):
        callbacks = {
            "RUNTIME_REEVALUATE": lambda: {"status": "FAIL"}
        }
        result, _ = self.run_case(
            execute=True,
            callbacks=callbacks,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_resume_cycle(self):
        result, _ = self.run_case(
            resume=True,
            active_lock=True,
        )
        self.assertTrue(result["cycle_recovered"])
        self.assertTrue(result["cycle_completed"])

    def test_clear_lock(self):
        result, _ = self.run_case(
            clear=True,
            active_lock=True,
        )
        self.assertEqual(
            result["state"],
            "CONTROLLED_CYCLE_LOCK_CLEARED",
        )

    def test_dashboard_written(self):
        result, root = self.run_case()
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_safety_contract(self):
        result, _ = self.run_case(execute=True)
        self.assertEqual(result["max_actions_per_cycle"], 1)
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertFalse(result["continuous_loop_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
