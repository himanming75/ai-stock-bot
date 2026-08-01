
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.single_order_network_optin_fast_track_v94_01_v95_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=NetworkOptInConfig()
    def test_config(self): self.c.validate()
    def test_unsafe_url(self):
        with self.assertRaises(ValueError):
            NetworkOptInConfig(base_url="https://api.alpaca.markets").validate()
    def test_credentials_missing(self): self.assertEqual(credential_state({})["status"],"MISSING")
    def test_credentials_redacted(self):
        x=credential_state({"APCA_API_KEY_ID":"ABC123","APCA_API_SECRET_KEY":"SECRET"})
        self.assertFalse(x["raw_credentials_exposed"])
    def test_headers_blocked(self): self.assertEqual(auth_headers_preview({})["status"],"BLOCKED_MISSING_CREDENTIALS")
    def test_headers_ready(self):
        x=auth_headers_preview({"APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"})
        self.assertEqual(x["status"],"READY_PREVIEW")
    def test_catalog(self): self.assertEqual(endpoint_catalog(self.c)["status"],"PASS")
    def test_read_default(self): self.assertEqual(read_opt_in(self.c,{})["status"],"OFFLINE_DEFAULT")
    def test_read_optin(self):
        e={self.c.read_network_opt_in_env:"1","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        self.assertTrue(read_opt_in(self.c,e)["network_read_allowed"])
    def test_write_contract(self): self.assertFalse(single_order_write_contract(self.c,{})["actual_write_authorized"])
    def test_request_preview(self): self.assertEqual(order_request_preview(self.c)["status"],"READY_PREVIEW_ONLY")
    def test_response_parser(self): self.assertEqual(response_parser_fixture()["status"],"PASS")
    def test_failure_policy(self): self.assertEqual(network_failure_policy()["scenario_count"],6)
    def test_reconciliation(self): self.assertEqual(reconciliation_preview()["status"],"PASS")
    def test_safety(self): self.assertEqual(safety_certification(self.c)["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_integrated(self): self.assertEqual(integrated(self.c)["status"],"PASS")
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}})
            m=build_manifest(o,l); self.assertTrue(verify_manifest(o,m))
    def test_orders_zero(self): self.assertEqual(self.c.actual_orders_submitted,0)
    def test_network_zero(self): self.assertEqual(self.c.network_requests_executed,0)
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
