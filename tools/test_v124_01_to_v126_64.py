import tempfile,unittest
from pathlib import Path
from continuous_paper_shadow.signals import build_signals
from continuous_paper_shadow.planner import build_plans
from continuous_paper_shadow.gate import evaluate_all
from continuous_paper_shadow.shadow import build_shadow_records
from continuous_paper_shadow.qualification import evaluate
from continuous_paper_shadow.engine import evaluate as run

POLICY={"symbols":["AAPL"],"reference_prices":{"AAPL":100},
"signal_threshold_pct":0.25,"maximum_order_notional":250,
"maximum_quantity":2,"order_equity_pct":0.1,"paper_mode":True,
"live_submission_enabled":False,"minimum_sessions":20}

class Tests(unittest.TestCase):
    def test_signal_buy(self):
        r=build_signals({"AAPL":{"latestTrade":{"p":101}}},POLICY)
        self.assertEqual(r[0]["action"],"BUY")
    def test_plan(self):
        s=[{"symbol":"AAPL","price":100,"action":"BUY","strategy_id":"S"}]
        self.assertEqual(build_plans(s,{"equity":100000},POLICY)[0]["qty"],"1")
    def test_gate(self):
        p=build_plans([{"symbol":"AAPL","price":100,"action":"BUY","strategy_id":"S"}],{"equity":100000},POLICY)
        self.assertTrue(evaluate_all(p,POLICY)["passed"])
    def test_shadow_live_zero(self):
        p=[{"symbol":"AAPL","side":"buy","qty":"1","estimated_notional":100}]
        self.assertEqual(build_shadow_records(p,"X")[0]["actual_live_orders_submitted"],0)
    def test_qualification(self):
        self.assertFalse(evaluate([],POLICY)["passed"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["state"],"CONTINUOUS_PAPER_SHADOW_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
