import tempfile, unittest
from pathlib import Path
from multi_timeframe_strategy.config import load, validate
from multi_timeframe_strategy.timeframes import profile_for, enrich
from multi_timeframe_strategy.scoring import score
from multi_timeframe_strategy.conflicts import resolve
from multi_timeframe_strategy.voting import vote
from multi_timeframe_strategy.allocation import build
from multi_timeframe_strategy.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_profiles(self):
        p = load(Path(tempfile.mkdtemp()))
        self.assertEqual(profile_for("1m", p), "SCALP")
        self.assertEqual(profile_for("15m", p), "DAY")
        self.assertEqual(profile_for("1d", p), "SWING")

    def test_confidence_gate(self):
        p = load(Path(tempfile.mkdtemp()))
        r = enrich({"timeframe": "1m", "confidence": 50}, p)
        self.assertFalse(r["eligible"])

    def test_score(self):
        r = score({"confidence": 80, "trend_alignment": 80, "volume_confirmation": 80, "profile": "DAY"})
        self.assertGreater(r["strategy_score"], 70)

    def test_conflict(self):
        rows = [
            {"symbol": "A", "strategy_score": 90, "eligible": True},
            {"symbol": "A", "strategy_score": 80, "eligible": True},
        ]
        resolved = resolve(rows, False)
        self.assertEqual(len([x for x in resolved if x["eligible"]]), 1)

    def test_vote(self):
        rows = [{"symbol": "A", "strategy_id": "x", "profile": "DAY", "timeframe": "5m", "action": "BUY", "strategy_score": 80, "capital_weight_pct": 100, "eligible": True}]
        self.assertEqual(vote(rows)[0]["action"], "BUY")

    def test_allocation_limit(self):
        p = load(Path(tempfile.mkdtemp()))
        rows = [{"eligible": True, "risk_per_trade_pct": 0.5, "strategy_id": "x"}]
        self.assertTrue(build(rows, p)["within_total_risk_limit"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
