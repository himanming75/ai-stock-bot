from __future__ import annotations
from decimal import Decimal
import tempfile
import unittest
from pathlib import Path

from ai_research_final.champion import ChampionChallengerManager
from ai_research_final.drift import DriftDetector
from ai_research_final.monte_carlo import MonteCarloSimulator
from ai_research_final.optimizer import ParameterOptimizer
from ai_research_final.rebalancer import PortfolioRebalancer
from ai_research_final.walk_forward import WalkForwardValidator


class Tests(unittest.TestCase):
    def test_walk_forward(self):
        returns = [Decimal("0.01")] * 20
        result = WalkForwardValidator().validate(
            returns=returns,
            train_size=8,
            test_size=4,
        )
        self.assertGreater(result["window_count"], 0)

    def test_monte_carlo(self):
        result = MonteCarloSimulator().simulate(
            returns=[Decimal("0.01"), Decimal("-0.005")],
            simulations=100,
            horizon=20,
        )
        self.assertEqual(result["simulation_count"], 100)
        self.assertFalse(result["actual_capital_used"])

    def test_grid_search(self):
        result = ParameterOptimizer().grid_search(
            grid={"x": [1, 2, 3]},
            objective=lambda params: Decimal(params["x"]),
        )
        self.assertEqual(result["best"]["parameters"]["x"], 3)

    def test_champion_never_auto_promotes(self):
        result = ChampionChallengerManager().evaluate(
            candidates=[
                {"strategy_id": "a", "score": "0.8"},
                {"strategy_id": "b", "score": "0.6"},
            ],
            minimum_score=Decimal("0.7"),
            minimum_margin=Decimal("0.1"),
        )
        self.assertTrue(result["promotion_eligible"])
        self.assertFalse(result["actual_promotion_performed"])

    def test_rebalancer_creates_no_orders(self):
        result = PortfolioRebalancer().preview(
            current_weights={"A": Decimal("0.5")},
            target_weights={"A": Decimal("0.6")},
            portfolio_value=Decimal("1000"),
            minimum_trade_notional=Decimal("10"),
        )
        self.assertFalse(result["actual_orders_created"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
