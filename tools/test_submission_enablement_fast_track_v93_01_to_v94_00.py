
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.submission_enablement_fast_track_v93_01_v94_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=FastTrackConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError): FastTrackConfig(paper_order_submission_authorized=True).validate()
    def test_request(self): self.assertEqual(enablement_request()["status"],"PENDING")
    def test_approvals(self): self.assertEqual(approvals(enablement_request())["approval_count"],2)
    def test_session(self):
        r=enablement_request(); a=approvals(r)
        self.assertEqual(session(self.c,r,a)["status"],"ACTIVE")
    def test_intent(self): self.assertEqual(order_intent(self.c)["validation_status"],"PASS")
    def test_adapter(self):
        r=enablement_request();a=approvals(r);s=session(self.c,r,a)
        self.assertFalse(adapter_preview(order_intent(self.c),s)["network_request_executed"])
    def test_mock(self):
        r=enablement_request();a=approvals(r);s=session(self.c,r,a)
        self.assertEqual(mock_execution(adapter_preview(order_intent(self.c),s))["status"],"PASS")
    def test_reconcile(self):
        r=enablement_request();a=approvals(r);s=session(self.c,r,a);i=order_intent(self.c)
        self.assertEqual(reconcile(i,mock_execution(adapter_preview(i,s)))["status"],"PASS")
    def test_safety(self): self.assertEqual(safety_and_recovery(self.c)["status"],"PASS")
    def test_integrated(self): self.assertEqual(integrated(self.c)["status"],"PASS")
    def test_tamper(self): self.assertTrue(tamper()["tamper_detected"])
    def test_rollback(self): self.assertTrue(rollback()["rollback_ready"])
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("submission-fast-track-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store(o,{"x":{"status":"PASS"}});m=manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_limits(self):
        self.assertEqual(self.c.max_order_notional,100.0)
        self.assertEqual(self.c.max_quantity,1)
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
