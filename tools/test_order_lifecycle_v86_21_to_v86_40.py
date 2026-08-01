from pathlib import Path
from tempfile import TemporaryDirectory
import unittest,json
from alpaca_market_data.order_lifecycle_v86_21_40 import *
class T(unittest.TestCase):
 def setUp(self):self.c=LifecycleConfig()
 def test_config(self):self.c.validate()
 def test_get_only(self):
  with self.assertRaises(ValueError):LifecycleConfig(allow_delete=True).validate()
 def test_credentials(self):self.assertTrue(credential_status({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_identifier(self):self.assertTrue(identifier_status({"AI_STOCK_BOT_PAPER_ORDER_ID":"x"})["valid"])
 def test_optin(self):self.assertFalse(opt_in(self.c,{},True)["allowed"])
 def test_urls(self):self.assertIn("/v2/orders/",urls(self.c,{"AI_STOCK_BOT_PAPER_ORDER_ID":"x"})["order"])
 def test_schema(self):self.assertEqual(order_schema(fixtures()["order"])["status"],"PASS")
 def test_lifecycle(self):self.assertEqual(lifecycle(fixtures()["order"])["classification"],"TERMINAL")
 def test_position(self):self.assertEqual(position_reconcile(fixtures()["order"],fixtures()["positions"])["status"],"PASS")
 def test_account(self):self.assertEqual(account_reconcile(fixtures()["account"])["status"],"PASS")
 def test_evaluate(self):self.assertEqual(evaluate(fixtures()["order"],fixtures()["account"],fixtures()["positions"])["status"],"PASS")
 def test_offline(self):self.assertEqual(offline_run()["network_requests_executed"],0)
 def test_mock_actual(self):
  env={"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y","AI_STOCK_BOT_PAPER_ORDER_ID":"o"}
  f=fixtures()
  def tr(url,headers,timeout):
   p=f["order"] if "/orders/" in url else f["account"] if url.endswith("/account") else f["positions"]
   return 200,json.dumps(p).encode()
  self.assertEqual(actual_run(self.c,env,tr)["network_requests_executed"],3)
 def test_rollback(self):self.assertFalse(rollback()["new_order_submission"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self):self.assertEqual(len([f"V86.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
