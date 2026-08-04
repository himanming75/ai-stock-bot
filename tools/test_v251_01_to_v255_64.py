import tempfile, unittest
from pathlib import Path
from execution_optimizer.config import load, validate
from execution_optimizer.quote_analyzer import analyze
from execution_optimizer.fill_probability import estimate
from execution_optimizer.slippage import estimate as slip
from execution_optimizer.planner import build
from execution_optimizer.retry_manager import build as retry
from execution_optimizer.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(load(Path(t))["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_quote(self):
        p = load(Path(tempfile.mkdtemp()))
        q = analyze({"bid": 99, "ask": 101, "last": 100, "quote_age_seconds": 1}, p)
        self.assertEqual(q["mid"], 100)

    def test_stale_quote(self):
        p = load(Path(tempfile.mkdtemp()))
        self.assertFalse(analyze({"bid": 99, "ask": 100, "quote_age_seconds": 99}, p)["passed"])

    def test_fill_probability(self):
        r = estimate({"spread_pct": 0.01}, {"relative_volume": 2, "top_of_book_depth": 1000, "volatility_pct": 1})
        self.assertGreater(r["fill_probability_pct"], 60)

    def test_slippage(self):
        r = slip({"action": "BUY", "reference_price": 100}, {"ask": 100.1, "bid": 99.9, "mid": 100})
        self.assertGreater(r["expected_slippage_pct"], 0)

    def test_plan_limit(self):
        p = load(Path(tempfile.mkdtemp()))
        q = {"passed": True, "mid": 100}
        plan = build({"symbol": "A", "action": "BUY", "quantity": 1, "confidence": 80}, q, {"fill_probability_pct": 90}, {"expected_slippage_pct": 0.01}, p)
        self.assertEqual(plan["order_type"], "LIMIT")

    def test_retry_no_submission(self):
        self.assertFalse(retry({"order_type": "LIMIT"}, {"retry_limit": 2, "retry_delay_seconds": 5, "partial_fill_timeout_seconds": 90})["broker_submission_step_included"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
