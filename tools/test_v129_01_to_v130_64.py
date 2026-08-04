import tempfile,unittest
from pathlib import Path
from restricted_live_candidate.account import normalize_account
from restricted_live_candidate.candidates import build
from restricted_live_candidate.gate import evaluate
from restricted_live_candidate.reconcile import compare
from restricted_live_candidate.gateway import evaluate as gateway
from restricted_live_candidate.engine import evaluate as run

POLICY={
"allowed_symbols":["AAPL"],"maximum_quantity":1,"maximum_notional":250,
"current_daily_pnl":0,"maximum_daily_loss":20,
"current_daily_order_count":0,"maximum_daily_orders":1,
"kill_switch_clear":True,"paper_qualification_passed":True,
"live_network_write_enabled":False,"live_submission_enabled":False,
}
SOURCE={"live_order_candidates":[{
"candidate_id":"c1","symbol":"AAPL","side":"buy","quantity":1,
"order_type":"market","estimated_notional":200}]}

class Tests(unittest.TestCase):
    def test_account(self):
        self.assertEqual(normalize_account({"equity":"100"})["equity"],100)
    def test_candidates(self):
        self.assertEqual(len(build(SOURCE)),1)
    def test_gate(self):
        c=build(SOURCE)
        a={"status":"ACTIVE","account_blocked":False,"trading_blocked":False}
        self.assertTrue(evaluate(c,a,[],[],POLICY)["passed"])
    def test_reconcile(self):
        self.assertTrue(compare(build(SOURCE),[],[])["passed"])
    def test_gateway_blocked(self):
        self.assertFalse(gateway({"passed":True},POLICY)["authorized"])
    def test_missing_source(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["state"],"RESTRICTED_LIVE_CANDIDATE_SOURCE_REQUIRED")
    def test_live_zero(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(run(Path(t))["actual_live_orders_submitted"],0)

if __name__=="__main__":unittest.main()
