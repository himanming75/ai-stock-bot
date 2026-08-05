from decimal import Decimal
import unittest
from intelligence_v4.models import StrategyCandidate
from intelligence_v4.ensemble import StrategyEnsembleV4
from intelligence_v4.risk import AdaptiveRiskEngineV3
from intelligence_v4.portfolio import PortfolioIntelligenceV2
from intelligence_v4.execution import ExecutionIntelligenceV2

class Tests(unittest.TestCase):
    def test_low_confidence_holds(self):
        d = StrategyEnsembleV4().decide(
            candidates=[StrategyCandidate("x", Decimal("0.1"), Decimal("0.1"), Decimal("0.1"), Decimal("0.1"), Decimal("0.5"), Decimal("0.5"))],
            market_regime="RANGING",
        )
        self.assertTrue(d.blocked)
        self.assertEqual(d.action, "HOLD")

    def test_daily_loss_blocks(self):
        d = AdaptiveRiskEngineV3().evaluate(
            symbol="AAPL", base_notional=Decimal("100"), volatility=Decimal("0.2"),
            sector_exposure=Decimal("0.1"), portfolio_exposure=Decimal("0.2"),
            drawdown_ratio=Decimal("0.1"), consecutive_losses=0,
            daily_loss_limit_reached=True, strategy_risk_budget=Decimal("1"),
        )
        self.assertTrue(d.blocked)

    def test_sector_limit_blocks(self):
        d = PortfolioIntelligenceV2().allocate(
            symbol="AAPL", portfolio_value=Decimal("10000"), current_weight=Decimal("0"),
            desired_weight=Decimal("0.1"), sector_weight_after=Decimal("0.5"),
            correlated_exposure_after=Decimal("0.2"),
        )
        self.assertIn("SECTOR_CONCENTRATION_LIMIT", d.blockers)

    def test_large_order_blocks(self):
        d = ExecutionIntelligenceV2().plan(
            symbol="AAPL", side="buy", quantity=Decimal("10"),
            reference_price=Decimal("200"), spread_bps=Decimal("2"),
            volatility=Decimal("0.2"), urgency=Decimal("0.5"),
            maximum_order_notional=Decimal("1000"),
        )
        self.assertTrue(d.blocked)

    def test_limit_plan(self):
        d = ExecutionIntelligenceV2().plan(
            symbol="AAPL", side="buy", quantity=Decimal("1"),
            reference_price=Decimal("200"), spread_bps=Decimal("4"),
            volatility=Decimal("0.2"), urgency=Decimal("0.4"),
            maximum_order_notional=Decimal("1000"),
        )
        self.assertFalse(d.blocked)
        self.assertEqual(d.order_type, "limit")

if __name__ == "__main__":
    unittest.main(verbosity=2)
