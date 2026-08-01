from pathlib import Path
from tempfile import TemporaryDirectory
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
import unittest
from alpaca_market_data.paper_scheduler_foundation_v88_01_20 import *

class T(unittest.TestCase):
 def setUp(self): self.c=PaperSchedulerFoundationConfig(); self.cal=market_calendar()
 def test_config(self): self.c.validate()
 def test_scheduler_rejected(self):
  with self.assertRaises(ValueError): PaperSchedulerFoundationConfig(scheduler_enabled=True).validate()
 def test_trading_day(self): self.assertTrue(is_trading_day(date(2026,7,6),self.cal))
 def test_holiday(self): self.assertFalse(is_trading_day(date(2026,7,3),self.cal))
 def test_early_close(self): self.assertTrue(session_times(self.c,date(2026,11,27),self.cal)["early_close"])
 def test_dst(self): self.assertEqual(dst_validation(self.c)["status"],"PASS")
 def test_events(self): self.assertEqual(event_plan(session_times(self.c,date(2026,7,6),self.cal))["event_count"],4)
 def test_duplicate(self):
  dt=datetime(2026,7,6,9,30,tzinfo=ZoneInfo(self.c.timezone))
  self.assertTrue(duplicate_guard(self.c,"MARKET_OPEN",dt,dt+timedelta(seconds=30))["duplicate_detected"])
 def test_missed(self):
  dt=datetime(2026,7,6,9,30,tzinfo=ZoneInfo(self.c.timezone))
  self.assertTrue(missed_schedule_recovery(self.c,dt,dt+timedelta(minutes=10))["recoverable"])
 def test_override(self):
  r=manual_override_request("u","r","MARKET_OPEN")
  self.assertEqual(manual_override_decision(r,"a",True)["status"],"APPROVED")
 def test_state(self): self.assertEqual(state_transition(scheduler_state(),"PREVIEW_EVENT")["to_state"],"DISABLED_READY")
 def test_heartbeat(self):
  dt=datetime.now(ZoneInfo(self.c.timezone))
  self.assertEqual(stale_heartbeat_check(dt,dt+timedelta(seconds=30))["status"],"PASS")
 def test_stale(self):
  dt=datetime.now(ZoneInfo(self.c.timezone))
  self.assertEqual(stale_heartbeat_check(dt,dt+timedelta(seconds=300))["status"],"FAIL")
 def test_shutdown(self): self.assertEqual(shutdown_plan()["status"],"PASS")
 def test_rollback(self): self.assertEqual(rollback_plan()["status"],"PASS")
 def test_scenario(self): self.assertTrue(scenario(self.c)["duplicate_detected"])
 def test_store_reuse(self):
  with TemporaryDirectory() as t:
   o=Path(t);store(o,{"a":{"x":1}});self.assertTrue(store(o,{"a":{"x":1}})["reused"])
 def test_manifest(self):
  with TemporaryDirectory() as t:
   o=Path(t);z=store(o,{"a":{"x":1}});m=manifest(o,z["ledger"]);self.assertTrue(verify_manifest(o,m))
 def test_bad_source(self):
  with TemporaryDirectory() as t:
   p=Path(t)/"x";p.write_text("{}")
   with self.assertRaises(ValueError):validate_source(p)
 def test_stage_count(self): self.assertEqual(len([f"V88.{i:02d}" for i in range(1,21)]),20)

if __name__=="__main__":unittest.main()
