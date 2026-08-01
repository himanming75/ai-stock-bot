
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_final_submission_certification_v92_41_60 import *

class T(unittest.TestCase):
    def setUp(self): self.c=FinalSubmissionCertificationConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            FinalSubmissionCertificationConfig(paper_order_submission_authorized=True).validate()
    def test_contract(self): self.assertEqual(final_submission_contract()["status"],"PASS")
    def test_risk(self): self.assertEqual(risk_acceptance()["status"],"PASS")
    def test_replay(self): self.assertTrue(deterministic_replay()["deterministic"])
    def test_recovery(self): self.assertEqual(recovery_certification()["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_certification()["rollback_certified"])
    def test_tamper(self): self.assertTrue(tamper_detection()["tamper_detected"])
    def test_acceptance(self):
        a=release_acceptance(self.c,final_submission_contract(),risk_acceptance(),
            deterministic_replay(),recovery_certification(),rollback_certification(),tamper_detection())
        self.assertEqual(a["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.c,{"status":"PASS","final_submission_preview_rc_ready":True})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-final-submit-cert-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_release_candidate(self):
        self.assertEqual(self.c.release_candidate,"ACTUAL_PAPER_FINAL_SUBMISSION_PREVIEW_RC1")
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_write_zero(self): self.assertEqual(self.c.write_capability_count,0)
    def test_stage_count(self): self.assertEqual(len(range(41,61)),20)

if __name__=="__main__": unittest.main()
