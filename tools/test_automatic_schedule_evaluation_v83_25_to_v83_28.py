
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.automatic_schedule_evaluation_v83_25_28 import (
    run_automatic_schedule_evaluation,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        create=False,
        complete=False,
        clear=False,
        market_open=True,
        session_active=False,
        risk_clear=True,
        supervised_ready=True,
        schedule_idle=True,
        active_lock=False,
        observed_at="2026-08-03T15:00:00+00:00",
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "session.json", {
            "trading_day": True,
            "market_open": market_open,
            "market_closed": not market_open,
            "session_active": session_active,
        })
        self.write(root / "risk.json", {
            "state": (
                "SHADOW_RISK_CLEAR"
                if risk_clear
                else "SHADOW_RISK_KILL_SWITCH_ACTIVE"
            )
        })
        self.write(root / "supervised.json", {
            "state": (
                "SUPERVISED_RUNNER_READY"
                if supervised_ready
                else "SUPERVISED_RUNNER_SAFE_MODE"
            )
        })
        self.write(root / "schedule.json", {
            "state": (
                "SCHEDULED_RUN_WAIT_GATES"
                if schedule_idle
                else "SCHEDULED_RUN_IN_PROGRESS"
            )
        })
        self.write(root / "policy.json", {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "windows_task_install_enabled": False,
            "local_trigger_execution_enabled": False,
            "continuous_loop_enabled": False,
            "window_start_utc": "13:30",
            "window_end_utc": "20:00",
            "max_triggers_per_day": 3,
            "minimum_trigger_interval_seconds": 300,
        })
        if active_lock:
            self.write(root / "lock.json", {
                "active": True,
                "trigger_id": "trigger-existing",
            })

        result = run_automatic_schedule_evaluation(
            session_result_path=root / "session.json",
            risk_result_path=root / "risk.json",
            supervised_result_path=root / "supervised.json",
            schedule_result_path=root / "schedule.json",
            policy_path=root / "policy.json",
            trigger_lock_path=root / "lock.json",
            trigger_ledger_path=root / "ledger.jsonl",
            trigger_plan_path=root / "plan.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            create_trigger=create,
            complete_trigger=complete,
            clear_trigger_lock=clear,
            observed_at_override=observed_at,
        )
        return result, root

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "LOCAL_TRIGGER_READY")

    def test_market_gate(self):
        result, _ = self.run_case(market_open=False)
        self.assertIn("MARKET_NOT_OPEN", result["trigger_reasons"])

    def test_active_session_gate(self):
        result, _ = self.run_case(session_active=True)
        self.assertIn("SESSION_ALREADY_ACTIVE", result["trigger_reasons"])

    def test_risk_gate(self):
        result, _ = self.run_case(risk_clear=False)
        self.assertIn("RISK_NOT_CLEAR", result["trigger_reasons"])

    def test_schedule_busy_gate(self):
        result, _ = self.run_case(schedule_idle=False)
        self.assertIn(
            "SCHEDULE_PIPELINE_NOT_IDLE",
            result["trigger_reasons"],
        )

    def test_create_trigger(self):
        result, root = self.run_case(create=True)
        self.assertTrue(result["trigger_created"])
        self.assertTrue((root / "plan.json").exists())
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_trigger(self):
        result, _ = self.run_case(
            create=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_complete_trigger(self):
        result, _ = self.run_case(
            complete=True,
            active_lock=True,
        )
        self.assertTrue(result["trigger_completed"])

    def test_clear_trigger_lock(self):
        result, _ = self.run_case(
            clear=True,
            active_lock=True,
        )
        self.assertEqual(result["state"], "LOCAL_TRIGGER_LOCK_CLEARED")

    def test_safety_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["local_trigger_execution_enabled"])
        self.assertFalse(result["windows_task_install_enabled"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
