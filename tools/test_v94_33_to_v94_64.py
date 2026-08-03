import tempfile, unittest
from pathlib import Path
from decision_orchestrator.planning import build_order_plan
from decision_orchestrator.dedup import plan_key, apply_duplicate_protection
from decision_orchestrator.gates import evaluate_gates
from decision_orchestrator.checklist import build_checklist
from decision_orchestrator.engine import evaluate

class Tests(unittest.TestCase):
    def test_plan(self):
        plans=build_order_plan(
            [{"strategy_id":"A","base_strategy":"MOMENTUM","weight_pct":50,"symbol":"AAPL"}],
            100000,.2,{"AAPL":200},{"minimum_order_notional":25}
        )
        self.assertGreater(plans[0]["quantity"],0)
    def test_plan_key_stable(self):
        plan={"strategy_id":"A","symbol":"AAPL","side":"BUY","quantity":10,"reference_price":200}
        self.assertEqual(plan_key(plan),plan_key(plan))
    def test_duplicate(self):
        plan={"strategy_id":"A","symbol":"AAPL","side":"BUY","quantity":10,"reference_price":200,"state":"PLANNED"}
        key=plan_key(plan)
        self.assertEqual(apply_duplicate_protection([plan],{key})[0]["state"],"BLOCKED_DUPLICATE")
    def test_gates(self):
        meta={"state":"META_STRATEGY_ENGINE_READY","paper_decision":"PAPER_TRADE_MINIMAL_EXPOSURE","risk_approved":True,"order_submission_enabled":False,"live_trading_enabled":False,"paper_only":True}
        plans=[{"state":"PLANNED","planned_notional":1000}]
        self.assertTrue(evaluate_gates(meta,plans,{})["passed"])
    def test_checklist(self):
        checklist=build_checklist({"checks":{"meta_strategy_ready":True,"risk_approved":True,"paper_decision_allowed":True}},[{"state":"PLANNED"}])
        self.assertTrue(any(x["item"]=="MANUAL_APPROVAL_REQUIRED" for x in checklist))
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"DECISION_ORCHESTRATION_SOURCE_REQUIRED")
    def test_safety(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertFalse(evaluate(Path(t))["order_submission_enabled"])

if __name__=="__main__": unittest.main()
