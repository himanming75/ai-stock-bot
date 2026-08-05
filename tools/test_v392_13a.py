from __future__ import annotations
import unittest

from paper_portfolio.reconciliation import reconcile_portfolio
from paper_portfolio.reconciliation_guard import run_portfolio_reconciliation


def portfolio():
    return {
        "portfolio_version": "V392.12A",
        "cash": 99000.0,
        "equity": 100000.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "positions": {
            "AAPL": {
                "symbol": "AAPL",
                "quantity": 5.0,
                "average_cost": 200.0,
                "market_price": 200.0,
                "market_value": 1000.0,
                "unrealized_pnl": 0.0,
                "realized_pnl": 0.0,
            }
        },
    }


def event():
    return {
        "accounting_event_version": "V392.12A",
        "fill_event_id": "fill-001",
        "symbol": "AAPL",
    }


def registry():
    return {"applied_fill_event_ids": ["fill-001"]}


def accounting_result():
    return {
        "stage": "V392.12A",
        "status": "PASS",
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    }


class Tests(unittest.TestCase):
    def test_reconciles(self):
        result = reconcile_portfolio(portfolio(), event(), registry())
        self.assertTrue(result["valid"])

    def test_equity_mismatch(self):
        value = portfolio()
        value["equity"] = 99999.0
        result = reconcile_portfolio(value, event(), registry())
        self.assertFalse(result["valid"])

    def test_market_value_mismatch(self):
        value = portfolio()
        value["positions"]["AAPL"]["market_value"] = 500.0
        result = reconcile_portfolio(value, event(), registry())
        self.assertFalse(result["valid"])

    def test_unrealized_pnl_mismatch(self):
        value = portfolio()
        value["positions"]["AAPL"]["unrealized_pnl"] = 10.0
        result = reconcile_portfolio(value, event(), registry())
        self.assertFalse(result["valid"])

    def test_duplicate_fill_registry(self):
        value = registry()
        value["applied_fill_event_ids"].append("fill-001")
        result = reconcile_portfolio(portfolio(), event(), value)
        self.assertFalse(result["valid"])

    def test_missing_accounting_fill(self):
        value = registry()
        value["applied_fill_event_ids"] = []
        result = reconcile_portfolio(portfolio(), event(), value)
        self.assertFalse(result["valid"])

    def test_negative_cash_blocked(self):
        value = portfolio()
        value["cash"] = -10.0
        value["equity"] = 990.0
        result = reconcile_portfolio(value, event(), registry())
        self.assertFalse(result["valid"])

    def test_zero_orders(self):
        result = run_portfolio_reconciliation(
            accounting_result(),
            portfolio(),
            event(),
            registry(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
