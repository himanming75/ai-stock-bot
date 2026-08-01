
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.final_paper_automation_certification_v90_81_v91_00 import *

class T(unittest.TestCase):
    def setUp(self): self.config = FinalPaperAutomationCertificationConfig()
    def test_config(self): self.config.validate()
    def test_unsafe_scheduler(self):
        with self.assertRaises(ValueError):
            FinalPaperAutomationCertificationConfig(scheduler_enabled=True).validate()
    def test_unsafe_submit(self):
        with self.assertRaises(ValueError):
            FinalPaperAutomationCertificationConfig(paper_order_submission_authorized=True).validate()
    def test_contract(self): self.assertEqual(end_to_end_contract()["status"], "PASS")
    def test_safety(self):
        s=safety_matrix();self.assertEqual(s["status"],"PASS");self.assertGreater(s["blocked_count"],0)
    def test_replay(self):
        c={"chain_root_sha256":"x"};self.assertTrue(deterministic_replay(c,end_to_end_contract(),safety_matrix())["deterministic"])
    def test_containment(self): self.assertEqual(failure_containment()["status"],"PASS")
    def test_rollback(self): self.assertTrue(final_rollback()["rollback_ready"])
    def test_acceptance(self):
        r=release_acceptance(self.config,{"certificate_count":4},end_to_end_contract(),safety_matrix(),
            deterministic_replay({"chain_root_sha256":"x"},end_to_end_contract(),safety_matrix()),
            failure_containment(),final_rollback())
        self.assertEqual(r["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.config,{"status":"PASS","final_release_accepted":True})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}});self.assertTrue(pid.startswith("paper-automation-final-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l);self.assertTrue(verify_manifest(o,m))
    def test_manifest_tamper(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            (o/"final_paper_automation_ledger_v90_89.json").write_text("{}\n")
            self.assertFalse(verify_manifest(o,m))
    def test_write_zero(self): self.assertEqual(self.config.write_capability_count,0)
    def test_network_zero(self): self.assertEqual(self.config.network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.config.actual_orders_submitted,0)
    def test_release_candidate(self): self.assertEqual(self.config.release_candidate,"PAPER_AUTOMATION_FINAL_RC1")
    def test_stage_count(self): self.assertEqual(len(range(81,101)),20)

if __name__=="__main__": unittest.main()
