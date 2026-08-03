from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from paper_runtime.multi_day_paper_validation_v83_77_80 import (
    run_multi_day_paper_validation,
)


class MultiDayPaperValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.autonomous = self.root / "autonomous.json"
        self.policy = self.root / "policy.json"
        self.ledger = self.root / "daily.jsonl"
        self.summary = self.root / "summary.json"
        self.dashboard = self.root / "dashboard.json"
        self.result = self.root / "result.json"
        self.autonomous.write_text(json.dumps({
            "stage_range": "V83.73-V83.76",
            "state": "PAPER_AUTONOMOUS_CYCLE_AUTHORIZED",
            "status": "PASS",
        }), encoding="utf-8")
        self.policy.write_text(json.dumps({
            "paper_only": True,
            "broker_write_enabled": False,
            "order_submission_enabled": False,
            "live_trading_enabled": False,
            "external_network_enabled": False,
            "continuous_loop_enabled": False,
            "windows_task_enabled": False,
            "automatic_broker_execution_enabled": False,
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def run_day(self, day: str):
        return run_multi_day_paper_validation(
            autonomous_result_path=self.autonomous,
            policy_path=self.policy,
            daily_ledger_path=self.ledger,
            summary_path=self.summary,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override=f"{day}T16:00:00+00:00",
            validation_date_override=day,
            minimum_days=3,
        )

    def test_first_day_in_progress(self):
        result = self.run_day("2026-08-03")
        self.assertEqual(result["state"], "MULTI_DAY_PAPER_VALIDATION_IN_PROGRESS")
        self.assertEqual(result["completed_days"], 1)
        self.assertTrue(result["daily_record_written"])

    def test_duplicate_date_is_idempotent(self):
        self.run_day("2026-08-03")
        result = self.run_day("2026-08-03")
        self.assertEqual(result["completed_days"], 1)
        self.assertFalse(result["daily_record_written"])
        self.assertTrue(result["duplicate_date"])

    def test_three_unique_days_complete(self):
        self.run_day("2026-08-03")
        self.run_day("2026-08-04")
        result = self.run_day("2026-08-05")
        self.assertEqual(result["state"], "MULTI_DAY_PAPER_VALIDATION_COMPLETE")
        self.assertTrue(result["requirement_met"])
        self.assertEqual(
            result["next_phase"],
            "V83_81_PAPER_STABILITY_CERTIFICATION",
        )

    def test_unsafe_policy_blocks(self):
        value = json.loads(self.policy.read_text(encoding="utf-8"))
        value["broker_write_enabled"] = True
        self.policy.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_day("2026-08-03")
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["completed_days"], 0)

    def test_invalid_source_state_blocks(self):
        value = json.loads(self.autonomous.read_text(encoding="utf-8"))
        value["state"] = "PAPER_AUTONOMOUS_SAFE_MODE"
        self.autonomous.write_text(json.dumps(value), encoding="utf-8")
        result = self.run_day("2026-08-03")
        self.assertEqual(result["status"], "BLOCKED")

    def test_reset_ledger(self):
        self.run_day("2026-08-03")
        result = run_multi_day_paper_validation(
            autonomous_result_path=self.autonomous,
            policy_path=self.policy,
            daily_ledger_path=self.ledger,
            summary_path=self.summary,
            dashboard_path=self.dashboard,
            result_path=self.result,
            observed_at_override="2026-08-04T16:00:00+00:00",
            validation_date_override="2026-08-04",
            minimum_days=3,
            reset_ledger=True,
        )
        self.assertEqual(result["validation_dates"], ["2026-08-04"])


if __name__ == "__main__":
    unittest.main()
