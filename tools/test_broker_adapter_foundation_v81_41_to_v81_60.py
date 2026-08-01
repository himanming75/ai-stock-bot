from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.broker_adapter_foundation_v81_41_60 import *

class Tests(unittest.TestCase):
    def setUp(self):
        self.config = BrokerAdapterConfig()

    def test_config(self): self.config.validate()
    def test_network_rejected(self):
        with self.assertRaises(ValueError): BrokerAdapterConfig(allow_network=True).validate()
    def test_credentials_rejected(self):
        with self.assertRaises(ValueError): BrokerAdapterConfig(allow_credentials=True).validate()
    def test_registry(self): self.assertEqual(capability_registry()["adapter_count"], 3)
    def test_factory(self): self.assertEqual(adapter_factory("sandbox_broker")["adapter_name"], "SANDBOX_BROKER")
    def test_null_broker(self): self.assertFalse(adapter_factory("NULL_BROKER")["capabilities"]["account_read"])
    def test_unknown_adapter(self):
        with self.assertRaises(ValueError): adapter_factory("REAL_BROKER")
    def test_symbol(self): self.assertEqual(symbol_map("brk.b")["broker_symbol"], "BRK-B")
    def test_bad_symbol(self):
        with self.assertRaises(ValueError): symbol_map("")
    def test_market_order(self): self.assertTrue(translate_order({"symbol":"AAPL","side":"BUY","quantity":1})["preview_only"])
    def test_limit_order(self): self.assertEqual(translate_order({"symbol":"AAPL","side":"BUY","quantity":1,"order_type":"LIMIT","limit_price":100})["limit_price"],100.0)
    def test_bad_order(self):
        with self.assertRaises(ValueError): translate_order({"symbol":"AAPL","side":"BUY","quantity":0})
    def test_account(self): self.assertEqual(translate_account({"cash":1,"equity":2})["currency"],"USD")
    def test_bad_account(self):
        with self.assertRaises(ValueError): translate_account({"cash":-1,"equity":2})
    def test_positions(self): self.assertEqual(len(translate_positions([{"symbol":"AAPL","quantity":1,"average_price":100}])),1)
    def test_duplicate_positions(self):
        with self.assertRaises(ValueError): translate_positions([{"symbol":"AAPL","quantity":1,"average_price":100},{"symbol":"AAPL","quantity":2,"average_price":101}])
    def test_orders(self): self.assertEqual(translate_orders([{"adapter_order_id":"x","symbol":"AAPL","status":"FILLED"}])[0]["status"],"FILLED")
    def test_fills(self): self.assertEqual(translate_fills([{"fill_id":"f","adapter_order_id":"x","symbol":"AAPL","quantity":1,"price":100}])[0]["quantity"],1)
    def test_error_mapping(self): self.assertTrue(map_error("timeout")["retryable"])
    def test_retry(self): self.assertEqual(retry_plan("TIMEOUT",self.config)["maximum_attempts"],3)
    def test_no_retry(self): self.assertEqual(retry_plan("BAD_REQUEST",self.config)["maximum_attempts"],0)
    def test_rate_limit(self): self.assertTrue(rate_limit_guard(120,self.config)["allowed"])
    def test_rate_limit_block(self): self.assertFalse(rate_limit_guard(121,self.config)["allowed"])
    def test_snapshot(self): self.assertEqual(build_fixture_snapshot()["actual_orders_submitted"],0)
    def test_audit(self):
        r=capability_registry();a=adapter_factory("SANDBOX_BROKER");s=build_fixture_snapshot()
        self.assertEqual(build_audit(self.config,r,a,s,retry_plan("TIMEOUT",self.config),rate_limit_guard(0,self.config))["status"],"PASS")
    def test_store_reuse(self):
        with TemporaryDirectory() as t:
            out=Path(t);store_package(out,{"a":{"x":1}})
            self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
    def test_manifest(self):
        with TemporaryDirectory() as t:
            out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"])
            self.assertTrue(verify_manifest(out,m))
    def test_manifest_tamper(self):
        with TemporaryDirectory() as t:
            out=Path(t);z=store_package(out,{"a":{"x":1}});m=build_manifest(out,z["ledger"])
            (out/"packages"/z["package_id"]/"a.json").write_text("{}")
            with self.assertRaises(ValueError): verify_manifest(out,m)
    def test_bad_cert(self):
        with TemporaryDirectory() as t:
            p=Path(t)/"cert.json";p.write_text("{}")
            with self.assertRaises(ValueError): validate_multi_asset_certificate(p)
    def test_safety_source(self):
        text=(Path(__file__).resolve().parents[1]/"alpaca_market_data/broker_adapter_foundation_v81_41_60.py").read_text().lower()
        for token in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):
            self.assertNotIn(token,text)
    def test_stage_count(self): self.assertEqual(len([f"V81.{i:02d}" for i in range(41,61)]),20)

if __name__=="__main__": unittest.main()
