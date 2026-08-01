from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.live_broker_final_cert_v84_81_v85_00 import *

class T(unittest.TestCase):
 def setUp(self): self.c=LiveBrokerFinalCertificationConfig()
 def test_config(self): self.c.validate()
 def test_network_rejected(self):
  with self.assertRaises(ValueError): LiveBrokerFinalCertificationConfig(allow_network=True).validate()
 def test_cert_count(self): self.assertEqual(len(CERTS),4)
 def test_chain(self):
  ch={"certificate_count":4,"certificates":[{"stage":s,"status":"PASS","certificate_sha256":str(i)} for i,s in enumerate(["V84.20","V84.40","V84.60","V84.80"])]}
  self.assertEqual(validate_chain(ch,self.c)["status"],"PASS")
 def test_rollback(self): self.assertTrue(rollback_plan()["manual_action_required"])
 def test_compliance(self): self.assertEqual(compliance_report({"stage":"x","status":"PASS"})["status"],"PASS")
 def test_readiness(self): self.assertEqual(release_readiness({"status":"PASS"},rollback_plan())["status"],"PASS")
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
 def test_archive(self): self.assertTrue(archive_descriptor({"manifest_sha256":"a"*64})["immutable"])
 def test_bad_cert(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c";p.write_text("{}")
   with self.assertRaises(ValueError):validate_cert(p,"V84.80","x")
 def test_safety(self):
  s=(Path(__file__).resolve().parents[1]/"alpaca_market_data/live_broker_final_cert_v84_81_v85_00.py").read_text().lower()
  for x in ("submit_order(","tradingclient(","api_secret","api_key","os.getenv","requests.","httpx."): self.assertNotIn(x,s)
 def test_stage_count(self): self.assertEqual(len([f"V84.{i:02d}" for i in range(81,100)]+["V85.00"]),20)
if __name__=="__main__": unittest.main()
