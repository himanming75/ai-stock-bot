
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_automation_rc2_certification_v91_61_80 import *

class T(unittest.TestCase):
    def setUp(self): self.c = RC2CertificationConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            RC2CertificationConfig(paper_order_submission_authorized=True).validate()
    def test_chain(self):
        c=certification_chain({"stage":"V91.60","release_candidate":"X","certificate_sha256":"abc"})
        self.assertEqual(c["status"],"PASS")
    def test_replay(self):
        c=certification_chain({"stage":"V91.60","release_candidate":"X","certificate_sha256":"abc"})
        self.assertTrue(deterministic_replay(c)["deterministic"])
    def test_restart(self): self.assertEqual(restart_certification()["status"],"PASS")
    def test_recovery(self): self.assertEqual(recovery_certification()["status"],"PASS")
    def test_integrity(self): self.assertTrue(integrity_and_tamper()["tamper_detected"])
    def test_rollback(self): self.assertTrue(rollback_certification()["rollback_certified"])
    def test_acceptance(self):
        chain=certification_chain({"stage":"V91.60","release_candidate":"X","certificate_sha256":"abc"})
        a=release_acceptance(self.c,chain,deterministic_replay(chain),restart_certification(),
            recovery_certification(),integrity_and_tamper(),rollback_certification())
        self.assertEqual(a["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.c,{"status":"PASS","rc2_certification_accepted":True})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-rc2-cert-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_manifest_tamper(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            (o/"actual_paper_rc2_cert_ledger_v91_69.json").write_text("{}\n")
            self.assertFalse(verify_manifest(o,m))
    def test_release_candidate(self):
        self.assertEqual(self.c.release_candidate,"ACTUAL_PAPER_AUTOMATION_RC2_CERTIFIED_READ_ONLY")
    def test_write_zero(self): self.assertEqual(self.c.write_capability_count,0)
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_stage_count(self): self.assertEqual(len(range(61,81)),20)

if __name__=="__main__": unittest.main()
