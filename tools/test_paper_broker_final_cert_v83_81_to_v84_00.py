from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.paper_broker_final_cert_v83_81_v84_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperBrokerFinalCertificationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError):PaperBrokerFinalCertificationConfig(allow_network=True).validate()
 def test_chain_count(self): self.assertEqual(len(CERTS),5)
 def test_chain_validation(self):
  chain={"certificate_count":5,"certificates":[{"stage":s,"status":"PASS","certificate_sha256":str(i)} for i,s in enumerate(["V83.00","V83.20","V83.40","V83.60","V83.80"])]}
  self.assertEqual(chain_validation(chain,self.c)["status"],"PASS")
 def test_rollback(self): self.assertTrue(rollback_plan()["manual_action_required"])
 def test_release_readiness(self):
  self.assertEqual(release_readiness({"status":"PASS","paper_framework_compliant":True},rollback_plan())["status"],"PASS")
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
 def test_archive(self):
  m={"manifest_sha256":"a"*64};self.assertTrue(archive_descriptor(m)["immutable"])
 def test_report(self):
  d=final_report({"paper_framework_compliant":True},{"release_candidate":"RC1"},{"status":"PASS"},{"status":"PASS"})
  self.assertEqual(d["status"],"PASS")
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_certificate(p,"V83.80","x")
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/paper_broker_final_cert_v83_81_v84_00.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."):self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V83.{i:02d}" for i in range(81,100)]+["V84.00"]),20)
if __name__=="__main__":unittest.main()
