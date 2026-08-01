
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.multi_session_validation_fast_track_v98_01_v99_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=MultiSessionConfig()
    def test_config(self): self.c.validate()
    def test_queue(self): self.assertEqual(build_queue(self.c)["queue_depth"],3)
    def test_activate(self): self.assertEqual(activate_next(build_queue(self.c))["status"],"ACTIVE")
    def test_active_block(self):
        q=build_queue(self.c);a=activate_next(q)
        self.assertEqual(activate_next(a["queue"],a["active_session"])["status"],"BLOCKED_ACTIVE_SESSION")
    def test_isolation(self):
        a=activate_next(build_queue(self.c))
        self.assertEqual(session_isolation(a["active_session"],a["queue"])["status"],"PASS")
    def test_heartbeat(self):
        a=activate_next(build_queue(self.c))
        self.assertEqual(heartbeat(a["active_session"],a["active_session"]["activated_at"]+30)["status"],"HEALTHY")
    def test_rotate(self):
        a=activate_next(build_queue(self.c))
        self.assertEqual(rotate_token(a["active_session"])["status"],"ROTATED")
    def test_complete(self):
        a=activate_next(build_queue(self.c))
        self.assertEqual(complete_active(a["active_session"])["status"],"CLOSED")
    def test_cleanup(self):
        a=activate_next(build_queue(self.c))
        self.assertGreaterEqual(cleanup_expired(a["queue"],1_000_400)["expired_count"],1)
    def test_arbitration(self):
        a=activate_next(build_queue(self.c))
        self.assertEqual(arbitration(a["active_session"],a["queue"]["sessions"][0])["status"],"BLOCKED_CONCURRENT")
    def test_recovery(self): self.assertEqual(recovery_matrix()["scenario_count"],7)
    def test_audit(self): self.assertEqual(audit_chain([{"x":1},{"x":2}])["record_count"],2)
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_offline(self): self.assertEqual(offline_certification(self.c)["status"],"PASS")
    def test_safety(self): self.assertEqual(default_safety(self.c)["status"],"PASS")
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store(o,{"x":{"status":"PASS"}});m=manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
