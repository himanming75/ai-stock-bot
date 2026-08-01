from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_order_authorization_v83_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperOrderAuthorizationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperOrderAuthorizationConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(authorization_policy()["paper_submission_allowed"])
 def test_request(self): self.assertEqual(request_authorization("u","i","r",300)["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(request_authorization("u","i","r",300),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_evaluation(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  self.assertTrue(evaluate_request(r,self.c)["threshold_met"])
 def test_scopes(self): self.assertEqual(scope_contract()["submit_capability_count"],0)
 def test_token(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);self.assertFalse(t["paper_order_submission_authorized"])
 def test_token_validation(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);self.assertEqual(validate_token(t,"i")["status"],"PASS")
 def test_consume(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);self.assertTrue(consume_token(t)["used"])
 def test_revoke(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);self.assertTrue(revoke_token(t,"x")["revoked"])
 def test_expire(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);self.assertTrue(expire_token(t)["expired"])
 def test_replay(self): self.assertTrue(replay_guard(["x","x"])["replay_detected"])
 def test_receipt(self):
  r=request_authorization("u","i","r",300);r=add_approval(r,"a");r=add_approval(r,"b")
  t=issue_authorization_token(r,evaluate_request(r,self.c),self.c);v=validate_token(t,"i")
  self.assertEqual(authorization_receipt(t,v)["status"],"AUTHORIZATION_READY")
 def test_state_machine(self): self.assertFalse(authorization_state_machine()["paper_submit_enabled_state_present"])
 def test_scenarios(self): self.assertTrue(build_scenarios(self.c)["replay_detected"])
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
   with self.assertRaises(ValueError):validate_order_gate_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_order_authorization_v83_21_40.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V83.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
