import tempfile, unittest
from pathlib import Path
from paper_qualification.config import load, validate
from paper_qualification.reconciliation import compare
from paper_qualification.order_states import coverage
from paper_qualification.recovery import evaluate as recovery
from paper_qualification.metrics import calculate
from paper_qualification.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            p = load(Path(t))
            self.assertFalse(p["paper_submission_enabled"])
            self.assertFalse(p["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_reconciliation_pass(self):
        state = {"account": {"cash": 1}, "positions": [], "orders": []}
        self.assertTrue(compare(state, state)["passed"])

    def test_reconciliation_mismatch(self):
        left = {"account": {"cash": 1}, "positions": [], "orders": []}
        right = {"account": {"cash": 2}, "positions": [], "orders": []}
        self.assertFalse(compare(left, right)["passed"])

    def test_order_coverage(self):
        rows = [{"status": x} for x in ("new", "accepted", "partially_filled", "filled", "canceled")]
        self.assertEqual(coverage(rows)["coverage_pct"], 100.0)

    def test_recovery(self):
        rows = [{"recovery_status": "PASS", "duplicate_order": False, "resolved": True}]
        self.assertTrue(recovery(rows)["recovery_passed"])

    def test_metrics(self):
        result = calculate([{"pnl": 2}, {"pnl": -1}], [100, 102, 101])
        self.assertEqual(result["profit_factor"], 2.0)

    def test_engine_zero_orders(self):
        with tempfile.TemporaryDirectory() as t:
            result = evaluate(Path(t))
            self.assertEqual(result["actual_paper_orders_submitted"], 0)
            self.assertEqual(result["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
