import tempfile, unittest
from pathlib import Path
from position_manager_v2.config import load, validate
from position_manager_v2.positions import apply_buy, apply_sell, mark
from position_manager_v2.exposure import calculate
from position_manager_v2.recovery import build as recovery
from position_manager_v2.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            c = load(Path(t))
            self.assertFalse(c["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_average_cost(self):
        p = apply_buy({"quantity": 0, "average_cost": 0}, 5, 100)
        p = apply_buy(p, 5, 102)
        self.assertEqual(p["average_cost"], 101)

    def test_realized_pnl(self):
        p = {"quantity": 10, "average_cost": 100, "realized_pnl": 0}
        p = apply_sell(p, 2, 105)
        self.assertEqual(p["realized_pnl"], 10)

    def test_unrealized_pnl(self):
        p = mark({"quantity": 10, "average_cost": 100, "realized_pnl": 0}, 102)
        self.assertEqual(p["unrealized_pnl"], 20)

    def test_exposure(self):
        e = calculate([{"symbol": "A", "sector": "T", "market_value": 100}], 900)
        self.assertEqual(e["equity"], 1000)

    def test_recovery_safe(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(recovery(Path(t))["automatic_submission_allowed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
