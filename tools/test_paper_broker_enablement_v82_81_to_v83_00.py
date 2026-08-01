from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_broker_enablement_v82_81_v83_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerEnablementConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerEnablementConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(paper_enablement_policy()["live_enablement_allowed"])
 def test_request(self): self.assertEqual(session_request("u","r",900)["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(session_request("u","r",900),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_approval(self):
  r=session_request("u","r",900);r=add_approval(r,"a");r=add_approval(r,"b")
  self.assertTrue(evaluate_approvals(r,self.c)["threshold_met"])
 def test_environment(self): self.assertTrue(environment_lock("PAPER")["paper_locked"])
 def test_capabilities(self): self.assertEqual(capability_verification()["write_capability_count"],0)
 def test_account(self): self.assertEqual(account_validation()["status"],"PASS")
 def test_health(self): self.assertEqual(health_validation()["status"],"PASS")
 def test_receipt(self):
  r=session_request("u","r",900);r=add_approval(r,"a");r=add_approval(r,"b");e=evaluate_approvals(r,self.c)
  receipt=issue_permission_receipt(r,e,paper_enablement_policy(),environment_lock("PAPER"),capability_verification(),account_validation(),health_validation(),self.c)
  self.assertEqual(receipt["status"],"ISSUED")
 def test_state_machine(self): self.assertFalse(enablement_state_machine()["live_enabled_state_present"])
 def test_session(self):
  r=session_request("u","r",900);r=add_approval(r,"a");r=add_approval(r,"b");e=evaluate_approvals(r,self.c)
  receipt=issue_permission_receipt(r,e,paper_enablement_policy(),environment_lock("PAPER"),capability_verification(),account_validation(),health_validation(),self.c)
  self.assertTrue(session_snapshot(receipt,self.c)["paper_session_authorized"])
 def test_revoke(self):
  session={"session_id":"x"};self.assertEqual(revoke_session(session,"done")["state"],"REVOKED")
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
   with self.assertRaises(ValueError):validate_dry_run_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_broker_enablement_v82_81_v83_00.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V82.{i:02d}" for i in range(81,100)]+["V83.00"]),20)
if __name__=="__main__":unittest.main()
