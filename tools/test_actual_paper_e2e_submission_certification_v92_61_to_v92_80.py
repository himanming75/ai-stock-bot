
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_e2e_submission_certification_v92_61_80 import *

class T(unittest.TestCase):
    def setUp(self): self.c=E2ECertificationConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            E2ECertificationConfig(paper_order_submission_authorized=True).validate()
    def test_flow(self): self.assertEqual(e2e_flow()["status"],"PASS")
    def test_idempotency(self): self.assertTrue(idempotency_certification()["deterministic"])
    def test_reconciliation(self): self.assertEqual(reconciliation_certification()["status"],"PASS")
    def test_containment(self): self.assertEqual(failure_containment()["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_certification()["rollback_certified"])
    def test_tamper(self): self.assertTrue(tamper_detection()["tamper_detected"])
    def test_acceptance(self):
        a=acceptance(self.c,{"certificate_count":4},e2e_flow(),idempotency_certification(),
            reconciliation_certification(),failure_containment(),rollback_certification(),tamper_detection())
        self.assertEqual(a["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.c,{"status":"PASS","e2e_preview_rc_ready":True})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-e2e-cert-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_release_candidate(self):
        self.assertEqual(self.c.release_candidate,"ACTUAL_PAPER_E2E_SUBMISSION_PREVIEW_RC1")
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_write_zero(self): self.assertEqual(self.c.write_capability_count,0)
    def test_stage_count(self): self.assertEqual(len(range(61,81)),20)

if __name__=="__main__": unittest.main()
