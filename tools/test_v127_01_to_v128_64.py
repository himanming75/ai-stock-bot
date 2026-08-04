import tempfile,unittest
from pathlib import Path
from micro_live_readiness.candidates import build_candidates
from micro_live_readiness.limits import evaluate_all
from micro_live_readiness.approval import create_request,evaluate_request
from micro_live_readiness.token import inspect_token
from micro_live_readiness.gateway import evaluate_gateway
from micro_live_readiness.shadow_compare import compare
from micro_live_readiness.engine import evaluate

POLICY={
"allowed_symbols":["AAPL"],"maximum_quantity":1,
"maximum_order_notional":250,"allowed_order_types":["market"],
"current_daily_live_order_count":0,"maximum_daily_live_orders":1,
"current_daily_live_pnl":0,"maximum_daily_live_loss":20,
"paper_qualification_required":True,"paper_qualification_passed":True,
"approval_expiry_minutes":10,"live_network_enabled":False,
"live_submission_enabled":False,"kill_switch_clear":True,
}
SOURCE={"paper_order_plans":[{
"symbol":"AAPL","side":"buy","qty":"1","type":"market",
"time_in_force":"day","estimated_notional":200,
"client_order_id":"x","strategy_id":"s"}]}

class Tests(unittest.TestCase):
    def test_candidates(self):
        self.assertEqual(len(build_candidates(SOURCE,POLICY)),1)
    def test_limits(self):
        c=build_candidates(SOURCE,POLICY)
        self.assertTrue(evaluate_all(c,POLICY)["passed"])
    def test_approval_waits(self):
        c=build_candidates(SOURCE,POLICY);l=evaluate_all(c,POLICY)
        a=evaluate_request(create_request(c,l,POLICY))
        self.assertFalse(a["fully_approved"])
    def test_token_absent(self):
        self.assertFalse(inspect_token(POLICY)["token_valid"])
    def test_gateway_blocked(self):
        l={"passed":True};a={"fully_approved":False};t={"token_valid":False,"token_used":False}
        self.assertFalse(evaluate_gateway(l,a,t,POLICY)["authorized"])
    def test_shadow_zero(self):
        c=build_candidates(SOURCE,POLICY)
        self.assertEqual(compare(c,POLICY)["actual_live_orders_submitted"],0)
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["state"],"MICRO_LIVE_READINESS_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(evaluate(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
