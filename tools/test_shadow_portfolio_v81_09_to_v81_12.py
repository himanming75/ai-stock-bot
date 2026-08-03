import json
import tempfile
import unittest
from pathlib import Path

from shadow_trading.portfolio_pnl_v81_09_12 import (
    apply_fill,
    default_portfolio,
    mark_to_market,
    run_shadow_portfolio,
)


class Tests(unittest.TestCase):
    def write(self, path: Path, payload: dict) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload), encoding="utf-8")

    def write_jsonl(self, path: Path, records: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            "\n".join(json.dumps(item) for item in records) + "\n",
            encoding="utf-8",
        )

    def test_buy_updates_average_and_cash(self):
        portfolio = default_portfolio(1000)
        result = apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 2,
                "fill_price": 100,
                "commission": 1,
            },
        )
        self.assertEqual(result["cash"], 799)
        self.assertEqual(
            result["positions"]["AAPL"]["average_price"],
            100,
        )

    def test_weighted_average(self):
        portfolio = default_portfolio(1000)
        apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 1,
                "fill_price": 100,
                "commission": 0,
            },
        )
        apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 1,
                "fill_price": 120,
                "commission": 0,
            },
        )
        self.assertEqual(
            portfolio["positions"]["AAPL"]["average_price"],
            110,
        )

    def test_sell_realized_pnl(self):
        portfolio = default_portfolio(1000)
        apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 2,
                "fill_price": 100,
                "commission": 0,
            },
        )
        apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "SELL",
                "quantity": 1,
                "fill_price": 120,
                "commission": 1,
            },
        )
        self.assertEqual(portfolio["realized_pnl"], 19)

    def test_insufficient_position_blocked(self):
        portfolio = default_portfolio(1000)
        with self.assertRaises(ValueError):
            apply_fill(
                portfolio,
                {
                    "symbol": "AAPL",
                    "side": "SELL",
                    "quantity": 1,
                    "fill_price": 120,
                    "commission": 0,
                },
            )

    def test_mark_to_market(self):
        portfolio = default_portfolio(1000)
        apply_fill(
            portfolio,
            {
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 2,
                "fill_price": 100,
                "commission": 0,
            },
        )
        result = mark_to_market(portfolio, {"AAPL": 110})
        self.assertEqual(result["unrealized_pnl"], 20)
        self.assertEqual(result["equity"], 1020)

    def run_case(self, execution_state="SHADOW_EXECUTION_FILLED"):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)

        self.write(root / "execution.json", {"state": execution_state})
        self.write(
            root / "policy.json",
            {
                "shadow_only": True,
                "broker_write_enabled": False,
                "live_trading_enabled": False,
                "initial_cash": 100000,
                "maximum_gross_exposure_pct": 100,
                "maximum_symbol_exposure_pct": 50,
            },
        )
        self.write(root / "prices.json", {"AAPL": 110})
        self.write_jsonl(
            root / "fills.jsonl",
            [{
                "fill_id": "fill-1",
                "symbol": "AAPL",
                "side": "BUY",
                "quantity": 1,
                "fill_price": 100,
                "commission": 0,
            }],
        )

        result = run_shadow_portfolio(
            execution_result_path=root / "execution.json",
            fill_ledger_path=root / "fills.jsonl",
            policy_path=root / "policy.json",
            portfolio_state_path=root / "portfolio.json",
            market_prices_path=root / "prices.json",
            equity_history_path=root / "equity.jsonl",
            daily_report_path=root / "daily.json",
            dashboard_path=root / "dashboard.json",
            recovery_snapshot_path=root / "recovery.json",
            result_path=root / "result.json",
        )
        return result, root

    def test_portfolio_updated(self):
        result, root = self.run_case()
        self.assertEqual(result["state"], "SHADOW_PORTFOLIO_UPDATED")
        self.assertEqual(result["new_fill_count"], 1)
        self.assertTrue((root / "portfolio.json").exists())

    def test_duplicate_fill_ignored(self):
        result, root = self.run_case()
        second = run_shadow_portfolio(
            execution_result_path=root / "execution.json",
            fill_ledger_path=root / "fills.jsonl",
            policy_path=root / "policy.json",
            portfolio_state_path=root / "portfolio.json",
            market_prices_path=root / "prices.json",
            equity_history_path=root / "equity.jsonl",
            daily_report_path=root / "daily.json",
            dashboard_path=root / "dashboard.json",
            recovery_snapshot_path=root / "recovery.json",
            result_path=root / "result.json",
        )
        self.assertEqual(second["new_fill_count"], 0)
        self.assertEqual(second["state"], "SHADOW_PORTFOLIO_NO_CHANGE")

    def test_wait_execution(self):
        result, _ = self.run_case(
            execution_state="WAIT_SHADOW_TRADING_FOUNDATION"
        )
        self.assertEqual(result["state"], "WAIT_SHADOW_EXECUTION")

    def test_read_only_contract(self):
        result, _ = self.run_case()
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])
        self.assertEqual(result["network_requests_executed"], 0)
        self.assertEqual(result["write_requests_executed"], 0)
        self.assertEqual(result["actual_paper_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main()
