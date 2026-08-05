from __future__ import annotations
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from multi_broker_etrade_unified.aggregation import (
    aggregate_positions,
    normalize_orders,
    order_statistics,
)
from multi_broker_etrade_unified.fixtures import (
    ORDERS,
    POSITIONS,
)
from multi_broker_etrade_unified.service import (
    ETradeUnifiedPortfolioService,
)


class Tests(unittest.TestCase):
    def test_duplicate_symbol_aggregation(self):
        positions = aggregate_positions(POSITIONS)
        spy = next(
            item
            for item in positions
            if item.symbol == "SPY"
        )
        self.assertEqual(
            spy.total_quantity,
            Decimal("15"),
        )
        self.assertEqual(
            spy.account_count,
            2,
        )

    def test_weighted_average_price(self):
        positions = aggregate_positions(POSITIONS)
        spy = next(
            item
            for item in positions
            if item.symbol == "SPY"
        )
        self.assertEqual(
            spy.weighted_average_price,
            Decimal(
                "503.3333333333333333333333333"
            ),
        )

    def test_order_status_normalization(self):
        orders = normalize_orders(ORDERS)
        stats = order_statistics(orders)
        self.assertEqual(
            stats["open_order_count"],
            1,
        )
        self.assertEqual(
            stats["filled_order_count"],
            1,
        )
        self.assertEqual(
            stats["cancelled_order_count"],
            1,
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                ETradeUnifiedPortfolioService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(
                result["unified_symbol_count"],
                2,
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ETradeUnifiedPortfolioService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "etrade_unified_positions.csv"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "etrade_unified_portfolio_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                ETradeUnifiedPortfolioService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertFalse(
                result[
                    "actual_broker_write_performed"
                ]
            )
            self.assertEqual(
                result[
                    "actual_paper_orders_submitted"
                ],
                0,
            )
            self.assertEqual(
                result[
                    "actual_live_orders_submitted"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
