import tempfile,unittest
from pathlib import Path
from autonomous_orchestrator.market import inspect
from autonomous_orchestrator.scanner import scan
from autonomous_orchestrator.selector import select
from autonomous_orchestrator.planner import build
from autonomous_orchestrator.execution import simulate
from autonomous_orchestrator.positions import apply
from autonomous_orchestrator.performance import summarize
from autonomous_orchestrator.checkpoint import build as checkpoint
from autonomous_orchestrator.engine import evaluate

POLICY={
"symbols":["AAPL"],"reference_prices":{"AAPL":100},
"signal_threshold_pct":0.25,"maximum_candidates_per_cycle":1,
"paper_execution_enabled":True,"live_submission_enabled":False,
"maximum_paper_orders_per_cycle":1,
}
FIX={"clock":{"is_open":True},"snapshots":{"AAPL":{"latestTrade":{"p":101}}}}
RISK={"dynamic_sizing":{"final_quantity":1}}

class Tests(unittest.TestCase):
    def test_market(self): self.assertTrue(inspect(FIX)["market_open"])
    def test_scan(self): self.assertEqual(scan(FIX,POLICY)[0]["action"],"BUY")
    def test_select(self): self.assertEqual(len(select(scan(FIX,POLICY),POLICY)),1)
    def test_plan(self): self.assertEqual(build(select(scan(FIX,POLICY),POLICY),RISK)[0]["qty"],"1")
    def test_execution(self): self.assertEqual(simulate([{"client_order_id":"x","symbol":"AAPL","side":"buy","qty":"1","estimated_price":101}],True,POLICY)["paper_orders_submitted"],1)
    def test_positions(self): self.assertEqual(apply([{"symbol":"AAPL","side":"buy","qty":1,"fill_price":100}])[0]["quantity"],1)
    def test_performance(self): self.assertEqual(summarize(1000,[])["ending_equity"],1000)
    def test_checkpoint(self): self.assertEqual(checkpoint("c","s",[],{})["generation"],1)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"AUTONOMOUS_ORCHESTRATOR_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
