from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.broker_read_only_v82_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=BrokerReadOnlyConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):BrokerReadOnlyConfig(allow_network=True).validate()
 def test_contract(self):
  d=capability_contract();self.assertGreater(d["read_capability_count"],0);self.assertEqual(d["write_capability_count"],0)
 def test_account(self): self.assertEqual(validate_account(account_fixture())["status"],"PASS")
 def test_positions(self): self.assertEqual(validate_positions(positions_fixture())["status"],"PASS")
 def test_orders(self): self.assertEqual(validate_orders(orders_fixture())["status"],"PASS")
 def test_clock(self): self.assertEqual(validate_clock(clock_fixture())["status"],"PASS")
 def test_assets(self): self.assertEqual(validate_assets(assets_fixture())["status"],"PASS")
 def test_market_data(self): self.assertEqual(validate_market_data(market_data_fixture())["status"],"PASS")
 def test_reconcile(self): self.assertIn("implied_equity",reconcile(account_fixture(),positions_fixture(),market_data_fixture()))
 def test_health(self):
  vals=[validate_account(account_fixture()),validate_positions(positions_fixture()),validate_orders(orders_fixture()),validate_clock(clock_fixture()),validate_assets(assets_fixture()),validate_market_data(market_data_fixture())]
  self.assertEqual(sync_health(vals)["status"],"PASS")
 def test_bad_position(self):
  bad=positions_fixture();bad[0]["market_value"]=1
  self.assertEqual(validate_positions(bad)["status"],"FAIL")
 def test_bad_order_status(self):
  bad=orders_fixture();bad[0]["status"]="UNKNOWN"
  self.assertEqual(validate_orders(bad)["status"],"FAIL")
 def test_bad_quote(self):
  bad=market_data_fixture();bad[0]["ask"]=1
  self.assertEqual(validate_market_data(bad)["status"],"FAIL")
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
   with self.assertRaises(ValueError):validate_live_safety_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/broker_read_only_v82_21_40.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V82.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
