import tempfile, unittest
from pathlib import Path
from live_shadow_slippage.config import load, validate
from live_shadow_slippage.quote import normalize
from live_shadow_slippage.slippage import estimate
from live_shadow_slippage.qualification import evaluate as qualify
from live_shadow_slippage.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c = load(Path(t))
            self.assertFalse(c["live_submission_enabled"])
            self.assertFalse(c["broker_write_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_quote_mid(self):
        q = normalize({"bid": 99, "ask": 101, "last": 100})
        self.assertEqual(q["mid"], 100)

    def test_spread_pct(self):
        q = normalize({"bid": 99, "ask": 101, "last": 100})
        self.assertEqual(q["spread_pct"], 2)

    def test_buy_slippage(self):
        q = normalize({"bid": 99.9, "ask": 100.1, "last": 100})
        s = estimate({"side": "BUY", "paper_reference_price": 100}, q)
        self.assertGreater(s["slippage_pct"], 0)

    def test_sell_slippage(self):
        q = normalize({"bid": 99.9, "ask": 100.1, "last": 100})
        s = estimate({"side": "SELL", "paper_reference_price": 100}, q)
        self.assertGreater(s["slippage_pct"], 0)

    def test_qualification_pass(self):
        p = load(Path(tempfile.mkdtemp()))
        q = normalize({"bid": 99.99, "ask": 100.01, "last": 100, "market_open": True, "quote_age_seconds": 1})
        s = estimate({"side": "BUY", "paper_reference_price": 100, "quantity": 1}, q)
        r = qualify(p, {"quantity": 1}, {"buying_power": 1000}, q, s)
        self.assertTrue(r["passed"])

    def test_stale_quote_blocked(self):
        p = load(Path(tempfile.mkdtemp()))
        q = normalize({"bid": 99.99, "ask": 100.01, "last": 100, "market_open": True, "quote_age_seconds": 100})
        s = estimate({"side": "BUY", "paper_reference_price": 100, "quantity": 1}, q)
        self.assertFalse(qualify(p, {"quantity": 1}, {"buying_power": 1000}, q, s)["passed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            result = evaluate(Path(t))
            self.assertEqual(result["actual_live_orders_submitted"], 0)
            self.assertEqual(result["daily_report"]["sample_count"], 1)

if __name__ == "__main__":
    unittest.main()
