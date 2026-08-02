from __future__ import annotations

from decimal import Decimal
import unittest

from autonomous_paper_runtime import (
    BrokerPortfolioReconciler,
    BrokerPortfolioReconciliationPolicy,
    BrokerPortfolioStatus,
)


def account(**overrides):
    value = {
        "cash": "100000",
        "equity": "100000",
        "buying_power": "399692.65",
    }
    value.update(overrides)
    return value


def internal(**overrides):
    value = {
        "cash": "100000",
        "equity": "100000",
        "buying_power": "399692.65",
        "positions": [],
    }
    value.update(overrides)
    return value


def buy_order(**overrides):
    value = {
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": "1",
        "filled_quantity": "0",
        "limit_price": "50",
    }
    value.update(overrides)
    return value


class BrokerPortfolioReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.reconciler = BrokerPortfolioReconciler()

    def test_empty_portfolio_matched_with_recovered_order(self):
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[buy_order()],
            internal_portfolio=internal(),
            internal_open_orders=[buy_order()],
        )
        self.assertEqual(report.status, BrokerPortfolioStatus.MATCHED)
        self.assertTrue(report.autonomous_order_allowed)

    def test_cash_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            broker_account=account(cash="99999"),
            broker_positions=[],
            broker_open_orders=[],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        self.assertTrue(report.safe_mode_engaged)
        self.assertFalse(report.cash_matched)

    def test_equity_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            broker_account=account(equity="99900"),
            broker_positions=[],
            broker_open_orders=[],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        self.assertFalse(report.equity_matched)

    def test_buying_power_mismatch_blocks(self):
        report = self.reconciler.reconcile(
            broker_account=account(buying_power="300000"),
            broker_positions=[],
            broker_open_orders=[],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        self.assertFalse(report.buying_power_matched)

    def test_position_fully_matched(self):
        position = {
            "symbol": "AAPL",
            "quantity": "1",
            "average_entry_price": "50",
            "market_value": "55",
            "unrealized_pnl": "5",
        }
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[position],
            broker_open_orders=[],
            internal_portfolio=internal(positions=[position]),
            internal_open_orders=[],
        )
        self.assertEqual(report.status, BrokerPortfolioStatus.MATCHED)

    def test_position_quantity_mismatch(self):
        broker = {
            "symbol": "AAPL", "quantity": "2",
            "average_entry_price": "50", "market_value": "110",
            "unrealized_pnl": "10",
        }
        inside = {
            "symbol": "AAPL", "quantity": "1",
            "average_entry_price": "50", "market_value": "55",
            "unrealized_pnl": "5",
        }
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[broker],
            broker_open_orders=[],
            internal_portfolio=internal(positions=[inside]),
            internal_open_orders=[],
        )
        self.assertFalse(report.position_quantities_matched)

    def test_position_symbol_mismatch(self):
        broker = {
            "symbol": "SPY", "quantity": "1",
            "average_entry_price": "500", "market_value": "500",
            "unrealized_pnl": "0",
        }
        inside = {
            "symbol": "AAPL", "quantity": "1",
            "average_entry_price": "50", "market_value": "50",
            "unrealized_pnl": "0",
        }
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[broker],
            broker_open_orders=[],
            internal_portfolio=internal(positions=[inside]),
            internal_open_orders=[],
        )
        self.assertFalse(report.position_symbols_matched)

    def test_average_price_tolerance(self):
        policy = BrokerPortfolioReconciliationPolicy(
            average_price_tolerance=Decimal("0.05")
        )
        broker = {
            "symbol": "AAPL", "quantity": "1",
            "average_entry_price": "50.04", "market_value": "50",
            "unrealized_pnl": "0",
        }
        inside = {
            "symbol": "AAPL", "quantity": "1",
            "average_entry_price": "50", "market_value": "50",
            "unrealized_pnl": "0",
        }
        report = BrokerPortfolioReconciler(policy=policy).reconcile(
            broker_account=account(),
            broker_positions=[broker],
            broker_open_orders=[],
            internal_portfolio=internal(positions=[inside]),
            internal_open_orders=[],
        )
        self.assertTrue(report.average_prices_matched)

    def test_open_order_count_mismatch(self):
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[buy_order()],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        self.assertFalse(report.open_order_count_matched)

    def test_reserved_notional_mismatch(self):
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[buy_order(limit_price="50")],
            internal_portfolio=internal(),
            internal_open_orders=[buy_order(limit_price="49")],
        )
        self.assertFalse(report.reserved_buy_notional_matched)

    def test_partial_fill_reserved_notional(self):
        broker_order = buy_order(
            quantity="2",
            filled_quantity="1",
            limit_price="50",
        )
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[broker_order],
            internal_portfolio=internal(),
            internal_open_orders=[broker_order],
        )
        self.assertTrue(report.reserved_buy_notional_matched)

    def test_zero_counters(self):
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        self.assertEqual(report.read_requests_executed, 0)
        self.assertEqual(report.write_requests_executed, 0)
        self.assertEqual(report.actual_paper_orders_submitted, 0)
        self.assertEqual(report.live_orders_submitted, 0)

    def test_json(self):
        report = self.reconciler.reconcile(
            broker_account=account(),
            broker_positions=[],
            broker_open_orders=[],
            internal_portfolio=internal(),
            internal_open_orders=[],
        )
        raw = report.to_json_dict()
        self.assertEqual(raw["status"], "MATCHED")
        self.assertEqual(raw["mismatches"], [])

    def test_policy_validation(self):
        with self.assertRaises(ValueError):
            BrokerPortfolioReconciliationPolicy(
                cash_tolerance=Decimal("-1")
            ).validate()


if __name__ == "__main__":
    unittest.main()
