import tempfile,unittest
from pathlib import Path
from controlled_micro_live.approval import build_approval
from controlled_micro_live.token import issue_simulated_token,consume_simulated_token
from controlled_micro_live.kill_switch import evaluate
from controlled_micro_live.payload import build_payload
from controlled_micro_live.simulator import simulate
from controlled_micro_live.review import evaluate as review
from controlled_micro_live.engine import evaluate as run

POLICY={
"approval_expiry_minutes":5,"simulated_token_issue_enabled":False,
"manual_kill_switch":False,"current_daily_pnl":0,"maximum_daily_loss":20,
"current_daily_order_count":0,"maximum_daily_orders":1,
"maximum_notional":250,"maximum_quantity":1,
"market_open_required":True,"market_open":True,
"broker_health":"HEALTHY","simulated_fill_price":200,
"live_network_enabled":False,"live_submission_enabled":False,
}
C={"candidate_id":"c1","symbol":"AAPL","side":"buy","quantity":1,
"order_type":"market","estimated_notional":200}

class Tests(unittest.TestCase):
    def test_approval(self):
        self.assertFalse(build_approval(C,POLICY)["fully_approved"])
    def test_token_not_issued(self):
        a=build_approval(C,POLICY)
        self.assertFalse(issue_simulated_token(a,POLICY)["token_present"])
    def test_token_replay(self):
        t={"token_valid":True,"token_used":False}
        used=consume_simulated_token(t)
        replay=consume_simulated_token(used)
        self.assertTrue(replay["token_replay_detected"])
    def test_kill_switch(self):
        self.assertTrue(evaluate(POLICY,C)["passed"])
    def test_payload_review_only(self):
        self.assertTrue(build_payload(C)["review_only"])
    def test_simulation_live_zero(self):
        s=simulate(build_payload(C),POLICY)
        self.assertFalse(s["actual_live_order_submitted"])
    def test_review(self):
        a=build_approval(C,POLICY)
        t=issue_simulated_token(a,POLICY)
        k=evaluate(POLICY,C)
        p=build_payload(C)
        s=simulate(p,POLICY)
        self.assertTrue(review(C,a,t,k,p,s,POLICY)["passed"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["state"],"CONTROLLED_MICRO_LIVE_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
