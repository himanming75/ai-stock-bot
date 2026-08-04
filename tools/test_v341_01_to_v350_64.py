from __future__ import annotations
import unittest
from governed_decision_bridge.engine import build_decision
from governed_decision_bridge.replay import verify_replay


def payload():
    return {
        "symbol": "AAPL",
        "governance": {
            "state": "REAL_PAPER_OBSERVATION_GOVERNANCE_QUALIFIED",
            "health": "HEALTHY",
            "incidents": [],
        },
        "account": {
            "status": "ACTIVE",
            "buying_power": "100000",
            "trading_blocked": False,
            "account_blocked": False,
        },
        "positions": [],
        "open_orders": [],
        "signal": {"action": "BUY", "confidence": 80},
        "portfolio": {"selected": True, "weight": 0.10},
        "risk": {"recommended_quantity": 2, "reference_price": 200},
        "strategy_votes": [
            {"strategy": "MOMENTUM", "action": "BUY", "confidence": 0.9, "weight": 1.0},
            {"strategy": "TREND", "action": "BUY", "confidence": 0.8, "weight": 1.0},
            {"strategy": "MEAN_REVERSION", "action": "HOLD", "confidence": 0.4, "weight": 0.5},
        ],
    }


class Tests(unittest.TestCase):
    def test_candidate_ready(self):
        result = build_decision(payload())
        self.assertEqual(result["state"], "GOVERNED_DECISION_CANDIDATE_READY")

    def test_submission_always_false(self):
        result = build_decision(payload())
        self.assertFalse(result["paper_order_candidate"]["submission_allowed"])

    def test_governance_blocks(self):
        value = payload()
        value["governance"]["health"] = "WARNING"
        result = build_decision(value)
        self.assertEqual(result["state"], "GOVERNED_DECISION_BLOCKED")

    def test_duplicate_blocks(self):
        value = payload()
        value["open_orders"] = [{"symbol": "AAPL", "side": "buy", "status": "accepted"}]
        result = build_decision(value)
        self.assertIn("DUPLICATE_OPEN_ORDER", result["constraints"]["blocking_reasons"])

    def test_buying_power_blocks(self):
        value = payload()
        value["account"]["buying_power"] = "100"
        result = build_decision(value)
        self.assertIn("INSUFFICIENT_BUYING_POWER", result["constraints"]["blocking_reasons"])

    def test_hold_no_candidate(self):
        value = payload()
        value["strategy_votes"] = []
        value["signal"] = {"action": "HOLD", "confidence": 0.9}
        result = build_decision(value)
        self.assertIn("HOLD_HAS_NO_ORDER_CANDIDATE", result["constraints"]["blocking_reasons"])

    def test_replay_integrity(self):
        result = build_decision(payload())
        self.assertTrue(verify_replay(result)["valid"])

    def test_zero_orders(self):
        result = build_decision(payload())
        self.assertEqual(result["actual_paper_orders_submitted"], 0)
        self.assertEqual(result["actual_live_orders_submitted"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
