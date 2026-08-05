from __future__ import annotations
import unittest

from paper_portfolio.accounting import apply_fill
from paper_portfolio.guard import run_fill_accounting


def portfolio():
    return {
        "portfolio_version": "V392.12A",
        "cash": 100000.0,
        "equity": 100000.0,
        "realized_pnl": 0.0,
        "unrealized_pnl": 0.0,
        "positions": {},
    }


def fill(side="BUY", qty=5.0, price=200.0, state="FILLED"):
    return {
        "fill_event_version": "V392.11A",
        "fill_event_id": f"fill-{side}-{qty}-{price}-{state}",
        "symbol": "AAPL",
        "side": side,
        "fill_state": state,
        "fill_price": price,
        "filled_quantity": qty,
        "filled_notional": qty * price,
        "simulated": True,
        "target_environment": "PAPER",
        "broker_adapter": "NONE",
    }


def simulator_result():
    return {
        "stage": "V392.11A",
        "state": "PAPER_EXECUTION_SIMULATOR_READY",
        "status": "PASS",
        "simulated_fill_created": True,
        "fill_accounting_allowed": True,
        "broker_network_enabled": False,
        "paper_submission_enabled": False,
        "live_submission_enabled": False,
    }


class Tests(unittest.TestCase):
    def test_buy_updates_cash_and_position(self):
        result = apply_fill(portfolio(), fill(), set())
        self.assertTrue(result["approved"])
        self.assertEqual(result["portfolio_state"]["cash"], 99000.0)
        self.assertEqual(
            result["portfolio_state"]["positions"]["AAPL"]["quantity"], 5.0
        )

    def test_average_cost(self):
        first = apply_fill(portfolio(), fill(qty=5, price=200), set())
        second = apply_fill(
            first["portfolio_state"],
            fill(qty=5, price=220),
            {first["accounting_event"]["fill_event_id"]},
        )
        self.assertEqual(
            second["portfolio_state"]["positions"]["AAPL"]["average_cost"],
            210.0,
        )

    def test_sell_realized_pnl(self):
        first_fill = fill(qty=5, price=200)
        first = apply_fill(portfolio(), first_fill, set())
        sell = fill(side="SELL", qty=2, price=230)
        second = apply_fill(
            first["portfolio_state"],
            sell,
            {first_fill["fill_event_id"]},
        )
        position = second["portfolio_state"]["positions"]["AAPL"]
        self.assertEqual(position["quantity"], 3.0)
        self.assertEqual(position["realized_pnl"], 60.0)

    def test_partial_fill_supported(self):
        event = fill(qty=2.5, price=200, state="PARTIALLY_FILLED")
        result = apply_fill(portfolio(), event, set())
        self.assertEqual(
            result["portfolio_state"]["positions"]["AAPL"]["quantity"], 2.5
        )

    def test_no_fill_no_change(self):
        event = fill(qty=0, price=200, state="NO_FILL")
        result = apply_fill(portfolio(), event, set())
        self.assertEqual(result["portfolio_state"]["cash"], 100000.0)

    def test_replay_rejected(self):
        event = fill()
        result = apply_fill(portfolio(), event, {event["fill_event_id"]})
        self.assertTrue(result["replay_detected"])
        self.assertFalse(result["approved"])

    def test_invalid_live_fill_rejected(self):
        event = fill()
        event["target_environment"] = "LIVE"
        result = apply_fill(portfolio(), event, set())
        self.assertFalse(result["approved"])

    def test_zero_orders(self):
        result = run_fill_accounting(
            simulator_result(),
            fill(),
            portfolio(),
            set(),
        )
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
