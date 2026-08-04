import tempfile, unittest
from pathlib import Path
from real_paper_data_collection.client import AlpacaPaperClient
from real_paper_data_collection.config import load, validate
from real_paper_data_collection.metrics import calculate
from real_paper_data_collection.reconcile import compare
from real_paper_data_collection.collector import collect

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["paper_submission_enabled"])
            self.assertEqual(p["maximum_new_orders_per_day"], 0)

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_live_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            AlpacaPaperClient("a", "b", "https://api.alpaca.markets")

    def test_metrics(self):
        a = {"equity": "101", "last_equity": "100"}
        p = [{"unrealized_pl": "2"}]
        o = [{"status": "filled"}, {"status": "canceled"}]
        r = calculate(a, p, o)
        self.assertEqual(r["daily_pnl"], 1.0)
        self.assertEqual(r["unrealized_pl"], 2.0)

    def test_reconciliation(self):
        previous = {"positions": [], "orders": []}
        current = {"positions": [{"symbol": "A", "qty": "1"}], "orders": []}
        self.assertEqual(compare(previous, current)["change_count"], 1)

    def test_dry_run_zero_orders(self):
        with tempfile.TemporaryDirectory() as t:
            r = collect(Path(t), allow_network=False)
            self.assertEqual(r["actual_paper_orders_submitted"], 0)
            self.assertEqual(r["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
