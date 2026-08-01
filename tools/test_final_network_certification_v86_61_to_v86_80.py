from pathlib import Path
from tempfile import TemporaryDirectory
import unittest, json
from alpaca_market_data.final_network_certification_v86_61_80 import *

def mkcert(stage,flag,extra=None):
 d={"stage":stage,"status":"PASS",flag:True,
    "paper_order_submission_authorized":False,"live_trading_authorized":False,
    "actual_orders_submitted":0}
 if extra:d.update(extra)
 d["certificate_sha256"]=hj(d);return d

class T(unittest.TestCase):
 def setUp(self): self.c=FinalNetworkCertificationConfig()
 def test_config(self): self.c.validate()
 def test_authorization_rejected(self):
  with self.assertRaises(ValueError): FinalNetworkCertificationConfig(live_trading_authorized=True).validate()
 def test_validate_certificate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c.json";wj(p,mkcert("V86.20","paper_single_order_validation_complete"))
   self.assertEqual(validate_certificate(p,"V86.20","paper_single_order_validation_complete")["status"],"PASS")
 def test_bad_certificate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c.json";p.write_text("{}")
   with self.assertRaises(ValueError):validate_certificate(p,"V86.20","paper_single_order_validation_complete")
 def test_classification_offline(self):
  s={"single_order_network_mode":"OFFLINE_FIXTURE","lifecycle_network_mode":"OFFLINE_FIXTURE",
     "position_network_mode":"OFFLINE_FIXTURE","lifecycle_filled_qty":1.0,"position_qty":1.0}
  self.assertEqual(evidence_classification(s)["classification"],"OFFLINE_CERTIFIED")
 def test_classification_unfilled(self):
  s={"single_order_network_mode":"OFFLINE_FIXTURE","lifecycle_network_mode":"ACTUAL_LIFECYCLE_READ",
     "position_network_mode":"ACTUAL_RECONCILIATION_READ","lifecycle_filled_qty":0.0,"position_qty":0.0}
  self.assertEqual(evidence_classification(s)["classification"],"OBSERVED_UNFILLED")
 def test_classification_filled(self):
  s={"single_order_network_mode":"ACTUAL_SINGLE_PAPER_ORDER","lifecycle_network_mode":"ACTUAL_LIFECYCLE_READ",
     "position_network_mode":"ACTUAL_RECONCILIATION_READ","lifecycle_filled_qty":1.0,"position_qty":1.0}
  self.assertEqual(evidence_classification(s)["classification"],"OBSERVED_FILLED")
 def test_integrity(self):
  chain={"single_order":mkcert("V86.20","paper_single_order_validation_complete"),
         "lifecycle":mkcert("V86.40","paper_order_lifecycle_validation_complete"),
         "position_account":mkcert("V86.60","paper_position_account_reconciliation_complete")}
  self.assertEqual(integrity_chain(chain)["certificate_count"],3)
 def test_safety(self):
  chain={"single_order":mkcert("V86.20","paper_single_order_validation_complete"),
         "lifecycle":mkcert("V86.40","paper_order_lifecycle_validation_complete"),
         "position_account":mkcert("V86.60","paper_position_account_reconciliation_complete")}
  self.assertEqual(safety_chain(chain)["status"],"PASS")
 def test_policy(self):
  cl={"classification":"OFFLINE_CERTIFIED","actual_network_evidence":False,"filled_evidence":False}
  self.assertTrue(certification_policy(self.c,cl)["allowed"])
 def test_rollback(self): self.assertEqual(rollback_verification()["status"],"PASS")
 def test_release_candidate(self):
  cl={"classification":"OBSERVED_FILLED"}
  self.assertIn("NETWORK_FILLED",release_candidate(cl)["release_candidate"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_manifest_tamper(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"])
   (o/"final_network_ledger_v86_72.json").write_text("{}")
   with self.assertRaises(ValueError):verify_manifest(o,m)
 def test_stage_count(self):self.assertEqual(len([f"V86.{i:02d}" for i in range(61,81)]),20)

if __name__=="__main__":unittest.main()
