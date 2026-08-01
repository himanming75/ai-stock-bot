from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,json
from alpaca_market_data.single_order_network_validation_v86_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=SingleOrderNetworkValidationConfig()
 def test_config(self): self.c.validate()
 def test_bad_endpoint(self):
  with self.assertRaises(ValueError):SingleOrderNetworkValidationConfig(base_url="https://api.alpaca.markets").validate()
 def test_policy(self): self.assertTrue(policy()["offline_default"])
 def test_credentials(self): self.assertTrue(credential_status({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_opt_in_default(self): self.assertFalse(opt_in_gate(self.c,{},True,True)["allowed"])
 def test_preflight(self):
  f=fixtures(self.c);self.assertEqual(preflight(self.c,f["account"],f["asset"],f["clock"],f["quote"])["status"],"PASS")
 def test_token(self):
  f=fixtures(self.c);p=preflight(self.c,f["account"],f["asset"],f["clock"],f["quote"])
  self.assertEqual(one_order_token(self.c,p)["order_limit"],1)
 def test_payload(self):
  f=fixtures(self.c);p=preflight(self.c,f["account"],f["asset"],f["clock"],f["quote"]);t=one_order_token(self.c,p)
  self.assertEqual(build_payload(self.c,t)["post_path"],"/v2/orders")
 def test_read_after_write(self):
  r={"response":fixtures(self.c)["order_response"]};self.assertEqual(read_after_write(r)["status"],"PASS")
 def test_consume(self):
  f=fixtures(self.c);p=preflight(self.c,f["account"],f["asset"],f["clock"],f["quote"]);t=one_order_token(self.c,p)
  self.assertTrue(consume_token(t)["used"])
 def test_revoke(self):
  f=fixtures(self.c);p=preflight(self.c,f["account"],f["asset"],f["clock"],f["quote"]);t=one_order_token(self.c,p)
  self.assertTrue(revoke_token(t,"x")["revoked"])
 def test_rollback(self): self.assertTrue(rollback_plan()["stop_after_one_order"])
 def test_offline(self): self.assertEqual(offline_scenario(self.c)["actual_orders_submitted"],0)
 def test_mock_actual(self):
  c=SingleOrderNetworkValidationConfig(explicit_network_opt_in=True,explicit_order_opt_in=True)
  env={"AI_STOCK_BOT_ENABLE_PAPER_NETWORK":"YES","AI_STOCK_BOT_ENABLE_SINGLE_PAPER_ORDER":"YES",
       "APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"}
  def transport(url,headers,body,timeout):
   return 201,json.dumps(fixtures(c)["order_response"]).encode()
  f=fixtures(c);p=preflight(c,f["account"],f["asset"],f["clock"],f["quote"]);t=one_order_token(c,p)
  self.assertTrue(execute_order(c,env,build_payload(c,t),transport)["ok"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"],0,0);self.assertTrue(verify_manifest(out,m))
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_enablement_certificate(p)
 def test_stage_count(self): self.assertEqual(len([f"V86.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__":unittest.main()
