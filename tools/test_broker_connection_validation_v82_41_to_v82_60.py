from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.broker_connection_validation_v82_41_60 import *

class T(unittest.TestCase):
 def setUp(self): self.c=BrokerConnectionValidationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):BrokerConnectionValidationConfig(allow_network=True).validate()
 def test_endpoint_contract(self): self.assertEqual(endpoint_contract()["write_endpoint_count"],0)
 def test_endpoint_validation(self): self.assertEqual(validate_endpoint_contract(endpoint_contract())["status"],"PASS")
 def test_credentials(self): self.assertEqual(validate_credential_shape(credential_shape_fixture())["status"],"PASS")
 def test_timeout(self): self.assertFalse(timeout_policy(self.c)["network_execution_authorized"])
 def test_retry(self): self.assertEqual(retry_policy(self.c)["maximum_attempts"],3)
 def test_rate_limit(self): self.assertEqual(rate_limit_policy(self.c)["network_requests_executed"],0)
 def test_heartbeat(self): self.assertTrue(heartbeat_fixture()["healthy"])
 def test_schema_count(self): self.assertEqual(response_schema_contract()["schema_count"],6)
 def test_schema_validation(self): self.assertEqual(validate_response_schemas(response_schema_contract(),sample_responses())["status"],"PASS")
 def test_bad_schema(self):
  s=sample_responses();del s["account"]["cash"]
  self.assertEqual(validate_response_schemas(response_schema_contract(),s)["status"],"FAIL")
 def test_error_map(self): self.assertTrue(error_classification()["mapping"]["429"]["retryable"])
 def test_error_validation(self): self.assertEqual(validate_error_classification(error_classification())["status"],"PASS")
 def test_tls(self): self.assertFalse(tls_contract()["plaintext_http_allowed"])
 def test_compatibility(self): self.assertTrue(provider_compatibility(endpoint_contract(),response_schema_contract())["read_only_compatible"])
 def test_health(self):
  vals=[validate_endpoint_contract(endpoint_contract()),validate_credential_shape(credential_shape_fixture()),validate_response_schemas(response_schema_contract(),sample_responses()),validate_error_classification(error_classification())]
  self.assertEqual(connection_health(heartbeat_fixture(),vals)["status"],"PASS")
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
   with self.assertRaises(ValueError):validate_read_only_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/broker_connection_validation_v82_41_60.py").read_text().lower()
  for x in ("submit_order(","cancel_order(","replace_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V82.{i:02d}" for i in range(41,61)]),20)
if __name__=="__main__":unittest.main()
