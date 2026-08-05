from __future__ import annotations

import unittest
from decimal import Decimal

from ai_decision_orchestration.service import AIDecisionOrchestrationService


def market(risk_mode="NEUTRAL"):
    return {
        "market_context": {
            "market_regime": "MIXED",
            "risk_mode": risk_mode,
            "blockers": [],
            "warnings": [],
            "ranked_symbols": [
                {
                    "symbol": "AAA", "composite_score": "0.72", "confidence": "0.94",
                    "trade_bias": "LONG", "blockers": [], "momentum_score": "0.70",
                    "technical_score": "0.66", "news_score": "0.55",
                    "earnings_score": "0.60", "options_score": "0.73",
                },
                {
                    "symbol": "BBB", "composite_score": "0.63", "confidence": "0.91",
                    "trade_bias": "NEUTRAL", "blockers": [], "momentum_score": "0.58",
                    "technical_score": "0.61", "news_score": "0.72",
                    "earnings_score": "0.58", "options_score": "0.60",
                },
                {
                    "symbol": "CCC", "composite_score": "0.40", "confidence": "0.95",
                    "trade_bias": "NEUTRAL", "blockers": [], "momentum_score": "0.42",
                    "technical_score": "0.50", "news_score": "0.50",
                    "earnings_score": "0.50", "options_score": "0.50",
                },
            ],
        }
    }


class DecisionOrchestrationTests(unittest.TestCase):
    def test_selects_ranked_symbols(self):
        result = AIDecisionOrchestrationService().orchestrate(market())
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.selected_symbols, ("AAA", "BBB"))

    def test_maximum_symbol_limit(self):
        result = AIDecisionOrchestrationService().orchestrate(
            market(), {"maximum_symbols": 1}
        )
        self.assertEqual(result.selected_symbols, ("AAA",))

    def test_risk_off_blocks_selection(self):
        result = AIDecisionOrchestrationService().orchestrate(market("RISK_OFF"))
        self.assertEqual(result.status, "BLOCKED")
        self.assertIn("NO_SYMBOLS_SELECTED", result.blockers)

    def test_total_weight_cap(self):
        result = AIDecisionOrchestrationService().orchestrate(
            market(), {"maximum_total_weight": "0.60"}
        )
        self.assertLessEqual(result.portfolio_weight, Decimal("0.60"))

    def test_no_order_side_effects_in_file_payload(self):
        service = AIDecisionOrchestrationService()
        result = service.orchestrate(market())
        self.assertTrue(result.selected_symbols)
        self.assertEqual(sum(1 for x in result.decisions if x.selected), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
