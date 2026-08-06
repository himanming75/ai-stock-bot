from __future__ import annotations
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from autonomous_portfolio_ai.allocator import (
    AutonomousPortfolioAllocator,
)
from autonomous_portfolio_ai.fixtures import (
    CANDIDATES,
)
from autonomous_portfolio_ai.service import (
    AutonomousPortfolioAICertificationService,
)


D = Decimal


class Tests(unittest.TestCase):
    def test_normal_allocation(self):
        result = AutonomousPortfolioAllocator().allocate(
            candidates=CANDIDATES,
            regime="BULL_TREND",
            portfolio_volatility=D("0.18"),
            drawdown_ratio=D("0.08"),
            daily_loss_ratio=D("0.01"),
            weekly_loss_ratio=D("0.02"),
        )
        self.assertEqual(
            result["risk_state"]["state"],
            "NORMAL",
        )
        self.assertTrue(
            result["rebalance_required"]
        )

    def test_max_position_guard(self):
        result = AutonomousPortfolioAllocator().allocate(
            candidates=CANDIDATES,
            regime="BULL_TREND",
            portfolio_volatility=D("0.18"),
            drawdown_ratio=D("0.08"),
            daily_loss_ratio=D("0.01"),
            weekly_loss_ratio=D("0.02"),
        )
        self.assertTrue(
            all(
                D(item["target_weight"]) <= D("0.15")
                for item in result["allocations"]
            )
        )

    def test_risk_hold(self):
        result = AutonomousPortfolioAllocator().allocate(
            candidates=CANDIDATES,
            regime="VOLATILE",
            portfolio_volatility=D("0.35"),
            drawdown_ratio=D("0.18"),
            daily_loss_ratio=D("0.04"),
            weekly_loss_ratio=D("0.07"),
        )
        self.assertEqual(
            result["risk_state"]["state"],
            "RISK_HOLD",
        )
        self.assertFalse(
            result["rebalance_required"]
        )

    def test_certification(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousPortfolioAICertificationService()
                .evaluate(
                    output_dir=Path(directory)
                )
            )
            self.assertEqual(
                result["status"],
                "PASS",
            )

    def test_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            AutonomousPortfolioAICertificationService().evaluate(
                output_dir=root
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_target_portfolio.json"
                ).exists()
            )
            self.assertTrue(
                (
                    root
                    / "autonomous_portfolio_ai_ledger.jsonl"
                ).exists()
            )

    def test_zero_order_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            result = (
                AutonomousPortfolioAICertificationService()
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
