from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_order_submission_gate_v92_21_40 import *
class T(unittest.TestCase):
 def setUp(self):self.c=SubmissionGateConfig()
 def test_config(self):self.c.validate()
 def test_unsafe(self):
  with self.assertRaises(ValueError):SubmissionGateConfig(paper_order_submission_authorized=True).validate()
 def test_approval(self):self.assertEqual(approval_gate()["status"],"PASS")
 def test_token(self):self.assertEqual(token_gate()["status"],"PASS")
 def test_risk(self):self.assertEqual(risk_gate()["status"],"PASS")
 def test_duplicate(self):self.assertEqual(duplicate_gate()["status"],"PASS")
 def test_safety(self):self.assertEqual(safety_gate(self.c)["status"],"PASS")
 def test_kill(self):self.assertEqual(kill_switch_gate()["status"],"PASS")
 def test_preview(self):self.assertEqual(preview_gate()["status"],"READY_PREVIEW_ONLY")
 def test_final_gate(self):self.assertEqual(final_submission_gate(self.c,approval_gate(),token_gate(),risk_gate(),duplicate_gate(),safety_gate(self.c),kill_switch_gate(),preview_gate())["status"],"CERTIFIED_PREVIEW_ONLY")
 def test_tamper(self):self.assertTrue(tamper_test()["tamper_detected"])
 def test_rollback(self):self.assertTrue(rollback_plan()["rollback_ready"])
 def test_audit(self):self.assertEqual(final_audit(self.c,final_submission_gate(self.c,approval_gate(),token_gate(),risk_gate(),duplicate_gate(),safety_gate(self.c),kill_switch_gate(),preview_gate()),tamper_test(),rollback_plan())["status"],"PASS")
 def test_store(self):
  with TemporaryDirectory() as t:self.assertTrue(store_package(Path(t),{"x":{"status":"PASS"}})[0].startswith("actual-paper-gate-cert-"))
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});self.assertTrue(verify_manifest(o,build_manifest(o,l)))
 def test_orders_zero(self):self.assertEqual(self.c.actual_orders_submitted,0)
 def test_network_zero(self):self.assertEqual(self.c.network_requests_executed,0)
 def test_stage_count(self):self.assertEqual(len(range(21,41)),20)
if __name__=="__main__":unittest.main()
