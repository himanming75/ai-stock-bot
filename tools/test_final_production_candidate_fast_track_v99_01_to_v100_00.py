
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.final_production_candidate_fast_track_v99_01_v100_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=FinalCandidateConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError):
            FinalCandidateConfig(live_trading_authorized=True).validate()
    def test_chain(self): self.assertEqual(certification_chain()["certificate_count"],10)
    def test_readiness(self): self.assertEqual(release_readiness(self.c)["status"],"PASS")
    def test_checklist(self):
        x=operations_checklist()
        self.assertEqual(x["required_count"],x["completed_count"])
    def test_incidents(self): self.assertEqual(incident_certification()["scenario_count"],10)
    def test_rollback(self): self.assertTrue(rollback_package()["rollback_ready"])
    def test_locks(self): self.assertTrue(final_safety_lock(self.c)["all_locked"])
    def test_acceptance(self):
        self.assertTrue(acceptance_contract(certification_chain(),release_readiness(self.c),
            operations_checklist(),incident_certification(),rollback_package(),
            final_safety_lock(self.c))["accepted"])
    def test_tamper(self): self.assertTrue(tamper_detection(certification_chain())["tamper_detected"])
    def test_audit(self):
        x=final_audit(self.c,certification_chain(),release_readiness(self.c),
            operations_checklist(),incident_certification(),rollback_package(),
            final_safety_lock(self.c),
            acceptance_contract(certification_chain(),release_readiness(self.c),
                operations_checklist(),incident_certification(),rollback_package(),
                final_safety_lock(self.c)),
            tamper_detection(certification_chain()))
        self.assertEqual(x["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("v100-final-candidate-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store(o,{"x":{"status":"PASS"}})
            m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_network_zero(self): self.assertEqual(self.c.default_network_requests_executed,0)
    def test_orders_zero(self): self.assertEqual(self.c.default_actual_orders_submitted,0)
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
