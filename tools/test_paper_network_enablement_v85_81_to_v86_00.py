from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_network_enablement_v85_81_v86_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerNetworkEnablementConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerNetworkEnablementConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(enablement_policy()["network_enabled"])
 def test_registry(self): self.assertEqual(capability_registry()["write_capability_count"],0)
 def test_scope(self): self.assertFalse(credential_scope_contract()["write_scope"])
 def test_credentials(self): self.assertTrue(inspect_credentials({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_opt_in(self):
  c=PaperBrokerNetworkEnablementConfig(explicit_network_opt_in=True)
  self.assertTrue(explicit_opt_in_gate(c,{"AI_STOCK_BOT_ENABLE_PAPER_NETWORK_WRITE_FOUNDATION":"YES"})["enablement_review_allowed"])
 def test_request(self): self.assertEqual(approval_request("u","r")["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(approval_request("u","r"),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_approval(self):
  r=approval_request("u","r");r=add_approval(r,"a");r=add_approval(r,"b")
  self.assertTrue(approval_gate(r,self.c)["allowed"])
 def test_session(self): self.assertEqual(session_contract(self.c)["one_order_limit"],1)
 def test_kill_switch(self): self.assertTrue(kill_switch_gate(self.c)["allowed"])
 def test_one_order(self): self.assertFalse(one_order_limit_gate(2,self.c)["allowed"])
 def test_notional(self): self.assertFalse(notional_gate(1000,self.c)["allowed"])
 def test_receipt(self):
  r=approval_request("u","r");r=add_approval(r,"a");r=add_approval(r,"b")
  gates={"approval":approval_gate(r,self.c),"opt_in":{"allowed":True},"kill_switch":kill_switch_gate(self.c),"one_order":one_order_limit_gate(1,self.c),"notional":notional_gate(100,self.c)}
  self.assertEqual(issue_enablement_receipt(r,gates,self.c)["status"],"ENABLEMENT_FOUNDATION_READY")
 def test_revoke(self):
  x={"receipt_sha256":"x","status":"ENABLEMENT_FOUNDATION_READY","network_enabled":False,"paper_order_submission_authorized":False}
  self.assertEqual(revoke_receipt(x,"x")["status"],"REVOKED")
 def test_rollback(self): self.assertEqual(rollback_plan()["status"],"PASS")
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
   with self.assertRaises(ValueError):validate_submission_sim_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_network_enablement_v85_81_v86_00.py").read_text().lower()
  for x in ('urlopen(','tradingclient(','submit_order(','method="post"'):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V85.{i:02d}" for i in range(81,100)]+["V86.00"]),20)
if __name__=="__main__":unittest.main()
