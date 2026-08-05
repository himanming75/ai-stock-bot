from __future__ import annotations

import unittest
from decimal import Decimal

from order_ticket_generator.service import OrderTicketGeneratorService


class Tests(unittest.TestCase):
    def execution(self):
        return {
            "execution_plans": [
                {
                    "symbol": "QQQ",
                    "blocked": False,
                    "quantity": "6.7256",
                    "reference_price": "565.00",
                    "side": "buy",
                    "order_type": "limit",
                    "slice_count": 3,
                    "limit_price": "565.11",
                }
            ]
        }

    def policy(self):
        return {
            "time_in_force": "day",
            "extended_hours": False,
            "client_order_prefix": "aisb",
            "minimum_quantity": "0.0001",
            "maximum_ticket_notional": "5000",
            "fractional_precision": 4,
        }

    def test_three_slices_generated(self):
        tickets = OrderTicketGeneratorService().generate(
            self.execution(), self.policy()
        )
        self.assertEqual(len(tickets), 3)

    def test_quantity_is_preserved(self):
        tickets = OrderTicketGeneratorService().generate(
            self.execution(), self.policy()
        )
        total = sum(
            (Decimal(ticket.payload["qty"]) for ticket in tickets),
            Decimal("0"),
        )
        self.assertEqual(total, Decimal("6.7256"))

    def test_limit_payload(self):
        ticket = OrderTicketGeneratorService().generate(
            self.execution(), self.policy()
        )[0]
        self.assertEqual(ticket.payload["type"], "limit")
        self.assertEqual(ticket.payload["limit_price"], "565.11")

    def test_deterministic_client_order_id(self):
        service = OrderTicketGeneratorService()
        first = service.generate(self.execution(), self.policy())[0]
        second = service.generate(self.execution(), self.policy())[0]
        self.assertEqual(first.client_order_id, second.client_order_id)

    def test_no_submission_side_effect(self):
        import inspect
        source = inspect.getsource(OrderTicketGeneratorService.run_file)
        self.assertIn('"actual_order_submission_performed": False', source)
        self.assertIn('"actual_paper_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
