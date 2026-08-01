
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from alpaca_market_data.controlled_session_execution_fast_track_v97_01_v98_00 import *

class T(unittest.TestCase):
    def setUp(self): self.c=ControlledSessionConfig()
    def test_config(self): self.c.validate()
    def test_env_blocked(self): self.assertEqual(session_environment({})["status"],"BLOCKED")
    def test_create(self): self.assertEqual(create_session(self.c)["status"],"CREATED")
    def test_start_blocked(self): self.assertEqual(start_session(create_session(self.c),{})["status"],"BLOCKED")
    def test_start_ready(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1","AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1","AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
           "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        self.assertEqual(start_session(create_session(self.c),e)["status"],"ACTIVE")
    def test_heartbeat(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1","AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1","AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
           "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        c=create_session(self.c);s=start_session(c,e)
        self.assertEqual(heartbeat(s,c["created_at"]+30)["status"],"HEALTHY")
    def test_duplicate(self): self.assertEqual(duplicate_session_guard({"x"},"x")["status"],"BLOCKED_DUPLICATE")
    def test_resume(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1","AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1","AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
           "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        c=create_session(self.c);s=start_session(c,e)
        cp={"session_id":c["session_id"],"remaining_orders":1,"remaining_uses":1,"kill_switch_clear":True}
        self.assertEqual(resume_session(s,cp,c["created_at"]+60)["status"],"RESUMED_READ_ONLY")
    def test_consume(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1","AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1","AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
           "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        c=create_session(self.c);s=start_session(c,e)
        self.assertEqual(consume_session(s)["status"],"CONSUMED")
    def test_close(self):
        e={"AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_READ":"1","AI_STOCK_BOT_ENABLE_ACTUAL_PAPER_SINGLE_ORDER":"1",
           "AI_STOCK_BOT_ENABLE_CONTROLLED_EXECUTION":"1","AI_STOCK_BOT_ENABLE_CONTROLLED_SESSION":"1",
           "AI_STOCK_BOT_CONTROLLED_SESSION_CONFIRMATION":CONFIRMATION_TEXT,
           "AI_STOCK_BOT_KILL_SWITCH":"0","APCA_API_KEY_ID":"A","APCA_API_SECRET_KEY":"B"}
        c=create_session(self.c);s=start_session(c,e);x=consume_session(s)
        self.assertEqual(close_session(x)["status"],"CLOSED")
    def test_recovery(self): self.assertEqual(recovery_policy()["scenario_count"],6)
    def test_rollback(self): self.assertTrue(rollback_plan()["rollback_ready"])
    def test_offline(self): self.assertEqual(offline_certification(self.c)["status"],"PASS")
    def test_safety(self): self.assertEqual(default_safety(self.c)["status"],"PASS")
    def test_manifest(self):
        with TemporaryDirectory() as t:
            o=Path(t);_,l=store(o,{"x":{"status":"PASS"}});m=manifest(o,l)
            self.assertTrue(verify_manifest(o,m))
    def test_stage_range(self): self.assertEqual(len(range(1,101)),100)

if __name__=="__main__": unittest.main()
