from __future__ import annotations

import inspect
import unittest
from decimal import Decimal

from partial_fill_validation.service import (
    PartialFillValidationService,
)


class Tests(unittest.TestCase):
    def service(self):
        return PartialFillValidationService(client=object())

    def partial_order(self):
        return {
            "id": "order-1",
            "client_order_id": "partial-1",
            "symbol": "SPY",
            "side": "buy",
            "status": "partially_filled",
            "qty": "10",
            "filled_qty": "4",
            "filled_avg_price": "600",
        }

    def test_partial_fill_math(self):
        state = self.service().evaluate_order(
            self.partial_order(),
            [{"symbol": "SPY", "qty": "4"}],
        )
        self.assertEqual(state.remaining_qty, Decimal("6"))
        self.assertEqual(state.fill_ratio, Decimal("0.4"))
        self.assertEqual(
            state.filled_notional,
            Decimal("2400"),
        )

    def test_partial_fill_position_consistent(self):
        state = self.service().evaluate_order(
            self.partial_order(),
            [{"symbol": "SPY", "qty": "4"}],
        )
        self.assertTrue(state.position_consistent)
        self.assertEqual(state.blockers, ())

    def test_invalid_partial_quantities_block(self):
        order = self.partial_order()
        order["filled_qty"] = "10"
        state = self.service().evaluate_order(
            order,
            [{"symbol": "SPY", "qty": "10"}],
        )
        self.assertIn(
            "INVALID_PARTIAL_FILL_QUANTITIES",
            state.blockers,
        )

    def test_read_only_contract(self):
        source = inspect.getsource(
            PartialFillValidationService.monitor
        )
        self.assertIn(
            '"actual_broker_write_performed": False',
            source,
        )
        self.assertIn(
            '"actual_order_submission_performed": False',
            source,
        )

    def test_zero_new_orders(self):
        source = inspect.getsource(
            PartialFillValidationService.monitor
        )
        self.assertIn(
            '"actual_paper_orders_submitted": 0',
            source,
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
