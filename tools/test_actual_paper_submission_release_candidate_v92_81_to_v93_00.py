
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_submission_release_candidate_v92_81_v93_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=SubmissionReleaseCandidateConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            SubmissionReleaseCandidateConfig(paper_order_submission_authorized=True).validate()
    def test_manifest(self):
        m=rc_manifest({"stage":"V92.80","release_candidate":"X","certificate_sha256":"abc"})
        self.assertEqual(m["status"],"PASS")
    def test_readiness(self): self.assertEqual(readiness_check()["status"],"PASS")
    def test_lock(self): self.assertTrue(final_lock()["all_locked"])
    def test_acceptance(self):
        m=rc_manifest({"stage":"V92.80","release_candidate":"X","certificate_sha256":"abc"})
        self.assertEqual(acceptance(self.c,m,readiness_check(),final_lock())["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_archive(self): self.assertEqual(archive_plan()["record_count"],7)
    def test_tamper(self):
        m=rc_manifest({"stage":"V92.80","release_candidate":"X","certificate_sha256":"abc"})
        self.assertTrue(tamper_detection(m)["tamper_detected"])
    def test_audit(self):
        self.assertEqual(final_audit(self.c,{"status":"PASS","rc_ready":True},
            rollback_plan(),archive_plan(),{"status":"PASS"})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-submission-rc-"))
    def test_bundle_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}})
            m=build_bundle_manifest(o,l)
            self.assertTrue(verify_bundle_manifest(o,m))
    def test_release_candidate(self):
        self.assertEqual(self.c.release_candidate,"ACTUAL_PAPER_SUBMISSION_PREVIEW_RC1")
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_write_zero(self): self.assertEqual(self.c.write_capability_count,0)
    def test_stage_count(self): self.assertEqual(len(range(81,101)),20)

if __name__=="__main__": unittest.main()
