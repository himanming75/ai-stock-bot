from pathlib import Path
from tempfile import TemporaryDirectory
import unittest, json
from alpaca_market_data.position_account_reconciliation_v86_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PositionAccountReconciliationConfig()
 def test_config(self): self.c.validate()
 def test_get_only(self):
  with self.assertRaises(ValueError): PositionAccountReconciliationConfig(allow_post=True).validate()
 def test_credentials(self): self.assertTrue(credential_status({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_identifier(self): self.assertTrue(identifier_status({"AI_STOCK_BOT_PAPER_ORDER_ID":"x"})["valid"])
 def test_opt_in(self): self.assertFalse(opt_in(self.c,{},True)["allowed"])
 def test_urls(self): self.assertIn("/v2/orders/",endpoint_urls(self.c,{"AI_STOCK_BOT_PAPER_ORDER_ID":"x"})["order"])
 def test_order_metrics(self): self.assertEqual(order_metrics(fixtures()["order"])["filled_notional"],200.0)
 def test_position_lookup(self): self.assertEqual(find_position("AAPL",fixtures()["positions"])["matching_count"],1)
 def test_quantity(self):
  f=fixtures();m=order_metrics(f["order"]);l=find_position("AAPL",f["positions"])
  self.assertEqual(quantity_reconciliation(m,l,self.c)["status"],"PASS")
 def test_average_price(self):
  f=fixtures();m=order_metrics(f["order"]);l=find_position("AAPL",f["positions"])
  self.assertEqual(average_price_reconciliation(m,l,self.c)["status"],"PASS")
 def test_market_value(self):
  self.assertEqual(market_value_reconciliation(find_position("AAPL",fixtures()["positions"]),self.c)["status"],"PASS")
 def test_unrealized_pnl(self):
  self.assertEqual(unrealized_pnl_reconciliation(find_position("AAPL",fixtures()["positions"]),self.c)["status"],"PASS")
 def test_account_schema(self): self.assertEqual(account_schema(fixtures()["account"])["status"],"PASS")
 def test_account_numeric(self): self.assertEqual(account_numeric_reconciliation(fixtures()["account"],self.c)["status"],"PASS")
 def test_evaluate(self):
  f=fixtures();self.assertEqual(evaluate(self.c,f["order"],f["account"],f["positions"])["status"],"PASS")
 def test_offline(self): self.assertEqual(offline_run(self.c)["network_requests_executed"],0)
 def test_mock_actual(self):
  env={"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y","AI_STOCK_BOT_PAPER_ORDER_ID":"o"}
  f=fixtures()
  def tr(url,headers,timeout):
   payload=f["order"] if "/orders/" in url else f["account"] if url.endswith("/account") else f["positions"]
   return 200,json.dumps(payload).encode()
  self.assertEqual(actual_run(self.c,env,tr)["network_requests_executed"],3)
 def test_rollback(self): self.assertFalse(rollback_plan()["new_order_submission"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError): validate_source(p)
 def test_stage_count(self): self.assertEqual(len([f"V86.{i:02d}" for i in range(41,61)]),20)

if __name__=="__main__": unittest.main()
