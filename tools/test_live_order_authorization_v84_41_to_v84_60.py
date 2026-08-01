from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.live_order_authorization_v84_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=LiveOrderAuthorizationConfig()
 def approved(self):
  r=create_request("u","i","r",180)
  for x in ("a","b","c"): r=add_approval(r,x)
  return r
 def token(self):
  r=self.approved();return issue_token(r,evaluate_request(r,self.c),self.c)
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):LiveOrderAuthorizationConfig(allow_network=True).validate()
 def test_policy(self): self.assertFalse(authorization_policy()["submission_authorization_allowed"])
 def test_request(self): self.assertEqual(create_request("u","i","r",180)["status"],"PENDING")
 def test_duplicate_approval(self):
  r=add_approval(create_request("u","i","r",180),"a")
  with self.assertRaises(ValueError):add_approval(r,"a")
 def test_evaluation(self): self.assertTrue(evaluate_request(self.approved(),self.c)["threshold_met"])
 def test_scopes(self): self.assertEqual(scope_contract()["submit_capability_count"],0)
 def test_token(self): self.assertFalse(self.token()["live_order_submission_authorized"])
 def test_validation(self): self.assertEqual(validate_token(self.token(),"i")["status"],"PASS")
 def test_bad_validation(self): self.assertEqual(validate_token(self.token(),"wrong")["status"],"FAIL")
 def test_consume(self): self.assertTrue(consume_token(self.token())["used"])
 def test_revoke(self): self.assertTrue(revoke_token(self.token(),"x")["revoked"])
 def test_expire(self): self.assertTrue(expire_token(self.token())["expired"])
 def test_duplicate(self): self.assertTrue(duplicate_guard(["x","x"])["duplicate_detected"])
 def test_receipt(self):
  t=self.token();self.assertEqual(authorization_receipt(t,validate_token(t,"i"))["status"],"AUTHORIZATION_READY")
 def test_replay(self):
  r={"receipt_sha256":"x"};self.assertTrue(replay_guard([r,r])["replay_detected"])
 def test_state_machine(self): self.assertFalse(state_machine()["submit_enabled_state_present"])
 def test_scenarios(self):
  s=build_scenarios(self.c);self.assertTrue(s["duplicate_detected"]);self.assertTrue(s["replay_detected"])
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
   with self.assertRaises(ValueError):validate_gate_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/live_order_authorization_v84_41_60.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V84.{i:02d}" for i in range(41,61)]),20)
if __name__=="__main__":unittest.main()
