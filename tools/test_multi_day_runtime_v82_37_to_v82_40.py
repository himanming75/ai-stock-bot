
import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.multi_day_runtime_v82_37_40 import (
    next_trading_date,
    run_multi_day_runtime,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def policy(self):
        return {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "automatic_session_start_enabled": False,
            "continuous_loop_enabled": False,
            "market_holidays": ["2026-09-07"],
        }

    def run_case(
        self,
        *,
        certified=True,
        next_prepared=True,
        execute=False,
        reset=False,
        active_lock=False,
        existing_completed=False,
    ):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "eod.json", {
            "state": "NEXT_TRADING_DAY_READY",
            "trading_date": "2026-09-04",
        })
        self.write(root / "cert.json", {
            "certified": certified,
            "trading_date": "2026-09-04",
        })
        self.write(root / "next.json", {
            "next_day_ready": next_prepared,
            "next_trading_date": "2026-09-08",
        })
        self.write(root / "policy.json", self.policy())

        if active_lock:
            self.write(root / "lock.json", {
                "active": True,
                "runtime_id": "runtime-existing",
            })

        if existing_completed:
            (root / "ledger.jsonl").write_text(
                json.dumps({
                    "event": "ROLLOVER_COMPLETED",
                    "next_trading_date": "2026-09-08",
                }) + "\n",
                encoding="utf-8",
            )

        result = run_multi_day_runtime(
            end_of_day_result_path=root / "eod.json",
            certification_path=root / "cert.json",
            next_day_state_path=root / "next.json",
            policy_path=root / "policy.json",
            runtime_state_path=root / "runtime.json",
            rollover_lock_path=root / "lock.json",
            runtime_ledger_path=root / "ledger.jsonl",
            rollover_plan_path=root / "plan.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
            execute_rollover=execute,
            reset_runtime=reset,
        )
        return result, root

    def test_next_trading_date_weekend_and_holiday(self):
        result = next_trading_date(
            "2026-09-04",
            {"2026-09-07"},
        )
        self.assertEqual(result, "2026-09-08")

    def test_wait_certification(self):
        result, _ = self.run_case(certified=False)
        self.assertEqual(result["state"], "WAIT_DAILY_CERTIFICATION")

    def test_wait_next_day_preparation(self):
        result, _ = self.run_case(next_prepared=False)
        self.assertEqual(result["state"], "WAIT_NEXT_DAY_PREPARATION")

    def test_rollover_ready(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "MULTI_DAY_ROLLOVER_READY")

    def test_execute_rollover(self):
        result, root = self.run_case(execute=True)
        self.assertTrue(result["rollover_completed"])
        self.assertEqual(
            result["state"],
            "MULTI_DAY_ROLLOVER_COMPLETE",
        )
        self.assertTrue((root / "runtime.json").exists())
        self.assertTrue((root / "plan.json").exists())
        self.assertTrue((root / "ledger.jsonl").exists())

    def test_duplicate_rollover_blocked(self):
        result, _ = self.run_case(
            execute=True,
            active_lock=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_completed_rollover_blocked(self):
        result, _ = self.run_case(
            execute=True,
            existing_completed=True,
        )
        self.assertEqual(result["status"], "BLOCKED")

    def test_reset_runtime(self):
        result, _ = self.run_case(reset=True)
        self.assertTrue(result["runtime_reset"])
        self.assertEqual(result["state"], "MULTI_DAY_RUNTIME_RESET")

    def test_dashboard_written(self):
        result, root = self.run_case()
        self.assertTrue(result["dashboard_state_written"])
        self.assertTrue((root / "dashboard.json").exists())

    def test_read_only_contract(self):
        result, _ = self.run_case(execute=True)
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertFalse(result["automatic_session_start_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
