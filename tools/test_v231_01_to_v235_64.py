import tempfile, unittest
from pathlib import Path
from order_lifecycle_v2.config import load, validate
from order_lifecycle_v2.state_machine import can_transition, transition
from order_lifecycle_v2.fills import apply_fill
from order_lifecycle_v2.identity import client_order_id
from order_lifecycle_v2.duplicates import register
from order_lifecycle_v2.recovery import build as recovery
from order_lifecycle_v2.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c = load(Path(t))
            self.assertFalse(c["paper_submission_enabled"])
            self.assertFalse(c["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_transition_valid(self):
        self.assertTrue(can_transition("NEW", "PENDING"))

    def test_transition_invalid(self):
        self.assertFalse(can_transition("FILLED", "ACCEPTED"))

    def test_partial_fill(self):
        order = {"quantity": 10, "filled_quantity": 0, "average_fill_price": 0}
        result = apply_fill(order, 3, 100)
        self.assertEqual(result["state"], "PARTIALLY_FILLED")
        self.assertEqual(result["remaining_quantity"], 7)

    def test_full_fill_average(self):
        order = {"quantity": 10, "filled_quantity": 0, "average_fill_price": 0}
        order = apply_fill(order, 5, 100)
        order = apply_fill(order, 5, 102)
        self.assertEqual(order["state"], "FILLED")
        self.assertEqual(order["average_fill_price"], 101)

    def test_client_id_stable(self):
        self.assertEqual(client_order_id("M", "AAPL", "BUY", "1"), client_order_id("M", "AAPL", "BUY", "1"))

    def test_duplicate(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            order = {"symbol": "AAPL", "side": "BUY", "quantity": 1, "strategy_id": "M", "client_order_id": "X"}
            self.assertFalse(register(root, order)["duplicate"])
            self.assertTrue(register(root, order)["duplicate"])

    def test_recovery_no_submission(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(recovery(Path(t))["automatic_submission_allowed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
