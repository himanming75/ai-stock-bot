import json
import tempfile
import unittest
from pathlib import Path

from paper_pilot.validation_analytics import MultiDayValidationAnalytics


class Tests(unittest.TestCase):
    def write(self, path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def append(self, path, records):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "".join(json.dumps(item) + "\n" for item in records),
            encoding="utf-8",
        )

    def run_case(self, records, summary=None, gate=None):
        td = tempfile.TemporaryDirectory()
        self.addCleanup(td.cleanup)
        root = Path(td.name)
        policy = {
            "paper_only": True,
            "read_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "maximum_trend_points": 60,
        }
        summary = summary or {
            "validation_days": len(records),
            "healthy_days": sum(
                1 for item in records if item.get("day_healthy")
            ),
            "unhealthy_days": sum(
                1 for item in records if not item.get("day_healthy")
            ),
            "consecutive_healthy_days": len(records),
            "minimum_validation_days": 5,
            "minimum_consecutive_healthy_days": 3,
            "validation_complete": False,
        }
        gate = gate or {
            "validation_gate_clear": False,
            "gate_reasons": ["MINIMUM_VALIDATION_DAYS_NOT_MET"],
        }
        self.write(root/"policy.json", policy)
        self.write(root/"summary.json", summary)
        self.write(root/"gate.json", gate)
        if records:
            self.append(root/"ledger.jsonl", records)

        result = MultiDayValidationAnalytics().run(
            policy_path=root/"policy.json",
            validation_summary_path=root/"summary.json",
            validation_gate_path=root/"gate.json",
            validation_ledger_path=root/"ledger.jsonl",
            analytics_path=root/"analytics.json",
            trend_path=root/"trend.json",
            report_path=root/"report.json",
            dashboard_state_path=root/"dashboard.json",
            result_path=root/"result.json",
        )
        return result, root

    def test_empty_data_waits(self):
        result, _ = self.run_case([])
        self.assertEqual(result["state"], "WAIT_VALIDATION_DATA")

    def test_progress_calculation(self):
        records = [{"day_healthy": True}] * 3
        result, _ = self.run_case(records)
        self.assertEqual(result["progress_pct"], 60)

    def test_healthy_rate(self):
        records = [
            {"day_healthy": True},
            {"day_healthy": True},
            {"day_healthy": False},
        ]
        result, _ = self.run_case(records)
        self.assertAlmostEqual(result["healthy_rate_pct"], 66.66666667)

    def test_equity_trend_up(self):
        records = [
            {"validation_date": "2026-08-01", "latest_equity": 100000},
            {"validation_date": "2026-08-02", "latest_equity": 101000},
        ]
        result, _ = self.run_case(records)
        self.assertEqual(result["equity_trend"], "UP")

    def test_complete_analytics(self):
        records = [{"day_healthy": True}] * 5
        summary = {
            "validation_days": 5,
            "healthy_days": 5,
            "unhealthy_days": 0,
            "consecutive_healthy_days": 5,
            "minimum_validation_days": 5,
            "minimum_consecutive_healthy_days": 3,
            "validation_complete": True,
        }
        gate = {"validation_gate_clear": True, "gate_reasons": []}
        result, _ = self.run_case(records, summary, gate)
        self.assertEqual(
            result["state"], "VALIDATION_ANALYTICS_COMPLETE"
        )

    def test_read_only_contract(self):
        result, _ = self.run_case([])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertFalse(result["broker_write_enabled"])


if __name__ == "__main__":
    unittest.main()
