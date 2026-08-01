
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.controlled_execution_fast_track_v95_01_v96_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=ControlledExecutionConfig()
    def test_config(self): self.c.validate()
    def test_live_url_rejected(self):
        with self.assertRaises(ValueError):
            ControlledExecutionConfig(base_url="https://api.alpaca.markets").validate()
    def test_environment_blocked(self): self.assertEqual(execution_environment({})["status"],"BLOCKED")
    def test_environment_ready(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1",
           "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1",
           "AI_STOCK_BOT_CONTROLLED_EXECUTION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        self.assertTrue(execution_environment(e)["execution_ready"])
    def test_order(self): self.assertEqual(build_order(self.c)["qty"],"1")
    def test_token(self): self.assertEqual(approval_token(self.c)["approval_count"],2)
    def test_preflight_blocked(self): self.assertEqual(preflight(self.c,{})["status"],"BLOCKED")
    def test_fixture_execute(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1",
           "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1",
           "AI_STOCK_BOT_CONTROLLED_EXECUTION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        self.assertEqual(execute_once(self.c,FixtureTransport(),e)["status"],"FIXTURE_ACCEPTED")
    def test_real_transport_blocked(self):
        self.assertEqual(execute_once(self.c,AlpacaPaperTransport(),{},allow_network=False)["status"],"BLOCKED")
    def test_reconcile(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1",
           "AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1",
           "AI_STOCK_BOT_CONTROLLED_EXECUTION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        x=execute_once(self.c,FixtureTransport(),e)
        self.assertEqual(reconcile(x)["status"],"PASS")
    def test_failure_policy(self): self.assertEqual(failure_policy()["scenario_count"],7)
    def test_rollback(self): self.assertTrue(kill_switch_and_rollback()["rollback_ready"])
    def test_offline_certification(self): self.assertEqual(offline_certification(self.c)["status"],"PASS")
    def test_default_safety(self): self.assertEqual(default_safety(self.c)["status"],"PASS")
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store_package(o,{"x":{"status":"PASS"}})
            m=build_manifest(o,l);self.assertTrue(verify_manifest(o,m))
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__":unittest.main()
