import tempfile, unittest
from pathlib import Path
from exit_manager_v2.config import load, validate
from exit_manager_v2.rules import take_profit, stop_loss, trailing_stop, break_even, time_exit
from exit_manager_v2.priority import select
from exit_manager_v2.scale_out import quantity
from exit_manager_v2.recovery import build as recovery
from exit_manager_v2.engine import evaluate

class Tests(unittest.TestCase):
    def test_policy_safe(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(load(Path(t))["live_submission_enabled"])

    def test_validate(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(validate(load(Path(t)))["valid"])

    def test_take_profit(self):
        p = {"average_cost": 100, "market_price": 106}
        self.assertTrue(take_profit(p, load(Path(tempfile.mkdtemp())))["triggered"])

    def test_stop_loss(self):
        p = {"average_cost": 100, "market_price": 96}
        self.assertTrue(stop_loss(p, load(Path(tempfile.mkdtemp())))["triggered"])

    def test_trailing_stop(self):
        p = {"market_price": 97, "highest_price": 100}
        self.assertTrue(trailing_stop(p, load(Path(tempfile.mkdtemp())))["triggered"])

    def test_break_even(self):
        p = {"average_cost": 100, "market_price": 100, "highest_price": 103}
        self.assertTrue(break_even(p, load(Path(tempfile.mkdtemp())))["triggered"])

    def test_time_exit(self):
        p = {"holding_minutes": 400}
        self.assertTrue(time_exit(p, load(Path(tempfile.mkdtemp())))["triggered"])

    def test_priority(self):
        selected = select([
            {"triggered": True, "reason": "TAKE_PROFIT"},
            {"triggered": True, "reason": "STOP_LOSS"},
        ])
        self.assertEqual(selected["reason"], "STOP_LOSS")

    def test_scale_out(self):
        self.assertEqual(quantity({"quantity": 10}, {"scale_out_pct": 50}, "TAKE_PROFIT"), 5)

    def test_recovery_safe(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(recovery(Path(t))["automatic_submission_allowed"])

    def test_engine_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"], 0)

if __name__ == "__main__":
    unittest.main()
