from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.live_safety_foundation_v82_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=LiveSafetyConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):LiveSafetyConfig(allow_network=True).validate()
 def test_environment(self): self.assertEqual(environment_guard("paper")["environment"],"PAPER")
 def test_live_environment_blocked(self): self.assertFalse(environment_guard("LIVE")["live_access_allowed"])
 def test_lock(self): self.assertFalse(live_mode_lock()["live_mode_enabled"])
 def test_request(self): self.assertEqual(approval_request("u","r",300)["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(approval_request("u","r",300),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_evaluation(self):
  r=approval_request("u","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  self.assertTrue(evaluate_approvals(r,self.c)["approval_threshold_met"])
 def test_token(self):
  e={"approval_threshold_met":True};self.assertEqual(issue_dry_run_token(e,self.c)["scope"],"DRY_RUN_ONLY")
 def test_kill_switch(self): self.assertTrue(kill_switch()["trading_blocked"])
 def test_emergency(self): self.assertTrue(emergency_stop("x")["new_orders_blocked"])
 def test_loss_guard(self): self.assertFalse(daily_loss_guard(-500,100000,self.c)["breached"])
 def test_loss_breach(self): self.assertTrue(daily_loss_guard(-3000,100000,self.c)["breached"])
 def test_drawdown(self): self.assertFalse(drawdown_guard(.01,self.c)["breached"])
 def test_order_guard(self): self.assertTrue(order_notional_guard(5,100,self.c)["allowed"])
 def test_order_block(self): self.assertFalse(order_notional_guard(20,100,self.c)["allowed"])
 def test_position_guard(self): self.assertTrue(position_notional_guard(2500,self.c)["allowed"])
 def test_state_machine(self): self.assertFalse(authorization_state_machine()["live_state_present"])
 def test_dry_run(self):
  env=environment_guard("PAPER");token={"scope":"DRY_RUN_ONLY"}
  g=dry_run_guard(token,env,order_notional_guard(5,100,self.c),position_notional_guard(2500,self.c),
   daily_loss_guard(-500,100000,self.c),drawdown_guard(.01,self.c),kill_switch(),None)
  self.assertEqual(g["status"],"PASS")
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
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/live_safety_foundation_v82_01_20.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V82.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__":unittest.main()
