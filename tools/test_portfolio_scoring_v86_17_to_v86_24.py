from __future__ import annotations

import unittest

from portfolio_scoring.allocation import allocate
from portfolio_scoring.diversification import diversification_score
from portfolio_scoring.engine import evaluate_portfolio
from portfolio_scoring.models import Candidate
from portfolio_scoring.scoring import rank_candidates, score_candidate


def candidate(
    symbol,
    sector,
    decision="BUY",
    confidence=80,
    composite_score=60,
    volatility_pct=2,
    max_position_pct=15,
):
    return Candidate(
        symbol=symbol,
        sector=sector,
        decision=decision,
        confidence=confidence,
        composite_score=composite_score,
        volatility_pct=volatility_pct,
        max_position_pct=max_position_pct,
        liquidity_score=90,
    )


class PortfolioScoringTests(unittest.TestCase):
    def test_buy_candidate_positive(self):
        row = score_candidate(candidate("AAPL", "TECH"))
        self.assertGreater(row["risk_adjusted_score"], 0)

    def test_sell_candidate_negative(self):
        row = score_candidate(
            candidate("AAPL", "TECH", decision="SELL")
        )
        self.assertLess(row["risk_adjusted_score"], 0)

    def test_high_volatility_penalty(self):
        low = score_candidate(
            candidate("A", "TECH", volatility_pct=1)
        )
        high = score_candidate(
            candidate("B", "TECH", volatility_pct=8)
        )
        self.assertGreater(
            low["risk_adjusted_score"],
            high["risk_adjusted_score"],
        )

    def test_ranking(self):
        rows = rank_candidates([
            candidate("LOW", "TECH", composite_score=30),
            candidate("HIGH", "HEALTH", composite_score=80),
        ])
        self.assertEqual(rows[0]["symbol"], "HIGH")

    def test_symbol_cap_respected(self):
        ranked = rank_candidates([
            candidate("A", "TECH", max_position_pct=5),
            candidate("B", "HEALTH", max_position_pct=30),
        ])
        allocations, _ = allocate(
            ranked,
            portfolio_exposure_pct=50,
            sector_limit_pct=30,
            minimum_score=0,
        )
        a = next(row for row in allocations if row["symbol"] == "A")
        self.assertLessEqual(a["recommended_weight_pct"], 5)

    def test_sector_cap_respected(self):
        ranked = rank_candidates([
            candidate("A", "TECH", max_position_pct=30),
            candidate("B", "TECH", max_position_pct=30),
        ])
        _, summary = allocate(
            ranked,
            portfolio_exposure_pct=60,
            sector_limit_pct=25,
            minimum_score=0,
        )
        self.assertLessEqual(
            summary["sector_allocations_pct"]["TECH"], 25
        )

    def test_diversification_score(self):
        value = diversification_score(
            [{"symbol": "A"}, {"symbol": "B"}],
            {"TECH": 10, "HEALTH": 10},
        )
        self.assertGreater(value, 0)

    def test_engine_safety(self):
        result = evaluate_portfolio(
            [candidate("A", "TECH")],
            {
                "maximum_portfolio_exposure_pct": 50,
                "maximum_sector_exposure_pct": 25,
                "minimum_risk_adjusted_score": 0,
            },
        )
        self.assertTrue(result["paper_only"])
        self.assertFalse(result["broker_write_enabled"])
        self.assertFalse(result["order_submission_enabled"])


if __name__ == "__main__":
    unittest.main()
