import tempfile, unittest
from pathlib import Path
from ai_strategy_ensemble_v3.config import load, validate
from ai_strategy_ensemble_v3.regime import detect
from ai_strategy_ensemble_v3.scoring import score
from ai_strategy_ensemble_v3.allocation import allocate
from ai_strategy_ensemble_v3.decision import combine
from ai_strategy_ensemble_v3.gate import evaluate as gate
from ai_strategy_ensemble_v3.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(load(Path(t))["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_bull_regime(self):
        self.assertEqual(detect({"trend_score": 70, "breadth_pct": 60, "volatility_pct": 2})["regime"], "BULL_TREND")

    def test_sideways_regime(self):
        self.assertEqual(detect({"trend_score": 50, "breadth_pct": 50, "volatility_pct": 2})["regime"], "SIDEWAYS")

    def test_strategy_score(self):
        p = load(Path(tempfile.mkdtemp()))
        row = {"strategy_id": "m", "strategy_type": "momentum", "observations": 20, "win_rate_pct": 60, "profit_factor": 1.6, "sharpe": 1.2, "maximum_drawdown_pct": 4, "signal_confidence": 80}
        self.assertGreater(score(row, "BULL_TREND", p)["score"], 55)

    def test_allocation(self):
        p = load(Path(tempfile.mkdtemp()))
        rows = [{"strategy_id": "a", "eligible": True, "score": 80}, {"strategy_id": "b", "eligible": True, "score": 70}]
        self.assertAlmostEqual(sum(x["weight_pct"] for x in allocate(rows, p)), 100, places=3)

    def test_combine_buy(self):
        rows = [{"strategy_id": "a", "symbol": "AAPL", "action": "BUY", "signal_confidence": 90, "weight_pct": 100}]
        self.assertEqual(combine(rows)[0]["action"], "BUY")

    def test_gate_blocks_exit_conflict(self):
        p = load(Path(tempfile.mkdtemp()))
        result = gate({"symbol": "AAPL", "confidence": 90}, {"risk_gate": {"passed": True}}, {"snapshot": {"rows": [{"symbol": "AAPL", "exit_triggered": True}]}}, p)
        self.assertFalse(result["passed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
