from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.live_order_gate_v84_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=LiveOrderGateConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):LiveOrderGateConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(gate_policy()["rules"]["live_order_submit_enabled"])
 def test_intent(self): self.assertFalse(make_live_intent("AAPL","BUY",1,100)["live_order_submission_authorized"])
 def test_bad_intent(self):
  with self.assertRaises(ValueError):make_live_intent("AAPL","BUY",0,100)
 def test_idempotency(self): self.assertTrue(idempotency_key(make_live_intent("AAPL","BUY",1,100))["key"].startswith("live-idem-"))
 def test_duplicate(self): self.assertTrue(duplicate_guard(["x","x"])["duplicate_detected"])
 def test_environment(self): self.assertTrue(environment_gate(make_live_intent("AAPL","BUY",1,100),self.c)["allowed"])
 def test_approval(self): self.assertTrue(approval_gate(3,self.c)["allowed"])
 def test_kill_switch(self): self.assertTrue(kill_switch_gate(self.c)["allowed"])
 def test_emergency(self): self.assertTrue(emergency_stop_gate(self.c)["allowed"])
 def test_account(self):
  a={"status":"ACTIVE","equity":1,"buying_power":1,"trading_blocked":True,"source":"OFFLINE_FIXTURE"}
  self.assertTrue(account_gate(a)["allowed"])
 def test_buying_power(self): self.assertTrue(buying_power_gate(make_live_intent("AAPL","BUY",1,100),self.c)["allowed"])
 def test_position(self): self.assertFalse(position_gate(make_live_intent("AAPL","SELL",10,100),5,self.c)["allowed"])
 def test_daily_loss(self): self.assertTrue(daily_loss_gate(-500,self.c)["halt_required"])
 def test_exposure(self): self.assertFalse(exposure_gate(4800,make_live_intent("AAPL","BUY",3,100),self.c)["allowed"])
 def test_preflight(self):
  a={"status":"ACTIVE","equity":1,"buying_power":10000,"trading_blocked":True,"source":"OFFLINE_FIXTURE"}
  self.assertEqual(preflight(make_live_intent("AAPL","BUY",1,100),3,a,0,0.0,0.0,self.c)["status"],"GATE_PASS")
 def test_receipt(self):
  a={"status":"ACTIVE","equity":1,"buying_power":10000,"trading_blocked":True,"source":"OFFLINE_FIXTURE"}
  i=make_live_intent("AAPL","BUY",1,100);idem=idempotency_key(i);pf=preflight(i,3,a,0,0.0,0.0,self.c)
  self.assertEqual(gate_receipt(i,idem,pf)["status"],"GATE_PASS")
 def test_replay(self):
  r={"receipt_sha256":"x"};self.assertTrue(replay_guard([r,r])["replay_detected"])
 def test_scenarios(self):
  s=build_scenarios(self.c);self.assertEqual(s["scenario_count"],4);self.assertGreater(s["gate_reject_count"],0)
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
   with self.assertRaises(ValueError):validate_enablement_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/live_order_gate_v84_21_40.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V84.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
