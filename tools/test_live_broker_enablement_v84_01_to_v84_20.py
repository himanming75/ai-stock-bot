from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.live_broker_enablement_v84_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=LiveBrokerEnablementConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):LiveBrokerEnablementConfig(allow_network=True).validate()
 def test_registry(self): self.assertEqual(capability_registry()["write_capability_count"],0)
 def test_environment(self): self.assertTrue(environment_guard("LIVE")["live_environment_selected"])
 def test_request(self): self.assertEqual(approval_request("u","r")["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(approval_request("u","r"),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_approval(self):
  r=approval_request("u","r")
  for x in ("a","b","c"): r=add_approval(r,x)
  self.assertTrue(evaluate_approvals(r,self.c)["threshold_met"])
 def test_kill_switch(self): self.assertTrue(kill_switch(self.c)["armed"])
 def test_emergency(self): self.assertTrue(emergency_stop(self.c)["enabled"])
 def test_account_guard(self):
  a={"account_id":"x","status":"ACTIVE","equity":1,"buying_power":1,"trading_blocked":True,"source":"OFFLINE_FIXTURE"}
  self.assertEqual(account_guard(a)["status"],"PASS")
 def test_position_guard(self): self.assertTrue(position_guard({"symbol":"A","quantity":1,"mark_price":100},self.c)["allowed"])
 def test_order_guard(self): self.assertFalse(order_guard({"symbol":"A","quantity":10,"reference_price":100},self.c)["allowed"])
 def test_daily_loss(self): self.assertTrue(daily_loss_guard(-500,self.c)["halt_required"])
 def test_state_machine(self): self.assertFalse(state_machine()["live_enabled_state_present"])
 def test_scenarios(self):
  s=build_scenarios(self.c);self.assertGreater(s["order_reject_count"],0);self.assertGreater(s["daily_loss_halt_count"],0)
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
   with self.assertRaises(ValueError):validate_paper_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/live_broker_enablement_v84_01_20.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V84.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__":unittest.main()
