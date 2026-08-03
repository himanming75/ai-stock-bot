import tempfile, unittest
from pathlib import Path
from paper_position_lifecycle.rules import evaluate_exit
from paper_position_lifecycle.accounting import close_position
from paper_position_lifecycle.state import build_position_state
from paper_position_lifecycle.engine import evaluate

class Tests(unittest.TestCase):
    def test_stop_loss(self):
        r=evaluate_exit({"average_cost":100,"quantity":10},94,1,100,{})
        self.assertEqual(r["reason"],"STOP_LOSS")
    def test_take_profit(self):
        r=evaluate_exit({"average_cost":100,"quantity":10},111,1,111,{})
        self.assertEqual(r["reason"],"TAKE_PROFIT")
    def test_trailing_stop(self):
        r=evaluate_exit({"average_cost":100,"quantity":10},104,5,110,{})
        self.assertEqual(r["reason"],"TRAILING_STOP")
    def test_max_holding(self):
        r=evaluate_exit({"average_cost":100,"quantity":10},101,20,101,{})
        self.assertEqual(r["reason"],"MAX_HOLDING_PERIOD")
    def test_hold(self):
        r=evaluate_exit({"average_cost":100,"quantity":10},102,2,102,{})
        self.assertEqual(r["action"],"HOLD")
    def test_close_position(self):
        r=close_position("AAPL",{"average_cost":100,"quantity":10},110)
        self.assertEqual(r["realized_pnl"],100)
    def test_state(self):
        s=build_position_state({"AAPL":{"quantity":5,"average_cost":100,"mark_price":101}},{},"2026-08-04")
        self.assertEqual(s["positions"]["AAPL"]["holding_days"],1)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"PAPER_POSITION_LIFECYCLE_SOURCE_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
