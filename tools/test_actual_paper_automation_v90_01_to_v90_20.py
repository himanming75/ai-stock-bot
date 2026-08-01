
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_automation_v90_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=ActualPaperAutomationConfig()
 def test_config(self): self.c.validate()
 def test_live_url_rejected(self):
  with self.assertRaises(ValueError): ActualPaperAutomationConfig(base_url="https://api.alpaca.markets").validate()
 def test_catalog(self):
  x=endpoint_catalog(self.c);self.assertEqual(x["write_capability_count"],0)
 def test_credentials_missing(self): self.assertFalse(credentials_from_env(self.c,{})["present"])
 def test_credentials_redacted(self):
  x=credentials_from_env(self.c,{"APCA_API_KEY_ID":"1234567890","APCA_API_SECRET_KEY":"secret"})
  self.assertTrue(x["present"]);self.assertNotEqual(x["redacted_key"],x["api_key"])
 def test_optin(self): self.assertTrue(network_opted_in(self.c,{self.c.network_opt_in_env:"YES"}))
 def test_headers(self):
  c={"present":True,"api_key":"k","api_secret":"s"};self.assertIn("APCA-API-KEY-ID",build_headers(c))
 def test_get_only(self):
  with self.assertRaises(ValueError): validate_request("POST",self.c.base_url+"/v2/orders",self.c)
 def test_order_get_blocked(self):
  with self.assertRaises(ValueError): validate_request("GET",self.c.base_url+"/v2/orders/x",self.c)
 def test_account_read(self):
  c={"present":True,"api_key":"k","api_secret":"s"}
  self.assertEqual(read_endpoint(self.c,"account",c,mock_transport)["status"],"PASS")
 def test_clock_read(self):
  c={"present":True,"api_key":"k","api_secret":"s"}
  self.assertEqual(read_endpoint(self.c,"clock",c,mock_transport)["status"],"PASS")
 def test_calendar_read(self):
  c={"present":True,"api_key":"k","api_secret":"s"}
  self.assertEqual(read_endpoint(self.c,"calendar",c,mock_transport)["status"],"PASS")
 def test_account_schema(self):
  x=mock_transport("GET",self.c.base_url+"/v2/account",{},1)["body"]
  self.assertEqual(validate_account(x)["status"],"PASS")
 def test_clock_schema(self):
  x=mock_transport("GET",self.c.base_url+"/v2/clock",{},1)["body"]
  self.assertEqual(validate_clock(x)["status"],"PASS")
 def test_calendar_schema(self):
  x=mock_transport("GET",self.c.base_url+"/v2/calendar?start=x",{},1)["body"]
  self.assertEqual(validate_calendar(x)["status"],"PASS")
 def test_offline(self): self.assertEqual(offline_scenario(self.c)["status"],"PASS")
 def test_actual_requires_optin(self):
  with self.assertRaises(ValueError): actual_read_scenario(self.c,{})
 def test_actual_mock(self):
  env={self.c.network_opt_in_env:"YES",self.c.api_key_env:"k",self.c.api_secret_env:"s"}
  self.assertEqual(actual_read_scenario(self.c,env,mock_transport)["status"],"PASS")
 def test_safety(self): self.assertEqual(safety_tests(self.c)["status"],"PASS")
 def test_store(self):
  with TemporaryDirectory() as t:
   pid,_=store(Path(t),{"x":{"a":1}});self.assertTrue(pid.startswith("actual-paper-read-foundation-"))
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);_,l=store(o,{"x":{"a":1}});self.assertEqual(manifest(o,l)["status"],"PASS")

if __name__=="__main__": unittest.main()
