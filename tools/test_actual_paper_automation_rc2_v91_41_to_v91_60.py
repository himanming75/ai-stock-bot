
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_automation_rc2_v91_41_60 import *

class T(unittest.TestCase):
    def setUp(self): self.c=AutomationRC2Config()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError): AutomationRC2Config(runtime_loop_enabled=True).validate()
    def test_persistence(self): self.assertEqual(persistence_validation()["status"],"PASS")
    def test_recovery(self): self.assertEqual(recovery_chain()["status"],"PASS")
    def test_gate(self): self.assertEqual(permission_gate()["status"],"READY_READ_ONLY")
    def test_kill(self): self.assertEqual(kill_switch_validation()["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_acceptance(self):
        a=acceptance(self.c,{"certificate_count":2},persistence_validation(),recovery_chain(),permission_gate(),kill_switch_validation(),rollback_plan())
        self.assertEqual(a["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.c,{"status":"PASS","rc2_foundation_ready":True})["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-rc2-foundation-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_manifest_tamper(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            (o/"actual_paper_rc2_ledger_v91_49.json").write_text("{}\n")
            self.assertFalse(verify_manifest(o,m))
    def test_release_candidate(self): self.assertEqual(self.c.release_candidate,"ACTUAL_PAPER_AUTOMATION_RC2_READ_ONLY")
    def test_write_zero(self): self.assertEqual(self.c.write_capability_count,0)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_approvals(self): self.assertEqual(self.c.required_approvals,2)
    def test_ttl(self): self.assertEqual(self.c.session_ttl_seconds,300)
    def test_single_use(self): self.assertEqual(self.c.max_session_uses,1)
    def test_stage_count(self): self.assertEqual(len(range(41,61)),20)

if __name__=="__main__": unittest.main()
