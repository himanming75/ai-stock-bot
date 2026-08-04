import tempfile, unittest
from pathlib import Path
from autonomous_paper_trading.config import load, validate
from autonomous_paper_trading.idempotency import make_key, register
from autonomous_paper_trading.engine import evaluate
from autonomous_paper_trading.alpaca_paper import AlpacaPaperClient

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["real_paper_submission_enabled"])
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_live_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            AlpacaPaperClient("a", "b", "https://api.alpaca.markets")

    def test_idempotency(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            key = make_key("S", {"symbol": "A", "action": "BUY", "quantity": 1})
            self.assertTrue(register(root, key, {})["registered"])
            self.assertTrue(register(root, key, {})["duplicate"])

    def test_dry_run_zero(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(Path(t), allow_network=False)
            self.assertEqual(r["actual_paper_orders_submitted"], 0)
            self.assertEqual(r["actual_live_orders_submitted"], 0)

    def test_network_not_authorized_block(self):
        with tempfile.TemporaryDirectory() as t:
            r = evaluate(Path(t), allow_network=False)
            self.assertIn("NETWORK_CALL_NOT_AUTHORIZED_FOR_THIS_RUN", r["blocking_reasons"])

if __name__ == "__main__":
    unittest.main()
