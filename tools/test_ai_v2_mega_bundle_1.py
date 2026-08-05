from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from ai_v2.ensemble import StrategyEnsembleRanker
from ai_v2.learning import PerformanceLearningLedger
from ai_v2.portfolio_optimizer import PortfolioOptimizer
from ai_v2.risk_v2 import DynamicRiskEngineV2


class Tests(unittest.TestCase):
    def test_ensemble_ranks_highest_first(self):
        ranker = StrategyEnsembleRanker()
        low = ranker.score(
            strategy_id="low",
            signal_strength=Decimal("0.3"),
            historical_metrics={},
            regime_fit=Decimal("0.3"),
            risk_penalty=Decimal("0.2"),
        )
        high = ranker.score(
            strategy_id="high",
            signal_strength=Decimal("0.9"),
            historical_metrics={
                "win_rate": "0.7",
                "profit_factor": "2",
            },
            regime_fit=Decimal("0.9"),
            risk_penalty=Decimal("0"),
        )
        self.assertEqual(ranker.rank([low, high])[0].strategy_id, "high")

    def test_learning_ledger_summary(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = PerformanceLearningLedger(
                Path(directory) / "ledger.jsonl"
            )
            ledger.record(
                strategy_id="s",
                symbol="AAPL",
                pnl=Decimal("2"),
                return_pct=Decimal("0.01"),
                holding_minutes=10,
                exit_reason="TARGET",
            )
            ledger.record(
                strategy_id="s",
                symbol="AAPL",
                pnl=Decimal("-1"),
                return_pct=Decimal("-0.005"),
                holding_minutes=10,
                exit_reason="STOP",
            )
            result = ledger.summarize()
        self.assertEqual(result["trade_count"], 2)
        self.assertEqual(result["win_rate"], "0.5000")

    def test_optimizer_keeps_cash_reserve(self):
        result = PortfolioOptimizer().optimize(
            symbol_scores={"AAPL": Decimal("1")},
            total_capital=Decimal("1000"),
            maximum_symbol_weight=Decimal("0.5"),
            cash_reserve_weight=Decimal("0.2"),
        )
        self.assertGreaterEqual(Decimal(result["cash_weight"]), Decimal("0.5"))
        self.assertFalse(result["actual_portfolio_modified"])

    def test_risk_reduces_high_volatility(self):
        engine = DynamicRiskEngineV2()
        low = engine.evaluate(
            symbol="AAPL",
            base_notional=Decimal("10"),
            volatility=Decimal("0.2"),
            portfolio_drawdown=Decimal("0"),
            maximum_drawdown=Decimal("10"),
            average_correlation=Decimal("0"),
            daily_loss_limit_reached=False,
        )
        high = engine.evaluate(
            symbol="AAPL",
            base_notional=Decimal("10"),
            volatility=Decimal("0.8"),
            portfolio_drawdown=Decimal("0"),
            maximum_drawdown=Decimal("10"),
            average_correlation=Decimal("0"),
            daily_loss_limit_reached=False,
        )
        self.assertLess(high.adjusted_notional, low.adjusted_notional)

    def test_daily_loss_limit_blocks(self):
        result = DynamicRiskEngineV2().evaluate(
            symbol="AAPL",
            base_notional=Decimal("10"),
            volatility=Decimal("0.2"),
            portfolio_drawdown=Decimal("0"),
            maximum_drawdown=Decimal("10"),
            average_correlation=Decimal("0"),
            daily_loss_limit_reached=True,
        )
        self.assertTrue(result.blocked)
        self.assertEqual(result.adjusted_notional, Decimal("0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
