import os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from controlled_paper_execution.engine import execute
from controlled_paper_execution.gates import ENABLE_PHRASE
def proposal():
 return {"state":"PAPER_ORDER_PROPOSAL_AWAITING_APPROVAL","status":"PASS","proposal_hash":"a"*64,
 "proposal":{"symbol":"SPY","side":"BUY","quantity":0.001,"order_type":"market","time_in_force":"day","estimated_notional":1.0,"eligible_for_approval":True,"submission_allowed":False},
 "approval":{"approved":True,"expires_at":"2099-01-01T00:00:00+00:00"}}
def policy(enabled=False):
 return {"paper_endpoint_only":True,"live_endpoint_enabled":False,"paper_submission_enabled":enabled,"maximum_order_notional":1.0,"maximum_daily_orders":1,
 "allowed_symbols":["SPY"],"allowed_order_types":["market"],"allowed_time_in_force":["day"],"kill_switch_active":False}
class Fake:
 def __init__(self):self.submissions=[]
 def get_clock(self):return {"is_open":True}
 def get_account(self):return {"status":"ACTIVE","trading_blocked":False,"account_blocked":False}
 def get_orders(self,status="open"):return []
 def submit_order(self,p):self.submissions.append(p);return {"id":"paper-1","status":"accepted",**p}
class Tests(unittest.TestCase):
 def env(self):return patch.dict(os.environ,{"ALPACA_PAPER_API_KEY":"k","ALPACA_PAPER_SECRET_KEY":"s"})
 def test_default_policy_blocks(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(execute(Path(d),proposal(),policy())["actual_paper_orders_submitted"],0)
 def test_missing_phrase_blocks(self):
  with tempfile.TemporaryDirectory() as d,self.env():
   self.assertIn("ENABLE_PHRASE_MISMATCH",execute(Path(d),proposal(),policy(True),allow_network=True,client=Fake())["gate"]["blocking_reasons"])
 def test_notional_blocks(self):
  x=proposal();x["proposal"]["estimated_notional"]=2
  with tempfile.TemporaryDirectory() as d,self.env():self.assertEqual(execute(Path(d),x,policy(True),ENABLE_PHRASE,True,Fake())["actual_paper_orders_submitted"],0)
 def test_symbol_blocks(self):
  x=proposal();x["proposal"]["symbol"]="AAPL"
  with tempfile.TemporaryDirectory() as d,self.env():self.assertIn("SYMBOL_NOT_ALLOWED",execute(Path(d),x,policy(True),ENABLE_PHRASE,True,Fake())["gate"]["blocking_reasons"])
 def test_one_mock_order(self):
  with tempfile.TemporaryDirectory() as d,self.env():
   c=Fake();r=execute(Path(d),proposal(),policy(True),ENABLE_PHRASE,True,c);self.assertEqual(r["actual_paper_orders_submitted"],1);self.assertEqual(len(c.submissions),1)
 def test_second_blocked(self):
  with tempfile.TemporaryDirectory() as d,self.env():
   c=Fake();self.assertEqual(execute(Path(d),proposal(),policy(True),ENABLE_PHRASE,True,c)["actual_paper_orders_submitted"],1);self.assertEqual(execute(Path(d),proposal(),policy(True),ENABLE_PHRASE,True,c)["actual_paper_orders_submitted"],0)
 def test_live_zero(self):
  with tempfile.TemporaryDirectory() as d:self.assertEqual(execute(Path(d),proposal(),policy())["actual_live_orders_submitted"],0)
 def test_no_network_no_submit(self):
  with tempfile.TemporaryDirectory() as d,self.env():self.assertEqual(execute(Path(d),proposal(),policy(True),ENABLE_PHRASE,False,Fake())["actual_paper_orders_submitted"],0)
if __name__=="__main__":unittest.main(verbosity=2)
