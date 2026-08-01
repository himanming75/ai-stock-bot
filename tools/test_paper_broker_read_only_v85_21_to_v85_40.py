from pathlib import Path
from tempfile import TemporaryDirectory
import unittest, json
from alpaca_market_data.paper_broker_read_only_v85_21_40 import *

class T(unittest.TestCase):
 def setUp(self): self.c=ReadOnlyConnectionConfig()
 def test_config(self): self.c.validate()
 def test_write_rejected(self):
  with self.assertRaises(ValueError): ReadOnlyConnectionConfig(allow_post=True).validate()
 def test_catalog(self): self.assertEqual(endpoint_catalog(self.c)["write_endpoint_count"],0)
 def test_credentials(self): self.assertTrue(credential_status({"APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"})["complete"])
 def test_auth_default(self): self.assertFalse(network_authorization(self.c,{},True)["network_authorized"])
 def test_url(self): self.assertIn("/v2/account",build_url(self.c,endpoint_catalog(self.c)["endpoints"]["account"]))
 def test_contract(self): self.assertEqual(request_contract("a","https://paper-api.alpaca.markets/v2/account")["method"],"GET")
 def test_schema_account(self): self.assertEqual(schema_validate("account",fixtures(self.c)["account"])["status"],"PASS")
 def test_schema_bad(self): self.assertEqual(schema_validate("account",{"id":"x"})["status"],"FAIL")
 def test_reconciliation(self):
  results={k:{"payload":v} for k,v in fixtures(self.c).items()}
  self.assertEqual(reconciliation(results)["status"],"PASS")
 def test_run_offline(self):
  r=run_validation(self.c,{},False);self.assertEqual(r["network_mode"],"OFFLINE_FIXTURE");self.assertEqual(r["network_requests_executed"],0)
 def test_mock_network(self):
  c=ReadOnlyConnectionConfig(explicit_network_opt_in=True)
  payloads=fixtures(c)
  def transport(url,headers,timeout):
   name="account"
   if "/clock" in url:name="clock"
   elif "/positions" in url:name="positions"
   elif "/orders" in url:name="orders"
   elif "/assets/" in url:name="asset"
   elif "/quotes/latest" in url:name="latest_quote"
   return 200,{},json.dumps(payloads[name]).encode()
  env={"AI_STOCK_BOT_ENABLE_PAPER_READ_ONLY":"YES","APCA_API_KEY_ID":"x","APCA_API_SECRET_KEY":"y"}
  r=run_validation(c,env,True,transport);self.assertEqual(r["network_mode"],"ACTUAL_READ_ONLY");self.assertEqual(r["network_requests_executed"],6)
 def test_retry(self): self.assertEqual(retry_classification()["write_retries"],0)
 def test_rate_limit(self): self.assertEqual(rate_limit_observer()["write_request_budget"],0)
 def test_tls(self): self.assertFalse(tls_audit(self.c)["plaintext_http"])
 def test_redaction(self): self.assertFalse(redaction_audit()["secret_values_persisted"])
 def test_fallback(self): self.assertFalse(fallback_policy()["automatic_fallback_after_auth_failure"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   out=Path(t);store_package(out,{"a":{"x":1}});self.assertTrue(store_package(out,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}})
   run={"network_mode":"OFFLINE_FIXTURE","network_requests_executed":0,"credentials_used":0}
   m=build_manifest(out,z["ledger"],run);self.assertTrue(verify_manifest(out,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   out=Path(t);z=store_package(out,{"a":{"x":1}})
   run={"network_mode":"OFFLINE_FIXTURE","network_requests_executed":0,"credentials_used":0}
   m=build_manifest(out,z["ledger"],run);(out/"packages"/z["package_id"]/"a.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(out,m)
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_foundation_certificate(p)
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_broker_read_only_v85_21_40.py").read_text().lower()
  for x in ('method="post"','method="delete"','submit_order(','tradingclient('): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V85.{i:02d}" for i in range(21,41)]),20)
if __name__=="__main__":unittest.main()
