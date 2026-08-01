from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_broker_network_foundation_v85_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerNetworkFoundationConfig()
 def test_config(self): self.c.validate()
 def test_bad_endpoint(self):
  with self.assertRaises(ValueError):validate_endpoint("http://paper-api.alpaca.markets","paper-api.alpaca.markets")
 def test_credentials(self): self.assertTrue(inspect_credentials({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_missing_credentials(self): self.assertFalse(inspect_credentials({})["complete"])
 def test_registry(self): self.assertEqual(capability_registry(self.c)["write_capability_count"],0)
 def test_catalog(self): self.assertEqual(endpoint_catalog(self.c)["write_endpoint_count"],0)
 def test_opt_in(self): self.assertFalse(network_opt_in(self.c,True)["network_allowed"])
 def test_plan(self):
  cat=endpoint_catalog(self.c);cred=inspect_credentials({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})
  self.assertFalse(request_plan("account",cat,cred,network_opt_in(self.c,True))["ready_for_network_probe"])
 def test_schemas(self): self.assertEqual(response_schema_catalog()["schema_count"],6)
 def test_validation(self): self.assertEqual(validate_response("orders",[])["status"],"PASS")
 def test_bad_validation(self): self.assertEqual(validate_response("account",{"id":"x"})["status"],"FAIL")
 def test_timeout(self): self.assertFalse(timeout_policy()["infinite_timeout_allowed"])
 def test_retry(self): self.assertFalse(retry_policy()["write_retry_enabled"])
 def test_rate_limit(self): self.assertEqual(rate_limit_policy()["write_requests_per_minute"],0)
 def test_tls(self): self.assertFalse(tls_policy(self.c)["plaintext_http_allowed"])
 def test_redaction(self): self.assertFalse(redaction_policy()["log_request_bodies"])
 def test_fixtures(self): self.assertIn("account",offline_fixtures()["fixtures"])
 def test_scenarios(self): self.assertEqual(validation_scenarios(self.c)["actual_network_requests"],0)
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
   with self.assertRaises(ValueError):validate_live_framework_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_broker_network_foundation_v85_01_20.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","requests.post","urllib.request.urlopen","httpx."): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V85.{i:02d}" for i in range(1,21)]),20)
if __name__=="__main__": unittest.main()
