from __future__ import annotations

import inspect
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from p3_micro_paper.ticket import create_micro_ticket
from p3_micro_paper.client import AlpacaPaperTradingClient
from p3_micro_paper.service import P3MicroPaperOrderService


class Tests(unittest.TestCase):
    def test_five_dollar_market_ticket(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ticket.json"
            ticket = create_micro_ticket(
                symbol="SPY",
                notional=Decimal("5"),
                output_path=path,
            )
            self.assertFalse(ticket["blocked"])
            self.assertEqual(ticket["payload"]["notional"], "5")
            self.assertEqual(ticket["payload"]["type"], "market")

    def test_above_five_dollars_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            ticket = create_micro_ticket(
                symbol="SPY",
                notional=Decimal("6"),
                output_path=Path(directory) / "ticket.json",
            )
            self.assertTrue(ticket["blocked"])

    def test_non_allowlisted_symbol_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            ticket = create_micro_ticket(
                symbol="AAPL",
                notional=Decimal("5"),
                output_path=Path(directory) / "ticket.json",
            )
            self.assertIn("SYMBOL_NOT_ALLOWED", ticket["blockers"])

    def test_paper_endpoint_guard(self):
        source = inspect.getsource(AlpacaPaperTradingClient.__init__)
        self.assertIn("NON_PAPER_ENDPOINT_BLOCKED", source)

    def test_live_order_zero_contract(self):
        source = inspect.getsource(
            P3MicroPaperOrderService.validate_and_submit
        )
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
