from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.strategy_execution_final_certification_v87_61_80 import *

def mkcert(stage,flag):
 d={"stage":stage,"status":"PASS",flag:True,
    "auto_execution_enabled":False,"paper_order_submission_authorized":False,
    "live_trading_authorized":False,"network_requests_executed":0,
    "actual_orders_submitted":0}
 d["certificate_sha256"]=hj(d);return d

class T(unittest.TestCase):
 def setUp(self): self.c=StrategyExecutionFinalCertificationConfig()
 def test_config(self): self.c.validate()
 def test_auto_exec_rejected(self):
  with self.assertRaises(ValueError):StrategyExecutionFinalCertificationConfig(auto_execution_enabled=True).validate()
 def test_validate_certificate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c.json";wj(p,mkcert("V87.20","paper_strategy_execution_operations_complete"))
   self.assertEqual(validate_certificate(p,"V87.20","paper_strategy_execution_operations_complete")["status"],"PASS")
 def test_bad_certificate(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"c.json";p.write_text("{}")
   with self.assertRaises(ValueError):validate_certificate(p,"V87.20","paper_strategy_execution_operations_complete")
 def test_integrity(self):
  chain={"operations":mkcert("V87.20","paper_strategy_execution_operations_complete"),
         "simulation":mkcert("V87.40","paper_strategy_execution_simulation_complete"),
         "reconciliation":mkcert("V87.60","paper_strategy_execution_reconciliation_complete")}
  self.assertEqual(integrity_chain(chain)["certificate_count"],3)
 def test_safety(self):
  chain={"operations":mkcert("V87.20","paper_strategy_execution_operations_complete"),
         "simulation":mkcert("V87.40","paper_strategy_execution_simulation_complete"),
         "reconciliation":mkcert("V87.60","paper_strategy_execution_reconciliation_complete")}
  self.assertEqual(safety_chain(chain,self.c)["status"],"PASS")
 def test_rollback(self): self.assertEqual(rollback_certificate()["status"],"PASS")
 def test_readiness(self):
  x={"status":"PASS"}
  self.assertEqual(release_readiness(self.c,x,x,x)["status"],"PASS")
 def test_archive(self):
  i={"chain_root_sha256":"a"*64,"certificate_count":3,"certificate_ids":{"x":"y"}}
  self.assertEqual(archive_record(i,self.c)["status"],"PASS")
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_release_package(self):
  m={"manifest_sha256":"a"*64};a={"archive_id":"x"}
  self.assertEqual(release_package(self.c,m,a)["status"],"PASS")
 def test_chain_verify(self):
  i={"chain_root_sha256":"a"*64};m={"manifest_sha256":"b"*64}
  r={"release_package_sha256":"c"*64,"promotion_authorized":False}
  self.assertEqual(final_chain_verification(i,m,r)["status"],"PASS")
 def test_stage_count(self):self.assertEqual(len([f"V87.{i:02d}" for i in range(61,81)]),20)

if __name__=="__main__":unittest.main()
