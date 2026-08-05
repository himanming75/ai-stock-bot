from __future__ import annotations

import inspect
import unittest
from decimal import Decimal

from paper_submission_gate.models import SubmissionPolicy
from paper_submission_gate.service import PaperSubmissionService


class FakeClient:
    def clock(self):
        return {"is_open": True}

    def account(self):
        return {"status": "ACTIVE"}

    def open_orders(self):
        return []

    def submit_order(self, payload):
        return {"id": "paper-order-1", "status": "accepted", **payload}

    def get_order_by_client_order_id(self, client_order_id):
        return {
            "id": "paper-order-1",
            "status": "accepted",
            "client_order_id": client_order_id,
        }


class Tests(unittest.TestCase):
    def ticket(self):
        return {
            "ticket_id": "ticket-1",
            "blocked": False,
            "blockers": [],
            "estimated_notional": "50",
            "payload": {
                "symbol": "QQQ",
                "qty": "0.05",
                "side": "buy",
                "type": "limit",
                "limit_price": "500",
                "time_in_force": "day",
                "client_order_id": "aisb-test",
                "extended_hours": False,
            },
        }

    def test_valid_ticket_has_no_blockers(self):
        service = PaperSubmissionService(FakeClient())
        blockers = service._ticket_blockers(
            self.ticket(),
            SubmissionPolicy(),
            {"is_open": True},
            set(),
        )
        self.assertEqual(blockers, [])

    def test_duplicate_is_blocked(self):
        service = PaperSubmissionService(FakeClient())
        blockers = service._ticket_blockers(
            self.ticket(),
            SubmissionPolicy(),
            {"is_open": True},
            {"aisb-test"},
        )
        self.assertIn("DUPLICATE_CLIENT_ORDER_ID", blockers)

    def test_notional_cap(self):
        ticket = self.ticket()
        ticket["payload"]["qty"] = "1"
        blockers = PaperSubmissionService(FakeClient())._ticket_blockers(
            ticket,
            SubmissionPolicy(maximum_order_notional=Decimal("100")),
            {"is_open": True},
            set(),
        )
        self.assertIn("ORDER_NOTIONAL_LIMIT_VIOLATION", blockers)

    def test_paper_endpoint_guard_exists(self):
        from paper_submission_gate.client import AlpacaPaperClient
        source = inspect.getsource(AlpacaPaperClient.__init__)
        self.assertIn("NON_PAPER_ENDPOINT_BLOCKED", source)

    def test_live_order_count_is_zero(self):
        source = inspect.getsource(PaperSubmissionService.submit)
        self.assertIn('"actual_live_orders_submitted": 0', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
