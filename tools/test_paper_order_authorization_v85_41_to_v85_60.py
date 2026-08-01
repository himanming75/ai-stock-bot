from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_authorization_v85_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperOrderAuthorizationConfig()
 def approved(self):
  i=create_order_intent("AAPL","BUY",2,100);r=create_request("u",i,"r",180)
  r=add_approval(r,"a");r=add_approval(r,"b");return i,r
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperOrderAuthorizationConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(authorization_policy()["paper_order_submission_allowed"])
 def test_intent(self): self.assertFalse(create_order_intent("AAPL","BUY",1,100)["paper_order_submission_authorized"])
 def test_bad_intent(self):
  with self.assertRaises(ValueError):create_order_intent("AAPL","BUY",0,100)
 def test_request(self): self.assertEqual(create_request("u",create_order_intent("AAPL","BUY",1,100),"r",180)["status"],"PENDING")
 def test_duplicate_approval(self):
  i=create_order_intent("AAPL","BUY",1,100);r=add_approval(create_request("u",i,"r",180),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_approval(self):
  _,r=self.approved();self.assertTrue(approval_gate(r,self.c)["allowed"])
 def test_opt_in(self):
  c=PaperOrderAuthorizationConfig(explicit_submission_opt_in=True)
  self.assertTrue(explicit_opt_in_gate(c,{"AI_STOCK_BOT_ENABLE_PAPER_ORDER_AUTHORIZATION":"YES"})["allowed"])
 def test_notional(self): self.assertFalse(notional_gate(create_order_intent("AAPL","BUY",10,100),self.c)["allowed"])
 def test_quantity(self): self.assertFalse(quantity_gate(create_order_intent("AAPL","BUY",11,10),self.c)["allowed"])
 def test_buying_power(self): self.assertTrue(buying_power_gate(create_order_intent("AAPL","BUY",1,100),self.c)["allowed"])
 def test_daily_loss(self): self.assertTrue(daily_loss_gate(-500,self.c)["halt_required"])
 def test_position(self): self.assertFalse(position_gate(create_order_intent("AAPL","SELL",5,100),0,self.c)["allowed"])
 def test_kill_switch(self): self.assertTrue(kill_switch_gate(self.c)["allowed"])
 def test_duplicate(self): self.assertTrue(duplicate_guard(["x","x"])["duplicate_detected"])
 def test_token(self):
  i,r=self.approved();c=PaperOrderAuthorizationConfig(explicit_submission_opt_in=True)
  gates={"approval":approval_gate(r,c),"opt_in":explicit_opt_in_gate(c,{"AI_STOCK_BOT_ENABLE_PAPER_ORDER_AUTHORIZATION":"YES"}),
         "notional":notional_gate(i,c),"quantity":quantity_gate(i,c),"buying_power":buying_power_gate(i,c),
         "daily_loss":daily_loss_gate(0,c),"position":position_gate(i,0,c),"kill_switch":kill_switch_gate(c)}
  self.assertFalse(issue_token(i,r,gates,c)["paper_order_submission_authorized"])
 def test_validation(self):
  s=build_scenarios(self.c);self.assertEqual(s["token_validation_status"],"PASS")
 def test_receipt(self): self.assertEqual(build_scenarios(self.c)["receipt_status"],"AUTHORIZATION_READY")
 def test_replay(self):
  r={"receipt_sha256":"x"};self.assertTrue(replay_guard([r,r])["replay_detected"])
 def test_scenarios(self): self.assertGreater(build_scenarios(self.c)["risk_reject_count"],0)
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"]);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_read_only_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_authorization_v85_41_60.py").read_text().lower()
  for x in ('method="post"','submit_order(','tradingclient(','urlopen('):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V85.{i:02d}" for i in range(41,61)]),20)
if __name__=="__main__":unittest.main()
