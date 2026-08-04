import tempfile, unittest
from pathlib import Path
from paper_operations_v2.config import load, validate
from paper_operations_v2.idempotency import make_key, register
from paper_operations_v2.lifecycle import record
from paper_operations_v2.reconcile import reconcile
from paper_operations_v2.recovery import build as recovery
from paper_operations_v2.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c = load(Path(t))
            self.assertFalse(c["real_network_enabled"])
            self.assertFalse(c["paper_submission_enabled"])
            self.assertFalse(c["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_idempotency_key_stable(self):
        self.assertEqual(make_key("C", "AAPL", "BUY", "M"), make_key("C", "AAPL", "BUY", "M"))

    def test_duplicate_blocked(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            key = make_key("C", "AAPL", "BUY", "M")
            self.assertTrue(register(root, key, {"x": 1})["registered"])
            self.assertTrue(register(root, key, {"x": 1})["duplicate"])

    def test_lifecycle(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(record(Path(t), "C", "O", "PLANNED")["state"], "PLANNED")

    def test_reconcile_pass(self):
        rows = [{"symbol": "AAPL", "quantity": 1}]
        self.assertTrue(reconcile(rows, rows)["passed"])

    def test_reconcile_conflict(self):
        a = [{"symbol": "AAPL", "quantity": 1}]
        b = [{"symbol": "AAPL", "quantity": 2}]
        self.assertFalse(reconcile(a, b)["passed"])

    def test_recovery_no_live(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(recovery(Path(t))["automatic_live_resume_allowed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

    def test_engine_no_paper_submission_default(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["paper_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
