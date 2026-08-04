import tempfile, unittest
from pathlib import Path
from real_paper_validation.config import load, validate
from real_paper_validation.client import AlpacaPaperClient
from real_paper_validation.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["micro_paper_order_enabled"])
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_live_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            AlpacaPaperClient("a", "b", "https://api.alpaca.markets")

    def test_default_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(Path(t), allow_network=False)
            self.assertEqual(r["actual_paper_orders_submitted"], 0)
            self.assertEqual(r["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
