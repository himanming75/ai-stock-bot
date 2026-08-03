
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.scheduled_supervised_runner_v83_17_20 import (
    evaluate_schedule_gate,
    run_scheduled_supervised_runner,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def run_case(
        self,
        *,
        authorize=False,
        complete=False,
        clear=False,
        market_open=True,
        trading_day=True,
        risk_clear=True,
        supervised_ready=True,
        active_lock=False,
        observed_at="2026-08-03T15:00:00+00:00",
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "calendar.json", {
            "trading_day": trading_day,
            "market_open": market_open,
            "market_closed": not market_open,
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
        self.write(root / "policy.json", {
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "windows_task_install_enabled": False,
            "continuous_loop_enabled": False,
            "window_start_utc": "13:30",
            "window_end_utc": "20:00",
            "max_runs_per_day": 3,
            "minimum_interval_seconds": 300,
            "max_supervised_cycles_per_run": 3,
        })
        if active_lock:
            self.write(root / "lock.json", {
                "active": True,
                "authorization_id": "auth-existing",
            })

        result = run_scheduled_supervised_runner(
            market_calendar_path=root / "calendar.json",
            risk_result_path=root / "risk.json",
            supervised_result_path=root / "supervised.json",
            policy_path=root / "policy.json",
            schedule_lock_path=root / "lock.json",
            schedule_ledger_path=root / "ledger.jsonl",
            authorization_path=root / "authorization.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            authorize_run=authorize,
            complete_run=complete,
            clear_schedule_lock=clear,
            observed_at_override=observed_at,
        )
        return result, root

    def test_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "SCHEDULED_RUN_READY")

    def test_market_closed_gate(self):
        result, _ = self.run_case(market_open=False)
        self.assertIn("MARKET_NOT_OPEN", result["schedule_reasons"])

    def test_non_trading_day_gate(self):
        result, _ = self.run_case(trading_day=False)
        self.assertIn("NOT_TRADING_DAY", result["schedule_reasons"])

    def test_outside_window_gate(self):
        result, _ = self.run_case(
            observed_at="2026-08-03T22:00:00+00:00"
        )
        self.assertIn(
            "OUTSIDE_ALLOWED_TIME_WINDOW",
            result["schedule_reasons"],
        )

    def test_risk_gate(self):
        result, _ = self.run_case(risk_clear=False)
        self.assertIn("RISK_NOT_CLEAR", result["schedule_reasons"])

    def test_authorize(self):
        result, root = self.run_case(authorize=True)
        self.assertTrue(result["run_authorized"])
        self.assertTrue((root / "authorization.json").exists())
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_authorization(self):
        result, _ = self.run_case(
            authorize=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_complete(self):
        result, _ = self.run_case(
            complete=True,
            active_lock=True,
        )
        self.assertTrue(result["run_completed"])

    def test_clear_lock(self):
        result, _ = self.run_case(
            clear=True,
            active_lock=True,
        )
        self.assertEqual(result["state"], "SCHEDULE_LOCK_CLEARED")

    def test_safety(self):
        result, _ = self.run_case()
        self.assertFalse(result["windows_task_install_enabled"])
        self.assertFalse(result["continuous_loop_enabled"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
