import tempfile, unittest
from pathlib import Path
from daily_paper_close.metrics import (
    daily_metrics, fill_summary, position_summary
)
from daily_paper_close.gates import evaluate_close_gates
from daily_paper_close.report import render_markdown
from daily_paper_close.engine import evaluate

class Tests(unittest.TestCase):
    def test_daily_metrics(self):
        result=daily_metrics(100,110,5,5)
        self.assertEqual(result["daily_pnl"],10)
        self.assertEqual(result["daily_return_pct"],10)
    def test_fill_summary(self):
        simulation={"fills":[
            {"state":"FILLED","gross_notional":100},
            {"state":"PARTIALLY_FILLED","gross_notional":50},
        ]}
        result=fill_summary(simulation)
        self.assertEqual(result["fill_count"],2)
        self.assertEqual(result["partial_fill_count"],1)
    def test_position_summary(self):
        result=position_summary({
            "reported_positions":{
                "AAPL":{"quantity":5,"average_cost":100}
            }
        })
        self.assertEqual(result["open_position_count"],1)
    def test_gates_pass(self):
        account={
            "state":"PAPER_ACCOUNT_RECONCILIATION_PASS",
            "integrity":{"passed":True},
            "actual_orders_submitted":0,
            "paper_only":True,
        }
        risk={"risk_approved":True}
        simulation={
            "state":"PAPER_EXECUTION_SIMULATION_COMPLETED",
            "actual_orders_submitted":0,
            "paper_only":True,
        }
        self.assertTrue(
            evaluate_close_gates(account,risk,simulation,{})["passed"]
        )
    def test_report(self):
        text=render_markdown({
            "close_date":"2026-08-03",
            "state":"DAILY_PAPER_CLOSE_COMPLETE",
            "status":"PASS",
            "paper_only":True,
            "actual_orders_submitted":0,
            "daily_metrics":{},
            "fill_summary":{},
            "position_summary":{},
            "close_gates":{"passed":True,"failed":[]},
        })
        self.assertIn("Daily Paper Close Report",text)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(
                evaluate(Path(t))["state"],
                "DAILY_PAPER_CLOSE_SOURCE_REQUIRED",
            )
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__":
    unittest.main()
