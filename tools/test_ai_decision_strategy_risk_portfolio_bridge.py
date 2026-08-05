from __future__ import annotations
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from ai_decision_bridge.service import DecisionBridgeService

class FakeEnsemble:
    def decide(self, **kwargs):
        return SimpleNamespace(action="TRADE", confidence=Decimal("0.80"), blockers=(), explanation=("FAKE",))
class FakeRisk:
    def evaluate(self, **kwargs):
        return SimpleNamespace(approved_notional=Decimal("1000"), risk_multiplier=Decimal("0.50"), blockers=())
class FakePortfolio:
    def allocate(self, **kwargs):
        return SimpleNamespace(target_weight=Decimal("0.20"), target_notional=Decimal("2000"), rebalance_required=True, blockers=())

def payload(selected=True):
    return {"decision_orchestration":{"market_regime":"MIXED","blockers":[],"decisions":[
        {"symbol":"QQQ","selected":selected,"composite_score":"0.70","confidence":"0.90","target_weight":"0.20","strategy_route":"OPTIONS_CONFIRMATION_ENSEMBLE"}
    ]}}

class BridgeTests(unittest.TestCase):
    def service(self):
        return DecisionBridgeService(FakeEnsemble(), FakeRisk(), FakePortfolio())

    @patch("ai_decision_bridge.service.build_candidates", return_value=[object()])
    def test_selected_decision_is_approved(self, _):
        r = self.service().bridge(payload())
        self.assertEqual(r.status, "PASS")
        self.assertEqual(r.approved_symbols, ("QQQ",))

    @patch("ai_decision_bridge.service.build_candidates", return_value=[object()])
    def test_notional_uses_lower_gate(self, _):
        r = self.service().bridge(payload())
        self.assertEqual(r.decisions[0].approved_notional, Decimal("1000"))

    def test_no_selected_decision_blocks(self):
        r = self.service().bridge(payload(False))
        self.assertEqual(r.status, "BLOCKED")
        self.assertIn("NO_SELECTED_AI_DECISIONS", r.blockers)

    @patch("ai_decision_bridge.service.build_candidates", return_value=[object()])
    def test_daily_loss_limit_blocks(self, _):
        class BlockRisk(FakeRisk):
            def evaluate(self, **kwargs):
                return SimpleNamespace(approved_notional=Decimal("0"), risk_multiplier=Decimal("0"), blockers=("DAILY_LOSS_LIMIT_REACHED",))
        r = DecisionBridgeService(FakeEnsemble(), BlockRisk(), FakePortfolio()).bridge(payload())
        self.assertEqual(r.status, "BLOCKED")

    @patch("ai_decision_bridge.service.build_candidates", return_value=[object()])
    def test_no_side_effect_fields_needed_for_bridge(self, _):
        r = self.service().bridge(payload())
        self.assertGreater(r.total_approved_notional, 0)

if __name__ == "__main__": unittest.main(verbosity=2)
