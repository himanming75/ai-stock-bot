import random, tempfile, unittest
from pathlib import Path
from paper_execution_simulator.cycle import build_cycle_id, read_completed_cycles
from paper_execution_simulator.fills import simulate_fill
from paper_execution_simulator.portfolio import apply_fill, mark_to_market
from paper_execution_simulator.engine import simulate

class Tests(unittest.TestCase):
    def test_cycle_stable(self):
        source={"decision_orchestration_certificate_sha256":"x","source_paper_decision":"A"}
        self.assertEqual(build_cycle_id(source,"2026-08-03"),build_cycle_id(source,"2026-08-03"))
    def test_completed_cycles(self):
        self.assertIn("abc",read_completed_cycles(['{"cycle_id":"abc","cycle_state":"COMPLETED"}']))
    def test_full_fill(self):
        plan={"quantity":10,"reference_price":100,"side":"BUY","state":"PLANNED"}
        fill=simulate_fill(plan,{"partial_fill_probability":0,"slippage_bps":5},random.Random(1))
        self.assertEqual(fill["state"],"FILLED")
    def test_partial_fill(self):
        plan={"quantity":10,"reference_price":100,"side":"BUY","state":"PLANNED"}
        fill=simulate_fill(plan,{"partial_fill_probability":1,"minimum_partial_fill_ratio":.5},random.Random(1))
        self.assertIn(fill["state"],{"PARTIALLY_FILLED","FILLED"})
    def test_apply_fill(self):
        plan={"symbol":"AAPL","side":"BUY"}
        fill={"state":"FILLED","filled_quantity":5,"fill_price":100,"commission":0,"cash_effect":-500}
        cash,positions=apply_fill(1000,{},plan,fill)
        self.assertEqual(cash,500)
        self.assertEqual(positions["AAPL"]["quantity"],5)
    def test_mark_to_market(self):
        value=mark_to_market(500,{"AAPL":{"quantity":5,"average_cost":100}},{"AAPL":110})
        self.assertEqual(value["equity"],1050)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(simulate(Path(t))["state"],"PAPER_EXECUTION_SIMULATOR_SOURCE_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(simulate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
