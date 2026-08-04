import tempfile, unittest
from pathlib import Path
from real_paper_micro_order.client import AlpacaPaperClient
from real_paper_micro_order.config import load, validate
from real_paper_micro_order.engine import evaluate
from real_paper_micro_order.idempotency import client_order_id
from real_paper_micro_order.token import inspect

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["micro_order_enabled"])
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_live_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            AlpacaPaperClient("a", "b", "https://api.alpaca.markets")

    def test_deterministic_client_id(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            p = load(root)
            self.assertEqual(client_order_id(root, p), client_order_id(root, p))

    def test_token_default_invalid(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            self.assertFalse(inspect(root, "X")["valid"])

    def test_dry_run_zero(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(Path(t), allow_network=False, allow_submission=False)
            self.assertEqual(r["actual_paper_orders_submitted"], 0)
            self.assertEqual(r["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
