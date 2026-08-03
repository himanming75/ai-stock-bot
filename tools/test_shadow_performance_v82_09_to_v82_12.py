
import json
import tempfile
import unittest
from pathlib import Path

from shadow_runtime.performance_analytics_v82_09_12 import (
    calculate_cycle_health,
    calculate_drawdown,
    calculate_trade_metrics,
    run_shadow_performance_analytics,
)


class Tests(unittest.TestCase):
    def test_drawdown(self):
        result = calculate_drawdown([100, 120, 90, 130])
        self.assertEqual(result["maximum_drawdown"], 30)
        self.assertEqual(result["maximum_drawdown_pct"], 25)

    def test_trade_metrics(self):
        result = calculate_trade_metrics([10, -5, 15, -5])
        self.assertEqual(result["trade_count"], 4)
        self.assertEqual(result["win_rate_pct"], 50)
        self.assertEqual(result["profit_factor"], 2.5)
        self.assertEqual(result["expectancy"], 3.75)

    def test_cycle_health(self):
        result = calculate_cycle_health([
            {"completed": True, "elapsed_ms": 10},
            {"completed": False, "elapsed_ms": 20},
        ])
        self.assertEqual(result["cycle_success_rate_pct"], 50)
        self.assertEqual(result["average_cycle_elapsed_ms"], 15)

    def write_json(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def write_jsonl(self, path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(row) for row in rows) + "\n",
            encoding="utf-8",
        )

    def run_case(self, enough_samples=False, enough_cycles=False):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        equity_rows = (
            [{"equity": value} for value in [100, 105, 102, 110, 120]]
            if enough_samples
            else [{"equity": 100}]
        )
        cycle_rows = (
            [
                {"completed": True, "elapsed_ms": 10},
                {"completed": True, "elapsed_ms": 11},
                {"completed": True, "elapsed_ms": 12},
            ]
            if enough_cycles else []
        )

        self.write_jsonl(root / "equity.jsonl", equity_rows)
        self.write_json(root / "portfolio.json", {
            "equity": equity_rows[-1]["equity"],
            "realized_pnl": 20,
        })
        if cycle_rows:
            self.write_jsonl(root / "cycles.jsonl", cycle_rows)
        self.write_json(root / "policy.json", {
            "shadow_only": True,
            "broker_write_enabled": False,
            "live_trading_enabled": False,
            "initial_equity": 100,
            "minimum_equity_samples": 5,
            "minimum_cycles": 3,
            "minimum_cycle_success_rate_pct": 90,
            "trade_pnls": [10, -5, 15],
        })

        result = run_shadow_performance_analytics(
            equity_history_path=root / "equity.jsonl",
            portfolio_state_path=root / "portfolio.json",
            cycle_ledger_path=root / "cycles.jsonl",
            policy_path=root / "policy.json",
            analytics_path=root / "analytics.json",
            health_report_path=root / "health.json",
            dashboard_path=root / "dashboard.json",
            result_path=root / "result.json",
        )
        return result, root

    def test_in_progress(self):
        result, _ = self.run_case()
        self.assertEqual(result["state"], "SHADOW_ANALYTICS_IN_PROGRESS")

    def test_complete(self):
        result, _ = self.run_case(
            enough_samples=True,
            enough_cycles=True,
        )
        self.assertEqual(result["state"], "SHADOW_ANALYTICS_COMPLETE")
        self.assertTrue(result["analytics_complete"])

    def test_reports_written(self):
        result, root = self.run_case()
        self.assertTrue(result["analytics_written"])
        self.assertTrue((root / "analytics.json").exists())
        self.assertTrue((root / "health.json").exists())
        self.assertTrue((root / "dashboard.json").exists())

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
