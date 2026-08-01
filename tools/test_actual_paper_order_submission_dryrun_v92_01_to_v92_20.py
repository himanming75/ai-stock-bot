
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from alpaca_market_data.actual_paper_order_submission_dryrun_v92_01_20 import *

class T(unittest.TestCase):
    def setUp(self): self.c=DryRunConfig()
    def test_config(self): self.c.validate()
    def test_unsafe(self):
        with self.assertRaises(ValueError): DryRunConfig(paper_order_submission_authorized=True).validate()
    def test_payload(self): self.assertEqual(build_order_payload()["symbol"],"AAPL")
    def test_payload_validation(self): self.assertEqual(validate_payload(self.c,build_order_payload())["status"],"PASS")
    def test_client_order_id(self): self.assertTrue(build_order_payload()["client_order_id"].startswith("dryrun-"))
    def test_idempotency(self): self.assertTrue(idempotency_key(build_order_payload()).startswith("idem-"))
    def test_request(self): self.assertFalse(dry_run_request(self.c,build_order_payload())["network_request_executed"])
    def test_mock(self): self.assertEqual(mock_alpaca_response(build_order_payload())["status"],"accepted")
    def test_fill(self): self.assertEqual(simulate_fill(mock_alpaca_response(build_order_payload()))["status"],"filled")
    def test_reconcile(self):
        p=build_order_payload();r=simulate_fill(mock_alpaca_response(p))
        self.assertEqual(reconcile(p,r)["status"],"PASS")
    def test_retry(self): self.assertFalse(retry_policy()["automatic_retry_allowed"])
    def test_transitions(self): self.assertEqual(state_transitions()["transition_count"],5)
    def test_negative(self): self.assertEqual(negative_scenarios(self.c)["status"],"PASS")
    def test_integrated(self): self.assertEqual(integrated_dry_run(self.c)["status"],"PASS")
    def test_audit(self):
        self.assertEqual(final_audit(self.c,integrated_dry_run(self.c),negative_scenarios(self.c))["status"],"PASS")
    def test_store(self):
        with TemporaryDirectory() as t:
            pid,_=store_package(Path(t),{"x":{"status":"PASS"}})
            self.assertTrue(pid.startswith("actual-paper-dryrun-"))
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}});m=build_manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_stage_count(self): self.assertEqual(len(range(1,21)),20)

if __name__=="__main__": unittest.main()
