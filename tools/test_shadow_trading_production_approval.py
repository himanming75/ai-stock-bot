from __future__ import annotations
from decimal import Decimal
import unittest

from shadow_production.approval import DeploymentLock, EmergencyStop
from shadow_production.shadow import FillSimulator, ShadowOrderIntake
from shadow_production.portfolio import ShadowPortfolio


class Tests(unittest.TestCase):
    def test_shadow_order_preview_only(self):
        order = ShadowOrderIntake().create(
            strategy_id="s",
            symbol="AAPL",
            side="buy",
            notional=Decimal("100"),
            reference_price=Decimal("200"),
            latency_ms=100,
            slippage_bps=Decimal("2"),
        )
        self.assertFalse(order.as_json()["actual_order_created"])

    def test_fill_simulated_only(self):
        order = ShadowOrderIntake().create(
            strategy_id="s",
            symbol="AAPL",
            side="buy",
            notional=Decimal("100"),
            reference_price=Decimal("200"),
            latency_ms=100,
            slippage_bps=Decimal("2"),
        )
        fill = FillSimulator().simulate(order)
        self.assertFalse(fill["actual_fill_received"])

    def test_shadow_portfolio_not_actual(self):
        portfolio = ShadowPortfolio(Decimal("1000"))
        snapshot = portfolio.snapshot()
        self.assertFalse(snapshot["actual_portfolio_modified"])

    def test_deployment_lock_blocks(self):
        result = DeploymentLock().evaluate(
            p2_validated=False,
            p3_validated=False,
            p4_validated=False,
            p5_validated=False,
            emergency_stop_active=False,
        )
        self.assertFalse(result["production_release_allowed"])

    def test_emergency_stop_preview_only(self):
        result = EmergencyStop().preview(requested=True)
        self.assertFalse(result["actual_emergency_stop_activated"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
