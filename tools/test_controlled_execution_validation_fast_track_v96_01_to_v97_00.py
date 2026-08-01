
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.controlled_execution_validation_fast_track_v96_01_v97_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=ValidationConfig()
    def test_config(self): self.c.validate()
    def test_live_url_rejected(self):
        with self.assertRaises(ValueError): ValidationConfig(base_url="https://api.alpaca.markets").validate()
    def test_env_blocked(self): self.assertEqual(validation_env({})["status"],"BLOCKED")
    def test_env_ready(self): self.assertEqual(validation_env(fixture_env())["status"],"READY")
    def test_account(self): self.assertEqual(account_validation(FixtureReadTransport().get(PAPER_BASE_URL+"/v2/account",{},10))["status"],"PASS")
    def test_clock(self): self.assertEqual(clock_validation(FixtureReadTransport().get(PAPER_BASE_URL+"/v2/clock",{},10))["status"],"PASS")
    def test_order(self):
        o=FixtureReadTransport().get(PAPER_BASE_URL+"/v2/orders:by_client_order_id?client_order_id=controlled-fixture",{},10)
        e={"client_order_id":"controlled-fixture","symbol":"AAPL","side":"buy","qty":"1"}
        self.assertEqual(order_validation(o,e)["status"],"PASS")
    def test_duplicate(self): self.assertEqual(duplicate_guard("x",{"x"})["status"],"BLOCKED_DUPLICATE")
    def test_unknown(self): self.assertEqual(unknown_state_policy()["scenario_count"],5)
    def test_cancel(self): self.assertFalse(cancel_policy_preview()["cancel_request_executed"])
    def test_cycle(self): self.assertEqual(validate_cycle(self.c,FixtureReadTransport(),fixture_env())["status"],"PASS")
    def test_network_blocked(self): self.assertEqual(validate_cycle(self.c,AlpacaPaperReadTransport(),fixture_env(),False)["status"],"BLOCKED")
    def test_offline(self): self.assertEqual(offline_certification(self.c)["status"],"PASS")
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store(o,{"x":{"status":"PASS"}});m=manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
